defmodule PesaGuard.DataExportService.Persistence.MigrationRunner do
  @moduledoc """
  Applies immutable, checksummed SQL migrations before the service accepts traffic.
  Each standalone service records its own applied migration versions.
  """

  @migration_table """
  CREATE TABLE IF NOT EXISTS telixo_schema_migrations (
    service_name TEXT NOT NULL,
    version TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (service_name, version)
  )
  """

  @spec run(atom() | pid(), binary(), atom()) :: :ok | {:error, term()}
  def run(connection, service_name, app) when is_binary(service_name) and is_atom(app) do
    try do
      Postgrex.query!(connection, @migration_table, [])
      migration_dir = Application.app_dir(app, "priv/migrations")

      migration_dir
      |> File.ls!()
      |> Enum.filter(&String.ends_with?(&1, ".sql"))
      |> Enum.sort()
      |> Enum.reduce_while(:ok, fn filename, :ok ->
        path = Path.join(migration_dir, filename)
        sql = File.read!(path)
        version = filename |> String.split("_", parts: 2) |> hd()
        checksum = :crypto.hash(:sha256, sql) |> Base.encode16(case: :lower)

        case Postgrex.transaction(connection, fn conn ->
               apply_migration(conn, service_name, version, checksum, sql)
             end) do
          {:ok, _result} -> {:cont, :ok}
          {:error, reason} -> {:halt, {:error, {:migration_failed, version, reason}}}
        end
      end)
    rescue
      error -> {:error, {:migration_runner_failed, error}}
    catch
      :exit, reason -> {:error, {:migration_runner_exit, reason}}
    end
  end

  defp apply_migration(conn, service_name, version, checksum, sql) do
    # Serialize migration application across service replicas and shared schemas.
    Postgrex.query!(conn, "SELECT pg_advisory_xact_lock(73194021, 1)", [])

    case Postgrex.query!(conn,
           "SELECT checksum FROM telixo_schema_migrations WHERE service_name = $1 AND version = $2",
           [service_name, version]
         ).rows do
      [[^checksum]] ->
        :already_applied

      [[_different_checksum]] ->
        raise "migration checksum mismatch for #{service_name}/#{version}; applied migrations are immutable"

      [] ->
        sql
        |> String.split(";")
        |> Enum.map(&String.trim/1)
        |> Enum.reject(&(&1 == ""))
        |> Enum.each(&Postgrex.query!(conn, &1, []))

        Postgrex.query!(
          conn,
          "INSERT INTO telixo_schema_migrations (service_name, version, checksum) VALUES ($1, $2, $3)",
          [service_name, version, checksum]
        )

        :applied
    end
  end
end
