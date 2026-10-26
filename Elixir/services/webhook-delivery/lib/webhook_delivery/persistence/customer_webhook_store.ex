defmodule PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStore do
  @moduledoc """
  Durable tenant-scoped customer webhook subscriptions and delivery queue.

  Signing secrets are envelope-encrypted with an AES-256-GCM key supplied through
  WEBHOOK_SECRET_ENCRYPTION_KEY (base64-encoded 32 bytes). The key must be held in
  a secret manager and rotated through an explicit migration procedure.
  """

  @connection PesaGuard.WebhookDelivery.Persistence.PostgresConnection
  @max_attempts 8
  @lease_seconds 60

  alias PesaGuard.WebhookDelivery.Domain.Processor

  def create_subscription(tenant_id, idempotency_key, target_url, event_types, secret)
      when is_binary(tenant_id) and byte_size(tenant_id) in 1..200 and
             is_binary(idempotency_key) and byte_size(idempotency_key) in 1..200 and
             is_binary(target_url) and is_list(event_types) and is_binary(secret) do
    with true <- byte_size(secret) >= 32,
         :ok <- validate_event_types(event_types),
         {:ok, _} <- Processor.prepare(%{"target_url" => target_url, "payload" => %{}}),
         {:ok, encryption_key} <- encryption_key() do
      subscription_id = random_id()
      nonce = :crypto.strong_rand_bytes(12)
      aad = associated_data(tenant_id, subscription_id)
      {ciphertext, tag} = :crypto.crypto_one_time_aead(:aes_256_gcm, encryption_key, nonce, secret, aad, true)

      sql = """
      INSERT INTO telixo_webhook_subscriptions
        (subscription_id, tenant_id, idempotency_key, target_url, event_types,
         secret_ciphertext, secret_nonce, secret_tag)
      VALUES ($1, $2, $3, $4, $5::text::jsonb, $6, $7, $8)
      ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
      RETURNING subscription_id, tenant_id, target_url, event_types::text, active, created_at
      """

      case Postgrex.query(@connection, sql, [
             subscription_id, tenant_id, idempotency_key, target_url,
             Jason.encode!(Enum.uniq(event_types)), ciphertext, nonce, tag
           ]) do
        {:ok, %{rows: [row]}} ->
          {:ok, decode_subscription(row), :created}

        {:ok, %{rows: []}} ->
          existing_sql = """
          SELECT subscription_id, tenant_id, target_url, event_types::text, active, created_at
          FROM telixo_webhook_subscriptions
          WHERE tenant_id = $1 AND idempotency_key = $2
          """

          case Postgrex.query(@connection, existing_sql, [tenant_id, idempotency_key]) do
            {:ok, %{rows: [row]}} ->
              existing = decode_subscription(row)

              if existing.target_url == target_url and existing.event_types == Enum.uniq(event_types) do
                {:ok, existing, :duplicate}
              else
                {:error, :idempotency_conflict}
              end

            _ ->
              {:error, :unavailable}
          end

        {:error, _} ->
          {:error, :unavailable}
      end
    else
      false -> {:error, :invalid_secret}
      {:error, reason} -> {:error, reason}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def create_subscription(_, _, _, _, _), do: {:error, :invalid_subscription}

  def list_subscriptions(tenant_id) when is_binary(tenant_id) do
    sql = """
    SELECT subscription_id, tenant_id, target_url, event_types::text, active, created_at
    FROM telixo_webhook_subscriptions
    WHERE tenant_id = $1
    ORDER BY created_at DESC
    LIMIT 200
    """

    case Postgrex.query(@connection, sql, [tenant_id]) do
      {:ok, %{rows: rows}} -> {:ok, Enum.map(rows, &decode_subscription/1)}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def enqueue(tenant_id, subscription_id, event_id, event_type, payload)
      when is_binary(tenant_id) and is_binary(subscription_id) and is_binary(event_id) and
             byte_size(event_id) in 1..200 and is_binary(event_type) and
             byte_size(event_type) in 1..160 and is_map(payload) do
    with {:ok, subscription} <- get_subscription(tenant_id, subscription_id),
         true <- subscription.active,
         true <- event_type in subscription.event_types do
      delivery_id = stable_delivery_id(subscription_id, event_id)
      sql = """
      INSERT INTO telixo_customer_webhook_deliveries
        (delivery_id, tenant_id, subscription_id, event_id, event_type, payload)
      VALUES ($1, $2, $3, $4, $5, $6::text::jsonb)
      ON CONFLICT (subscription_id, event_id) DO NOTHING
      RETURNING delivery_id, status, attempts, payload::text, created_at
      """

      case Postgrex.query(@connection, sql, [
             delivery_id, tenant_id, subscription_id, event_id, event_type, Jason.encode!(payload)
           ]) do
        {:ok, %{rows: [row]}} ->
          {:ok, decode_delivery(row), :created}

        {:ok, %{rows: []}} ->
          duplicate_sql = """
          SELECT delivery_id, status, attempts, payload::text, created_at
          FROM telixo_customer_webhook_deliveries
          WHERE tenant_id = $1 AND subscription_id = $2 AND event_id = $3
          """

          case Postgrex.query(@connection, duplicate_sql, [tenant_id, subscription_id, event_id]) do
            {:ok, %{rows: [row]}} ->
              existing = decode_delivery(row)
              if existing.payload == payload, do: {:ok, existing, :duplicate}, else: {:error, :event_conflict}

            _ ->
              {:error, :unavailable}
          end

        {:error, _} ->
          {:error, :unavailable}
      end
    else
      false -> {:error, :subscription_inactive_or_event_not_allowed}
      {:error, :not_found} -> {:error, :not_found}
      {:error, reason} -> {:error, reason}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def enqueue(_, _, _, _, _), do: {:error, :invalid_delivery}

  def claim(limit \\ 20) when is_integer(limit) and limit > 0 and limit <= 100 do
    sql = """
    WITH candidates AS (
      SELECT delivery_id
      FROM telixo_customer_webhook_deliveries
      WHERE (status = 'pending' AND next_attempt_at <= now())
         OR (status = 'in_progress' AND lease_expires_at < now())
      ORDER BY created_at
      LIMIT $1
      FOR UPDATE SKIP LOCKED
    )
    UPDATE telixo_customer_webhook_deliveries AS d
    SET status = 'in_progress', attempts = d.attempts + 1,
        lease_expires_at = now() + ($2 * interval '1 second'), updated_at = now()
    FROM candidates c, telixo_webhook_subscriptions s
    WHERE d.delivery_id = c.delivery_id
      AND s.subscription_id = d.subscription_id
      AND s.tenant_id = d.tenant_id
      AND s.active = TRUE
    RETURNING d.delivery_id, d.tenant_id, d.subscription_id, d.event_id, d.event_type,
              d.payload::text, d.attempts, s.target_url, s.secret_ciphertext,
              s.secret_nonce, s.secret_tag
    """

    with {:ok, key} <- encryption_key(),
         {:ok, %{rows: rows}} <- Postgrex.query(@connection, sql, [limit, @lease_seconds]) do
      Enum.reduce_while(rows, {:ok, []}, fn row, {:ok, acc} ->
        [delivery_id, tenant_id, subscription_id, event_id, event_type, payload, attempts,
         target_url, ciphertext, nonce, tag] = row

        case :crypto.crypto_one_time_aead(
               :aes_256_gcm, key, nonce, ciphertext,
               associated_data(tenant_id, subscription_id), tag, false
             ) do
          :error ->
            fail(tenant_id, delivery_id, "secret_decryption_failed", true)
            {:cont, {:ok, acc}}

          secret when is_binary(secret) ->
            delivery = %{
              delivery_id: delivery_id, tenant_id: tenant_id, subscription_id: subscription_id,
              event_id: event_id, event_type: event_type, payload: Jason.decode!(payload),
              attempts: attempts, target_url: target_url, secret: secret
            }
            {:cont, {:ok, [delivery | acc]}}
        end
      end)
      |> case do
        {:ok, deliveries} -> {:ok, Enum.reverse(deliveries)}
        error -> error
      end
    else
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def acknowledge(tenant_id, delivery_id, http_status)
      when is_binary(tenant_id) and is_binary(delivery_id) and is_integer(http_status) do
    sql = """
    UPDATE telixo_customer_webhook_deliveries
    SET status = 'delivered', last_http_status = $3, delivered_at = now(),
        lease_expires_at = NULL, last_error = NULL, updated_at = now()
    WHERE tenant_id = $1 AND delivery_id = $2 AND status = 'in_progress'
    """

    update_one(sql, [tenant_id, delivery_id, http_status])
  end

  def fail(tenant_id, delivery_id, reason, permanent? \\ false)
      when is_binary(tenant_id) and is_binary(delivery_id) and is_binary(reason) and
             is_boolean(permanent?) do
    sql = """
    UPDATE telixo_customer_webhook_deliveries
    SET status = CASE WHEN attempts >= $4 OR $5 THEN 'dead_lettered' ELSE 'pending' END,
        next_attempt_at = now() + LEAST(300, power(2, LEAST(attempts, 8))) * interval '1 second',
        lease_expires_at = NULL, last_error = left($3, 1000), updated_at = now()
    WHERE tenant_id = $1 AND delivery_id = $2 AND status = 'in_progress'
    """

    update_one(sql, [tenant_id, delivery_id, reason, @max_attempts, permanent?])
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

  defp get_subscription(tenant_id, subscription_id) do
    sql = """
    SELECT subscription_id, tenant_id, target_url, event_types::text, active, created_at
    FROM telixo_webhook_subscriptions
    WHERE tenant_id = $1 AND subscription_id = $2
    """

    case Postgrex.query(@connection, sql, [tenant_id, subscription_id]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_subscription(row)}
      {:ok, %{rows: []}} -> {:error, :not_found}
      {:error, _} -> {:error, :unavailable}
    end
  end

  defp validate_event_types(types) do
    valid? = is_list(types) and length(types) in 1..50 and
      Enum.all?(types, &(is_binary(&1) and byte_size(&1) in 1..160))

    if valid?, do: :ok, else: {:error, :invalid_event_types}
  end

  defp encryption_key do
    case System.get_env("WEBHOOK_SECRET_ENCRYPTION_KEY") do
      value when is_binary(value) ->
        case Base.decode64(value) do
          {:ok, key} when byte_size(key) == 32 -> {:ok, key}
          _ -> {:error, :encryption_key_must_be_base64_32_bytes}
        end

      _ ->
        {:error, :encryption_key_not_configured}
    end
  end

  defp associated_data(tenant_id, subscription_id), do: tenant_id <> ":" <> subscription_id

  defp random_id do
    Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)
  end

  defp stable_delivery_id(subscription_id, event_id) do
    :crypto.hash(:sha256, subscription_id <> ":" <> event_id)
    |> Base.url_encode64(padding: false)
  end

  defp decode_subscription([id, tenant_id, target_url, event_types, active, created_at]) do
    %{
      subscription_id: id, tenant_id: tenant_id, target_url: target_url,
      event_types: Jason.decode!(event_types), active: active,
      created_at: DateTime.to_iso8601(created_at)
    }
  end

  defp decode_delivery([id, status, attempts, payload, created_at]) do
    %{
      delivery_id: id, status: status, attempts: attempts,
      payload: Jason.decode!(payload), created_at: DateTime.to_iso8601(created_at)
    }
  end
end
