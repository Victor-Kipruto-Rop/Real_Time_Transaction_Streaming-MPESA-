defmodule PesaGuard.IncidentManagementService.RecordsController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.IncidentManagementService.Domain.Service
  alias PesaGuard.IncidentManagementService.Persistence.PostgresStore

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

        case Service.validate_command(command) do
          {:ok, validated} ->
            case PostgresStore.insert_once(
                   tenant_id,
                   kind,
                   idempotency_key,
                   Service.initial_state(),
                   validated
                 ) do
              {:ok, record, :created} ->
                conn |> put_status(:created) |> json(%{data: record, idempotent_replay: false})

              {:ok, record, :duplicate} ->
                json(conn, %{data: record, idempotent_replay: true})

              {:error, :unavailable} ->
                conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})

              {:error, _} ->
                conn |> put_status(:conflict) |> json(%{error: "idempotency_conflict"})
            end

          {:error, {:missing_fields, fields}} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_command", fields: fields})
        end
    end
  end

  def show(conn, %{"id" => id}) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case PostgresStore.get(tenant_id, id) do
      {:ok, record} -> json(conn, %{data: record})
      {:error, :not_found} -> conn |> put_status(:not_found) |> json(%{error: "not_found"})
      {:error, :unavailable} -> conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
    end
  end

  def transition(conn, %{"id" => id, "state" => next_state}) when is_binary(next_state) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    with {:ok, current} <- PostgresStore.get(tenant_id, id),
         true <- Service.transition_allowed?(current.state, next_state),
         {:ok, updated} <- PostgresStore.transition(tenant_id, id, current.state, next_state) do
      json(conn, %{data: updated})
    else
      {:error, :not_found} ->
        conn |> put_status(:not_found) |> json(%{error: "not_found"})

      {:error, :unavailable} ->
        conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})

      {:error, :conflict} ->
        conn |> put_status(:conflict) |> json(%{error: "state_conflict"})

      false ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_state_transition"})

      _ ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_state_transition"})
    end
  end

  def transition(conn, _params) do
    conn |> put_status(:bad_request) |> json(%{error: "state_required"})
  end

  defp valid_key?(key), do: is_binary(key) and byte_size(key) in 1..200
  defp valid_kind?(kind), do: is_binary(kind) and byte_size(kind) in 1..80
end
