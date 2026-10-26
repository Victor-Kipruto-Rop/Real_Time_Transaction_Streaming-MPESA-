defmodule PesaGuard.NotificationService.RecordsController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.NotificationService.Domain.Processor
  alias PesaGuard.NotificationService.Domain.Service
  alias PesaGuard.NotificationService.Persistence.PostgresStore
  alias PesaGuard.NotificationService.Persistence.PolicyStore

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
             {:ok, prepared} <- Processor.prepare(validated),
             :ok <- PolicyStore.authorize(tenant_id, prepared) do
          persist(conn, tenant_id, kind, idempotency_key, prepared)
        else
          {:error, reason} when reason in [:consent_record_unavailable, :consent_not_granted, :consent_purpose_missing, :channel_preference_disabled, :recipient_suppressed] ->
            conn |> put_status(:forbidden) |> json(%{error: "notification_policy_denied", reason: Atom.to_string(reason)})

          {:error, reason} when reason in [:policy_store_unavailable, :policy_record_unavailable] ->
            conn |> put_status(:service_unavailable) |> json(%{error: "notification_policy_unavailable"})

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

      {:error, reason} when reason in [:consent_record_unavailable, :consent_not_granted, :consent_purpose_missing, :channel_preference_disabled, :recipient_suppressed] ->
        conn |> put_status(:forbidden) |> json(%{error: "notification_policy_denied", reason: Atom.to_string(reason)})

      {:error, reason} when reason in [:policy_store_unavailable, :policy_record_unavailable, :unavailable] ->
        conn |> put_status(:service_unavailable) |> json(%{error: "notification_policy_or_persistence_unavailable"})

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

  defp persist(conn, tenant_id, kind, idempotency_key, prepared) do
    case PostgresStore.insert_once(
           tenant_id,
           kind,
           idempotency_key,
           Service.initial_state(),
           prepared
         ) do
      {:ok, record, :created} ->
        conn |> put_status(:created) |> json(%{data: record, idempotent_replay: false})

      {:ok, record, :duplicate} ->
        json(conn, %{data: record, idempotent_replay: true})

      {:error, :unavailable} ->
        conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})

      {:error, :conflict} ->
        conn |> put_status(:conflict) |> json(%{error: "idempotency_conflict"})

      {:error, _} ->
        conn |> put_status(:conflict) |> json(%{error: "idempotency_conflict"})
    end
  end

  defp valid_key?(key), do: is_binary(key) and byte_size(key) in 1..200
  defp valid_kind?(kind), do: is_binary(kind) and byte_size(kind) in 1..80
end
