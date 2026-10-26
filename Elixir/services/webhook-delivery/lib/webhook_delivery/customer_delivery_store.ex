defmodule PesaGuard.WebhookDelivery.CustomerDeliveryStore do
  @moduledoc """
  Durable customer webhook subscriptions and delivery lifecycle. Delivery IDs
  are deterministic per tenant/subscription/event, making enqueue idempotent.
  """

  @connection PesaGuard.WebhookDelivery.Persistence.PostgresConnection
  @max_batch 100

  alias PesaGuard.WebhookDelivery.Domain.Processor
  alias PesaGuard.WebhookDelivery.SecretBox

  def create_subscription(tenant_id, target_url, event_types, secret)
      when is_binary(tenant_id) and byte_size(tenant_id) in 1..200 and
             is_binary(target_url) and is_list(event_types) and is_binary(secret) do
    with true <- valid_event_types?(event_types),
         {:ok, _} <- Processor.prepare(%{"target_url" => target_url, "payload" => %{}}),
         {:ok, encrypted_secret} <- SecretBox.encrypt(secret) do
      subscription_id = random_id()
      sql = """
      INSERT INTO telixo_webhook_subscriptions
        (subscription_id, tenant_id, target_url, encrypted_secret, event_types)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING subscription_id, tenant_id, target_url, event_types, active, created_at
      """

      case Postgrex.query(@connection, sql, [subscription_id, tenant_id, target_url, encrypted_secret, event_types]) do
        {:ok, %{rows: [row]}} -> {:ok, decode_subscription(row)}
        {:error, _} -> {:error, :unavailable}
      end
    else
      false -> {:error, :invalid_event_types}
      {:error, reason} -> {:error, reason}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def create_subscription(_, _, _, _), do: {:error, :invalid_subscription}

  def list_subscriptions(tenant_id) when is_binary(tenant_id) do
    sql = """
    SELECT subscription_id, tenant_id, target_url, event_types, active, created_at
    FROM telixo_webhook_subscriptions
    WHERE tenant_id = $1
    ORDER BY created_at DESC
    """

    case Postgrex.query(@connection, sql, [tenant_id]) do
      {:ok, %{rows: rows}} -> {:ok, Enum.map(rows, &decode_subscription/1)}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def enqueue_event(tenant_id, event)
      when is_binary(tenant_id) and is_map(event) do
    event_id = Map.get(event, "event_id")
    event_type = Map.get(event, "event_type")

    with true <- valid_event_id?(event_id),
         true <- valid_event_type?(event_type),
         {:ok, encoded_event} <- Jason.encode(event) do
      sql = """
      INSERT INTO telixo_webhook_deliveries
        (delivery_id, tenant_id, subscription_id, event_id, event_type, event_payload)
      SELECT
        encode(digest(convert_to(s.subscription_id || ':' || $3, 'UTF8'), 'sha256'), 'hex'),
        s.tenant_id, s.subscription_id, $3, $4, $5::text::jsonb
      FROM telixo_webhook_subscriptions s
      WHERE s.tenant_id = $1 AND s.active = TRUE
        AND (s.event_types @> ARRAY[$4]::text[] OR '*' = ANY(s.event_types))
      ON CONFLICT (tenant_id, subscription_id, event_id) DO NOTHING
      RETURNING delivery_id
      """

      case Postgrex.query(@connection, sql, [tenant_id, event, event_id, event_type, encoded_event]) do
        {:ok, %{rows: rows}} -> {:ok, Enum.map(rows, fn [id] -> id end)}
        {:error, _} -> {:error, :unavailable}
      end
    else
      false -> {:error, :invalid_event}
      {:error, _} -> {:error, :invalid_event}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def enqueue_event(_, _), do: {:error, :invalid_event}

  def claim_deliveries(limit \\ 20) when is_integer(limit) and limit > 0 and limit <= @max_batch do
    sql = """
    WITH candidates AS (
      SELECT delivery_id
      FROM telixo_webhook_deliveries
      WHERE (status = 'pending' AND next_attempt_at <= now())
         OR (status = 'in_progress' AND lease_expires_at < now())
      ORDER BY created_at
      LIMIT $1
      FOR UPDATE SKIP LOCKED
    )
    UPDATE telixo_webhook_deliveries d
    SET status = 'in_progress', attempts = d.attempts + 1,
        lease_expires_at = now() + interval '60 seconds', updated_at = now()
    FROM candidates c
    WHERE d.delivery_id = c.delivery_id
    RETURNING d.delivery_id, d.tenant_id, d.subscription_id, d.event_id, d.event_type,
      d.event_payload::text, d.attempts,
      (SELECT s.target_url FROM telixo_webhook_subscriptions s
       WHERE s.tenant_id = d.tenant_id AND s.subscription_id = d.subscription_id),
      (SELECT s.encrypted_secret FROM telixo_webhook_subscriptions s
       WHERE s.tenant_id = d.tenant_id AND s.subscription_id = d.subscription_id)
    """

    case Postgrex.query(@connection, sql, [limit]) do
      {:ok, %{rows: rows}} -> {:ok, Enum.map(rows, &decode_delivery/1)}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def complete_delivery(tenant_id, delivery_id, status_code)
      when is_binary(tenant_id) and is_binary(delivery_id) and is_integer(status_code) do
    sql = """
    UPDATE telixo_webhook_deliveries
    SET status = 'succeeded', delivered_at = now(), updated_at = now(),
        last_status_code = $3, last_error_code = NULL, lease_expires_at = NULL
    WHERE tenant_id = $1 AND delivery_id = $2 AND status = 'in_progress'
    """

    update_one(sql, [tenant_id, delivery_id, status_code])
  end

  def fail_delivery(tenant_id, delivery_id, attempts, failure, status_code \\ nil)
      when is_binary(tenant_id) and is_binary(delivery_id) and is_integer(attempts) and is_binary(failure) do
    retry? = attempts < 8 and (status_code in [408, 425, 429] or is_nil(status_code) or status_code >= 500)
    delay = min(1_000 * Integer.pow(2, min(attempts - 1, 8)), 300_000)
    status = if retry?, do: "pending", else: "dead_lettered"
    sql = """
    UPDATE telixo_webhook_deliveries
    SET status = $3, next_attempt_at = now() + ($4 * interval '1 millisecond'),
        updated_at = now(), last_status_code = $5, last_error_code = $6,
        lease_expires_at = NULL
    WHERE tenant_id = $1 AND delivery_id = $2 AND status = 'in_progress'
    """
    update_one(sql, [tenant_id, delivery_id, status, if(retry?, do: delay, else: 0), status_code, String.slice(failure, 0, 120)])
  end

  def get_delivery(tenant_id, delivery_id) when is_binary(tenant_id) and is_binary(delivery_id) do
    sql = """
    SELECT delivery_id, tenant_id, subscription_id, event_id, event_type, status,
           attempts, last_status_code, last_error_code, created_at, updated_at, delivered_at
    FROM telixo_webhook_deliveries WHERE tenant_id = $1 AND delivery_id = $2
    """

    case Postgrex.query(@connection, sql, [tenant_id, delivery_id]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_history(row)}
      {:ok, %{rows: []}} -> {:error, :not_found}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  defp update_one(sql, params) do
    case Postgrex.query(@connection, sql, params) do
      {:ok, %{num_rows: 1}} -> :ok
      {:ok, %{num_rows: 0}} -> {:error, :conflict}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  defp valid_event_types?(types), do: length(types) in 1..50 and Enum.all?(types, &valid_event_type?/1) and length(Enum.uniq(types)) == length(types)
  defp valid_event_type?(value), do: is_binary(value) and byte_size(value) in 1..160 and String.match?(value, ~r/\A[a-zA-Z0-9._*-]+\z/)
  defp valid_event_id?(value), do: is_binary(value) and byte_size(value) in 1..200
  defp random_id, do: Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)

  defp decode_subscription([id, tenant, url, types, active, created]) do
    %{subscription_id: id, tenant_id: tenant, target_url: url, event_types: types, active: active, created_at: DateTime.to_iso8601(created)}
  end

  defp decode_delivery([id, tenant, subscription_id, event_id, event_type, payload, attempts, url, encrypted_secret]) do
    %{delivery_id: id, tenant_id: tenant, subscription_id: subscription_id, event_id: event_id,
      event_type: event_type, event: Jason.decode!(payload), attempts: attempts, target_url: url,
      encrypted_secret: encrypted_secret}
  end

  defp decode_history([id, tenant, subscription_id, event_id, event_type, status, attempts, status_code, error_code, created, updated, delivered]) do
    %{delivery_id: id, tenant_id: tenant, subscription_id: subscription_id, event_id: event_id,
      event_type: event_type, status: status, attempts: attempts, last_status_code: status_code,
      last_error_code: error_code, created_at: DateTime.to_iso8601(created),
      updated_at: DateTime.to_iso8601(updated), delivered_at: if(delivered, do: DateTime.to_iso8601(delivered), else: nil)}
  end
end
