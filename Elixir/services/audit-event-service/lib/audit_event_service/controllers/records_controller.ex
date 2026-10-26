defmodule PesaGuard.AuditEventService.RecordsController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.AuditEventService.Domain.Processor
  alias PesaGuard.AuditEventService.Domain.Service
  alias PesaGuard.AuditEventService.Persistence.AuditLedger

  def create(conn, params) do
    tenant_id = conn.assigns.tenant_context.tenant_id
    supplied_tenant = Map.get(params, "tenant_id")
    idempotency_key = conn |> Plug.Conn.get_req_header("idempotency-key") |> List.first()
    kind = Map.get(params, "record_type", "default")

    cond do
      is_binary(supplied_tenant) and supplied_tenant != tenant_id ->
        conn |> put_status(:forbidden) |> json(%{error: "tenant_mismatch"})

      not valid_key?(idempotency_key) ->
        conn |> put_status(:bad_request) |> json(%{error: "idempotency_key_required"})

      not valid_kind?(kind) ->
        conn |> put_status(:bad_request) |> json(%{error: "invalid_record_type"})

      true ->
        command = params |> Map.put("tenant_id", tenant_id) |> Map.drop(["record_type"])

        with {:ok, validated} <- Service.validate_command(command),
             {:ok, prepared} <- Processor.prepare(validated) do
          persist(conn, tenant_id, kind, idempotency_key, prepared)
        else
          {:error, {:missing_fields, fields}} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_command", fields: fields})

          {:error, reason} ->
            conn
            |> put_status(:unprocessable_entity)
            |> json(%{error: "invalid_command", reason: to_string(reason)})
        end
    end
  end

  def show(conn, %{"id" => id}) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case AuditLedger.get(tenant_id, id) do
      {:ok, event} -> json(conn, %{data: event})
      {:error, :not_found} -> conn |> put_status(:not_found) |> json(%{error: "not_found"})
      {:error, :unavailable} -> conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
    end
  end

  def transition(conn, _params) do
    conn |> put_status(:method_not_allowed) |> json(%{error: "audit_events_are_append_only"})
  end

  defp persist(conn, tenant_id, _kind, idempotency_key, prepared) do
    case AuditLedger.append(tenant_id, idempotency_key, prepared) do
      {:ok, event, :created} ->
        conn |> put_status(:created) |> json(%{data: event, idempotent_replay: false})

      {:ok, event, :duplicate} ->
        json(conn, %{data: event, idempotent_replay: true})

      {:error, :unavailable} ->
        conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})

      {:error, :conflict} ->
        conn |> put_status(:conflict) |> json(%{error: "idempotency_conflict"})

      {:error, _reason} ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_audit_event"})
    end
  end

  defp valid_key?(key), do: is_binary(key) and byte_size(key) in 1..200
  defp valid_kind?(kind), do: is_binary(kind) and byte_size(kind) in 1..80
end
