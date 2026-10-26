defmodule PesaGuard.AuditEventService.AdminController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.AuditEventService.Persistence.AuditControls
  alias PesaGuard.AuditEventService.Persistence.AuditLedger

  def get_retention_policy(conn, _params) do
    with {:ok, tenant_id, actor_id, reason, request_id} <- privileged_context(conn),
         :ok <- AuditControls.log_privileged_access(tenant_id, actor_id, "audit.retention_policy_read", reason, request_id),
         {:ok, policy} <- AuditControls.get_retention_policy(tenant_id) do
      json(conn, %{data: policy})
    else
      {:error, :forbidden} -> conn |> put_status(:forbidden) |> json(%{error: "privileged_role_required"})
      {:error, :reason_required} -> conn |> put_status(:bad_request) |> json(%{error: "audit_reason_required"})
      {:error, :unavailable} -> conn |> put_status(:service_unavailable) |> json(%{error: "audit_controls_unavailable"})
      _ -> conn |> put_status(:service_unavailable) |> json(%{error: "audit_controls_unavailable"})
    end
  end

  def update_retention_policy(conn, params) do
    with {:ok, tenant_id, actor_id, reason, request_id} <- privileged_context(conn),
         days when is_integer(days) <- Map.get(params, "retention_days"),
         legal_hold when is_boolean(legal_hold) <- Map.get(params, "legal_hold"),
         {:ok, policy} <- AuditControls.set_retention_policy(tenant_id, days, legal_hold, actor_id, reason, request_id) do
      json(conn, %{data: policy})
    else
      {:error, :forbidden} -> conn |> put_status(:forbidden) |> json(%{error: "privileged_role_required"})
      {:error, :reason_required} -> conn |> put_status(:bad_request) |> json(%{error: "audit_reason_required"})
      {:error, :invalid_policy} -> conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_retention_policy"})
      {:error, :unavailable} -> conn |> put_status(:service_unavailable) |> json(%{error: "audit_controls_unavailable"})
      _ -> conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_retention_policy"})
    end
  end

  def verify_integrity(conn, _params) do
    with {:ok, tenant_id, actor_id, reason, request_id} <- privileged_context(conn),
         :ok <- AuditControls.log_privileged_access(tenant_id, actor_id, "audit.integrity_verification_requested", reason, request_id) do
      case AuditLedger.verify_chain(tenant_id) do
        :ok -> json(conn, %{data: %{tenant_id: tenant_id, status: "verified", mode: "online"}})
        {:error, {:integrity_violation, event_id}} ->
          conn |> put_status(:conflict) |> json(%{error: "integrity_violation", event_id: event_id})
        {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "integrity_verification_unavailable"})
      end
    else
      {:error, :forbidden} -> conn |> put_status(:forbidden) |> json(%{error: "privileged_role_required"})
      {:error, :reason_required} -> conn |> put_status(:bad_request) |> json(%{error: "audit_reason_required"})
      _ -> conn |> put_status(:service_unavailable) |> json(%{error: "audit_controls_unavailable"})
    end
  end

  defp privileged_context(conn) do
    tenant = conn.assigns.tenant_context
    claims = tenant.claims || %{}
    roles = Map.get(claims, "roles", [])
    actor = tenant.subject
    reason = conn |> Plug.Conn.get_req_header("x-audit-reason") |> List.first()
    request_id = conn |> Plug.Conn.get_req_header("x-request-id") |> List.first() || random_id()

    cond do
      not is_list(roles) or Enum.empty?(roles) or
          not Enum.any?(roles, &(&1 in ["audit_admin", "audit_compliance", "platform_security_admin"])) ->
        {:error, :forbidden}

      not is_binary(actor) or actor == "" ->
        {:error, :forbidden}

      not is_binary(reason) or byte_size(String.trim(reason)) < 10 or byte_size(reason) > 500 ->
        {:error, :reason_required}

      true ->
        {:ok, tenant.tenant_id, actor, String.trim(reason), request_id}
    end
  end

  defp random_id, do: Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false)
end
