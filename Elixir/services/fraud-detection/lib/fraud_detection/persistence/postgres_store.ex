defmodule PesaGuard.FraudDetection.Persistence.PostgresStore do
  @moduledoc "PostgreSQL-backed tenant-scoped records with idempotency and guarded transitions."

  use GenServer

  @connection PesaGuard.FraudDetection.Persistence.PostgresConnection
  @service "fraud-detection"

  @schema """
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
  );
  CREATE INDEX IF NOT EXISTS telixo_service_records_tenant_created_idx
    ON telixo_service_records (service_name, tenant_id, created_at DESC);
  """

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def children do
    case System.get_env("DATABASE_URL") do
      url when is_binary(url) and url != "" ->
        [Supervisor.child_spec({__MODULE__, []}, id: __MODULE__)]

      _ when Application.get_env(:fraud_detection, :environment) == :prod ->
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
        case Postgrex.query(@connection, @schema, []) do
          {:ok, _result} -> {:ok, %{connected: true}}
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

    sql = """
    INSERT INTO telixo_service_records
      (record_id, service_name, tenant_id, kind, state, idempotency_key, payload)
    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
    ON CONFLICT (service_name, tenant_id, kind, idempotency_key) DO NOTHING
    RETURNING record_id, service_name, tenant_id, kind, state, idempotency_key,
              payload::text, created_at, updated_at
    """

    case Postgrex.query(@connection, sql, [
           record_id,
           @service,
           tenant_id,
           kind,
           state,
           idempotency_key,
           encoded_payload
         ]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_row(row), :created}
      {:ok, %{rows: []}} -> fetch_by_idempotency(tenant_id, kind, idempotency_key)
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

  defp fetch_by_idempotency(tenant_id, kind, idempotency_key) do
    sql = """
    SELECT record_id, service_name, tenant_id, kind, state, idempotency_key,
           payload::text, created_at, updated_at
    FROM telixo_service_records
    WHERE service_name = $1 AND tenant_id = $2 AND kind = $3 AND idempotency_key = $4
    """

    case Postgrex.query(@connection, sql, [@service, tenant_id, kind, idempotency_key]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_row(row), :duplicate}
      {:ok, %{rows: []}} -> {:error, :conflict}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
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
