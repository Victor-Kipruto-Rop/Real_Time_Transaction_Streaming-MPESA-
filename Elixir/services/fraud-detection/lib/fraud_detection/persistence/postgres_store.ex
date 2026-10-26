defmodule PesaGuard.FraudDetection.Persistence.PostgresStore do
  @moduledoc """
  PostgreSQL-backed tenant-scoped records and transactional outbox.
  Record creation and outbox insertion commit atomically.
  """

  use GenServer

  @connection PesaGuard.FraudDetection.Persistence.PostgresConnection
  @service "fraud-detection"

  @records_schema """
  CREATE TABLE IF NOT EXISTS telixo_service_records (
    record_id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (service_name, tenant_id, kind, idempotency_key)
  )
  """

  @outbox_schema """
  CREATE TABLE IF NOT EXISTS telixo_outbox (
    event_id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ
  )
  """

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def children do
    environment = Application.get_env(:fraud_detection, :environment)

    case {System.get_env("DATABASE_URL"), environment} do
      {url, _} when is_binary(url) and url != "" ->
        [Supervisor.child_spec({__MODULE__, []}, id: __MODULE__)]

      {_, :prod} ->
        raise "DATABASE_URL must be configured in production"

      _ ->
        []
    end
  end

  @impl true
  def init(_opts) do
    case Postgrex.start_link(
           url: System.fetch_env!("DATABASE_URL"),
           name: @connection,
           pool_size: 10
         ) do
      {:ok, _pid} ->
        with {:ok, _} <- Postgrex.query(@connection, @records_schema, []),
             {:ok, _} <- Postgrex.query(@connection, @outbox_schema, []),
             {:ok, _} <-
               Postgrex.query(
                 @connection,
                 "CREATE INDEX IF NOT EXISTS telixo_records_tenant_created_idx ON telixo_service_records (service_name, tenant_id, created_at DESC)",
                 []
               ),
             {:ok, _} <-
               Postgrex.query(
                 @connection,
                 "CREATE INDEX IF NOT EXISTS telixo_outbox_ready_idx ON telixo_outbox (service_name, status, next_attempt_at, created_at)",
                 []
               ) do
          {:ok, %{connected: true}}
        else
          {:error, reason} -> {:stop, {:schema_initialization_failed, reason}}
        end

      {:error, reason} ->
        {:stop, {:database_connection_failed, reason}}
    end
  end

  def ready? do
    case Postgrex.query(@connection, "SELECT 1", []) do
      {:ok, _} -> :ok
      {:error, _} -> {:error, :database_unavailable}
    end
  rescue
    _ -> {:error, :database_unavailable}
  end

  def insert_once(tenant_id, kind, idempotency_key, state, payload)
      when is_binary(tenant_id) and is_binary(kind) and is_binary(idempotency_key) and
             is_binary(state) and is_map(payload) do
    record_id = Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)
    encoded_payload = Jason.encode!(payload)

    record_sql = """
    INSERT INTO telixo_service_records
      (record_id, service_name, tenant_id, kind, state, idempotency_key, payload)
    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
    ON CONFLICT (service_name, tenant_id, kind, idempotency_key) DO NOTHING
    RETURNING record_id, service_name, tenant_id, kind, state, idempotency_key,
              payload::text, created_at, updated_at
    """

    case Postgrex.transaction(@connection, fn conn ->
           case Postgrex.query!(conn, record_sql, [
                  record_id,
                  @service,
                  tenant_id,
                  kind,
                  state,
                  idempotency_key,
                  encoded_payload
                ]).rows do
             [row] ->
               record = decode_row(row)
               event = %{
                 "event_id" => record_id,
                 "tenant_id" => tenant_id,
                 "event_type" => "#{@service}.record_created",
                 "occurred_at" => DateTime.utc_now() |> DateTime.to_iso8601(),
                 "schema_version" => 1,
                 "payload" => %{
                   "record_id" => record_id,
                   "record_type" => kind,
                   "state" => state,
                   "data" => payload
                 }
               }

               Postgrex.query!(
                 conn,
                 "INSERT INTO telixo_outbox (event_id, service_name, tenant_id, event_type, payload) VALUES ($1, $2, $3, $4, $5::jsonb)",
                 [record_id, @service, tenant_id, event["event_type"], Jason.encode!(event)]
               )

               {:ok, record, :created}

             [] ->
               existing_sql = """
               SELECT record_id, service_name, tenant_id, kind, state, idempotency_key,
                      payload::text, created_at, updated_at
               FROM telixo_service_records
               WHERE service_name = $1 AND tenant_id = $2 AND kind = $3 AND idempotency_key = $4
               """

               case Postgrex.query!(conn, existing_sql, [
                      @service,
                      tenant_id,
                      kind,
                      idempotency_key
                    ]).rows do
                 [row] ->
                   existing = decode_row(row)
                   if existing.payload == payload,
                     do: {:ok, existing, :duplicate},
                     else: {:error, :conflict}

                 [] ->
                   {:error, :conflict}
               end
           end
         end) do
      {:ok, result} -> result
      {:error, _reason} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def get(tenant_id, record_id) when is_binary(tenant_id) and is_binary(record_id) do
    sql = """
    SELECT record_id, service_name, tenant_id, kind, state, idempotency_key,
           payload::text, created_at, updated_at
    FROM telixo_service_records
    WHERE service_name = $1 AND tenant_id = $2 AND record_id = $3
    """

    case Postgrex.query(@connection, sql, [@service, tenant_id, record_id]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_row(row)}
      {:ok, %{rows: []}} -> {:error, :not_found}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def transition(tenant_id, record_id, expected_state, next_state)
      when is_binary(tenant_id) and is_binary(record_id) and is_binary(expected_state) and
             is_binary(next_state) do
    sql = """
    UPDATE telixo_service_records
    SET state = $1, updated_at = now()
    WHERE service_name = $2 AND tenant_id = $3 AND record_id = $4 AND state = $5
    RETURNING record_id, service_name, tenant_id, kind, state, idempotency_key,
              payload::text, created_at, updated_at
    """

    case Postgrex.query(@connection, sql, [
           next_state,
           @service,
           tenant_id,
           record_id,
           expected_state
         ]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_row(row)}
      {:ok, %{rows: []}} ->
        case get(tenant_id, record_id) do
          {:ok, _} -> {:error, :conflict}
          error -> error
        end

      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def claim_outbox(limit \\ 50) when is_integer(limit) and limit > 0 and limit <= 500 do
    sql = """
    WITH candidates AS (
      SELECT event_id
      FROM telixo_outbox
      WHERE service_name = $1 AND status = 'pending' AND next_attempt_at <= now()
      ORDER BY created_at
      FOR UPDATE SKIP LOCKED
      LIMIT $2
    )
    UPDATE telixo_outbox AS outbox
    SET status = 'in_progress', attempts = outbox.attempts + 1, updated_at = now()
    FROM candidates
    WHERE outbox.event_id = candidates.event_id
    RETURNING outbox.event_id, outbox.tenant_id, outbox.event_type,
              outbox.payload::text, outbox.attempts
    """

    case Postgrex.query(@connection, sql, [@service, limit]) do
      {:ok, %{rows: rows}} -> {:ok, Enum.map(rows, &decode_outbox/1)}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def acknowledge_outbox(tenant_id, event_id)
      when is_binary(tenant_id) and is_binary(event_id) do
    sql = """
    UPDATE telixo_outbox
    SET status = 'delivered', delivered_at = now(), updated_at = now(), last_error = NULL
    WHERE service_name = $1 AND tenant_id = $2 AND event_id = $3 AND status = 'in_progress'
    """

    case Postgrex.query(@connection, sql, [@service, tenant_id, event_id]) do
      {:ok, %{num_rows: 1}} -> :ok
      {:ok, %{num_rows: 0}} -> {:error, :conflict}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def fail_outbox(tenant_id, event_id, retry_at_unix, reason)
      when is_binary(tenant_id) and is_binary(event_id) and is_integer(retry_at_unix) and
             is_binary(reason) do
    sql = """
    UPDATE telixo_outbox
    SET status = CASE WHEN attempts >= 8 THEN 'dead_lettered' ELSE 'pending' END,
        next_attempt_at = to_timestamp($4),
        last_error = left($5, 1000),
        updated_at = now()
    WHERE service_name = $1 AND tenant_id = $2 AND event_id = $3 AND status = 'in_progress'
    """

    case Postgrex.query(@connection, sql, [
           @service,
           tenant_id,
           event_id,
           retry_at_unix,
           reason
         ]) do
      {:ok, %{num_rows: 1}} -> :ok
      {:ok, %{num_rows: 0}} -> {:error, :conflict}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  defp decode_outbox([event_id, tenant_id, event_type, payload, attempts]) do
    %{
      event_id: event_id,
      tenant_id: tenant_id,
      event_type: event_type,
      payload: Jason.decode!(payload),
      attempts: attempts
    }
  end

  defp decode_row([id, service, tenant, kind, state, key, payload, created, updated]) do
    %{
      record_id: id,
      service_name: service,
      tenant_id: tenant,
      kind: kind,
      state: state,
      idempotency_key: key,
      payload: Jason.decode!(payload),
      created_at: DateTime.to_iso8601(created),
      updated_at: DateTime.to_iso8601(updated)
    }
  end
end
