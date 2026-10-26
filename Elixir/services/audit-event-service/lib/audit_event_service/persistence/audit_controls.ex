defmodule PesaGuard.AuditEventService.Persistence.AuditControls do
  @moduledoc """
  Tenant-scoped retention policy and append-only privileged-access history.

  HTTP callers must be authorized by AdminController before invoking mutations.
  Retention policy changes are metadata only; physical expiry/purge must be
  performed by the separately authorized archive/retention executor.
  """

  @connection PesaGuard.AuditEventService.Persistence.PostgresConnection

  def get_retention_policy(tenant_id) when is_binary(tenant_id) do
    case Postgrex.query(@connection, """
         SELECT tenant_id, retention_days, legal_hold, updated_by, updated_at
         FROM telixo_audit_retention_policies
         WHERE tenant_id = $1
         """, [tenant_id]) do
      {:ok, %{rows: [row]}} -> {:ok, decode_policy(row)}
      {:ok, %{rows: []}} -> {:ok, %{tenant_id: tenant_id, retention_days: 2555, legal_hold: false, configured: false}}
      {:error, _} -> {:error, :unavailable}
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def get_retention_policy(_), do: {:error, :invalid_tenant}

  def set_retention_policy(tenant_id, days, legal_hold, actor_id, reason, request_id)
      when is_binary(tenant_id) and is_integer(days) and days in 30..36500 and
             is_boolean(legal_hold) and is_binary(actor_id) and is_binary(reason) and
             is_binary(request_id) do
    with :ok <- validate_audit_context(actor_id, reason, request_id) do
      access_id = random_id()

      result =
        Postgrex.transaction(@connection, fn conn ->
          Postgrex.query!(conn, """
          INSERT INTO telixo_audit_retention_policies
            (tenant_id, retention_days, legal_hold, updated_by)
          VALUES ($1, $2, $3, $4)
          ON CONFLICT (tenant_id) DO UPDATE
            SET retention_days = EXCLUDED.retention_days,
                legal_hold = EXCLUDED.legal_hold,
                updated_by = EXCLUDED.updated_by,
                updated_at = now()
          RETURNING tenant_id, retention_days, legal_hold, updated_by, updated_at
          """, [tenant_id, days, legal_hold, actor_id]).rows
          |> then(fn [row] -> decode_policy(row) end)

          insert_access_log(conn, access_id, tenant_id, actor_id, "audit.retention_policy_updated", reason, request_id)
        end)

      case result do
        {:ok, policy} -> {:ok, policy}
        {:error, _} -> {:error, :unavailable}
      end
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def set_retention_policy(_, _, _, _, _, _), do: {:error, :invalid_policy}

  def log_privileged_access(tenant_id, actor_id, action, reason, request_id)
      when is_binary(tenant_id) and is_binary(actor_id) and is_binary(action) and
             is_binary(reason) and is_binary(request_id) do
    with :ok <- validate_audit_context(actor_id, reason, request_id) do
      case Postgrex.query(@connection, """
           INSERT INTO telixo_audit_privileged_access_log
             (access_id, tenant_id, actor_id, action, reason, request_id)
           VALUES ($1, $2, $3, $4, $5, $6)
           """, [random_id(), tenant_id, actor_id, action, reason, request_id]) do
        {:ok, _} -> :ok
        {:error, _} -> {:error, :unavailable}
      end
    end
  rescue
    _ -> {:error, :unavailable}
  end

  def log_privileged_access(_, _, _, _, _), do: {:error, :invalid_audit_context}

  defp insert_access_log(conn, access_id, tenant_id, actor_id, action, reason, request_id) do
    Postgrex.query!(conn, """
    INSERT INTO telixo_audit_privileged_access_log
      (access_id, tenant_id, actor_id, action, reason, request_id)
    VALUES ($1, $2, $3, $4, $5, $6)
    """, [access_id, tenant_id, actor_id, action, reason, request_id])
  end

  defp validate_audit_context(actor, reason, request_id) do
    if byte_size(actor) in 1..200 and byte_size(String.trim(reason)) in 10..500 and
         byte_size(request_id) in 1..200,
      do: :ok,
      else: {:error, :invalid_audit_context}
  end

  defp decode_policy([tenant_id, days, legal_hold, updated_by, updated_at]) do
    %{
      tenant_id: tenant_id,
      retention_days: days,
      legal_hold: legal_hold,
      updated_by: updated_by,
      updated_at: DateTime.to_iso8601(updated_at),
      configured: true
    }
  end

  defp random_id, do: Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)
end
