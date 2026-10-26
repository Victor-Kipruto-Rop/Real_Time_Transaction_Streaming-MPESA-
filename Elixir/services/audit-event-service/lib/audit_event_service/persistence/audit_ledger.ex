defmodule PesaGuard.AuditEventService.Persistence.AuditLedger do
  @moduledoc """
  Tenant-scoped append-only audit ledger with a per-tenant hash chain.

  Appends and idempotency checks are serialized by a PostgreSQL transaction
  advisory lock. The generic mutable record API is not used for audit events.
  """

  @connection PesaGuard.AuditEventService.Persistence.PostgresConnection

  def append(tenant_id, idempotency_key, event)
      when is_binary(tenant_id) and byte_size(tenant_id) > 0 and
             is_binary(idempotency_key) and byte_size(idempotency_key) > 0 and is_map(event) do
    case Postgrex.transaction(@connection, fn conn ->
           append_transaction(conn, tenant_id, idempotency_key, event)
         end) do
      {:ok, {:ok, record, status}} -> {:ok, record, status}
      {:ok, {:error, reason}} -> {:error, reason}
      {:error, _reason} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  catch
    :exit, _ -> {:error, :unavailable}
  end

  def append(_, _, _), do: {:error, :invalid_event}

  def get(tenant_id, event_id) when is_binary(tenant_id) and is_binary(event_id) do
    sql = """
    SELECT event_id, tenant_id, tenant_sequence, idempotency_key, actor_type,
           action, occurred_at, event_payload::text, previous_hash, event_hash, recorded_at
    FROM telixo_audit_events
    WHERE tenant_id = $1 AND event_id = $2
    """

    case Postgrex.query(@connection, sql, [tenant_id, event_id]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_event(row)}
      {:ok, %{rows: []}} -> {:error, :not_found}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def get(_, _), do: {:error, :not_found}

  def verify_chain(tenant_id) when is_binary(tenant_id) do
    sql = """
    SELECT event_id, tenant_sequence, idempotency_key, event_payload::text, previous_hash, event_hash
    FROM telixo_audit_events
    WHERE tenant_id = $1
    ORDER BY tenant_sequence ASC
    """

    with {:ok, %{rows: rows}} <- Postgrex.query(@connection, sql, [tenant_id]) do
      verify_rows(rows, tenant_id, 1, nil)
    else
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def verify_chain(_), do: {:error, :invalid_tenant}

  defp append_transaction(conn, tenant_id, idempotency_key, event) do
    Postgrex.query!(conn, "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [tenant_id])

    case Postgrex.query!(conn, """
           SELECT event_id, tenant_id, tenant_sequence, idempotency_key, actor_type,
                  action, occurred_at, event_payload::text, previous_hash, event_hash, recorded_at
           FROM telixo_audit_events
           WHERE tenant_id = $1 AND idempotency_key = $2
           """, [tenant_id, idempotency_key]).rows do
      [row] ->
        existing = decode_event(row)
        if existing.event == event, do: {:ok, existing, :duplicate}, else: {:error, :conflict}

      [] ->
        append_new(conn, tenant_id, idempotency_key, event)
    end
  end

  defp append_new(conn, tenant_id, idempotency_key, event) do
    head_rows =
      Postgrex.query!(conn, """
      SELECT last_hash, last_sequence
      FROM telixo_audit_tenant_heads
      WHERE tenant_id = $1
      FOR UPDATE
      """, [tenant_id]).rows

    {previous_hash, sequence} =
      case head_rows do
        [[hash, last_sequence]] -> {hash, last_sequence + 1}
        [] -> {nil, 1}
      end

    event_id = Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)
    digest = calculate_hash(tenant_id, idempotency_key, sequence, event, previous_hash)

    insert_sql = """
    INSERT INTO telixo_audit_events
      (event_id, tenant_id, tenant_sequence, idempotency_key, actor_type, action,
       occurred_at, event_payload, previous_hash, event_hash)
    VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz, $8::text::jsonb, $9, $10)
    RETURNING event_id, tenant_id, tenant_sequence, idempotency_key, actor_type,
              action, occurred_at, event_payload::text, previous_hash, event_hash, recorded_at
    """

    [row] =
      Postgrex.query!(conn, insert_sql, [
        event_id,
        tenant_id,
        sequence,
        idempotency_key,
        event["actor_type"],
        event["action"],
        event["occurred_at"],
        Jason.encode!(event),
        previous_hash,
        digest
      ]).rows

    Postgrex.query!(conn, """
    INSERT INTO telixo_audit_tenant_heads (tenant_id, last_event_id, last_hash, last_sequence)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (tenant_id) DO UPDATE
      SET last_event_id = EXCLUDED.last_event_id,
          last_hash = EXCLUDED.last_hash,
          last_sequence = EXCLUDED.last_sequence,
          updated_at = now()
    """, [tenant_id, event_id, digest, sequence])

    {:ok, decode_event(row), :created}
  end

  defp verify_rows([], _tenant_id, _expected_sequence, _previous_hash), do: :ok

  defp verify_rows([[event_id, sequence, idempotency_key, payload_text, previous_hash, stored_hash] | rest],
         tenant_id, expected_sequence, expected_previous_hash) do
    event = Jason.decode!(payload_text)
    expected_hash = calculate_hash(tenant_id, idempotency_key, sequence, event, expected_previous_hash)

    if sequence == expected_sequence and previous_hash == expected_previous_hash and
         Plug.Crypto.secure_compare(stored_hash, expected_hash) do
      verify_rows(rest, tenant_id, expected_sequence + 1, stored_hash)
    else
      {:error, {:integrity_violation, event_id}}
    end
  end

  defp calculate_hash(tenant_id, idempotency_key, sequence, event, previous_hash) do
    envelope = %{
      "tenant_id" => tenant_id,
      "idempotency_key" => idempotency_key,
      "tenant_sequence" => sequence,
      "event" => event,
      "previous_hash" => previous_hash
    }

    :crypto.hash(:sha256, canonical_json(envelope))
    |> Base.encode16(case: :lower)
  end

  defp canonical_json(map) when is_map(map) do
    fields =
      map
      |> Enum.sort_by(fn {key, _value} -> key end)
      |> Enum.map(fn {key, value} -> Jason.encode!(key) <> ":" <> canonical_json(value) end)

    "{" <> Enum.join(fields, ",") <> "}"
  end

  defp canonical_json(list) when is_list(list) do
    "[" <> (list |> Enum.map(&canonical_json/1) |> Enum.join(",")) <> "]"
  end

  defp canonical_json(value), do: Jason.encode!(value)

  defp decode_event([event_id, tenant_id, sequence, idempotency_key, actor_type, action,
        occurred_at, payload_text, previous_hash, event_hash, recorded_at]) do
    %{
      event_id: event_id,
      tenant_id: tenant_id,
      tenant_sequence: sequence,
      idempotency_key: idempotency_key,
      actor_type: actor_type,
      action: action,
      occurred_at: DateTime.to_iso8601(occurred_at),
      event: Jason.decode!(payload_text),
      previous_hash: previous_hash,
      event_hash: event_hash,
      recorded_at: DateTime.to_iso8601(recorded_at)
    }
  end
end
