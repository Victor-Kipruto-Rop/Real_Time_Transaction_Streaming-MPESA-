defmodule PesaGuard.WebhookDelivery.CustomerWebhooksController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStore

  def index(conn, _params) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case CustomerWebhookStore.list_subscriptions(tenant_id) do
      {:ok, subscriptions} -> json(conn, %{data: subscriptions})
      {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
    end
  end

  def create(conn, params) do
    tenant_id = conn.assigns.tenant_context.tenant_id
    idempotency_key = conn |> Plug.Conn.get_req_header("idempotency-key") |> List.first()

    cond do
      not valid_key?(idempotency_key) ->
        conn |> put_status(:bad_request) |> json(%{error: "idempotency_key_required"})

      true ->
        case CustomerWebhookStore.create_subscription(
               tenant_id,
               idempotency_key,
               Map.get(params, "target_url"),
               Map.get(params, "event_types"),
               Map.get(params, "secret")
             ) do
          {:ok, subscription, :created} ->
            conn |> put_status(:created) |> json(%{data: subscription, idempotent_replay: false})

          {:ok, subscription, :duplicate} ->
            json(conn, %{data: subscription, idempotent_replay: true})

          {:error, :invalid_event_types} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_event_types"})

          {:error, :invalid_secret} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "secret_must_be_at_least_32_bytes"})

          {:error, :target_url_must_use_https} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "target_url_must_use_https"})

          {:error, :encryption_key_not_configured} ->
            conn |> put_status(:service_unavailable) |> json(%{error: "webhook_secret_encryption_unavailable"})

          {:error, :encryption_key_must_be_base64_32_bytes} ->
            conn |> put_status(:service_unavailable) |> json(%{error: "webhook_secret_encryption_unavailable"})

          {:error, :idempotency_conflict} ->
            conn |> put_status(:conflict) |> json(%{error: "idempotency_conflict"})

          {:error, :invalid_subscription} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_subscription"})

          {:error, _} ->
            conn |> put_status(:service_unavailable) |> json(%{error: "subscription_persistence_unavailable"})
        end
    end
  end

  def fanout(conn, %{"event_id" => event_id, "event_type" => event_type, "payload" => payload})
      when is_binary(event_id) and byte_size(event_id) in 1..200 and
             is_binary(event_type) and byte_size(event_type) in 1..160 and is_map(payload) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case CustomerWebhookStore.enqueue_for_event(tenant_id, event_id, event_type, payload) do
      {:ok, deliveries} ->
        conn |> put_status(:accepted) |> json(%{data: deliveries, accepted: length(deliveries)})

      {:error, {:fanout_incomplete, _reason}} ->
        conn |> put_status(:service_unavailable) |> json(%{error: "event_fanout_incomplete", retryable: true})

      {:error, :unavailable} ->
        conn |> put_status(:service_unavailable) |> json(%{error: "delivery_queue_unavailable"})

      {:error, _} ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_event"})
    end
  end

  def fanout(conn, _params) do
    conn |> put_status(:bad_request) |> json(%{error: "event_id_event_type_and_object_payload_required"})
  end

  def enqueue(conn, %{"subscription_id" => subscription_id} = params) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case CustomerWebhookStore.enqueue(
           tenant_id,
           subscription_id,
           Map.get(params, "event_id"),
           Map.get(params, "event_type"),
           Map.get(params, "payload")
         ) do
      {:ok, delivery, :created} ->
        conn |> put_status(:accepted) |> json(%{data: delivery, idempotent_replay: false})

      {:ok, delivery, :duplicate} ->
        json(conn, %{data: delivery, idempotent_replay: true})

      {:error, :not_found} ->
        conn |> put_status(:not_found) |> json(%{error: "subscription_not_found"})

      {:error, :subscription_inactive_or_event_not_allowed} ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "subscription_inactive_or_event_not_allowed"})

      {:error, :event_conflict} ->
        conn |> put_status(:conflict) |> json(%{error: "event_id_payload_conflict"})

      {:error, :invalid_delivery} ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_delivery"})

      {:error, _} ->
        conn |> put_status(:service_unavailable) |> json(%{error: "delivery_queue_unavailable"})
    end
  end

  def enqueue(conn, _params) do
    conn |> put_status(:bad_request) |> json(%{error: "subscription_id_required"})
  end

  def history(conn, %{"subscription_id" => subscription_id}) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case CustomerWebhookStore.list_deliveries(tenant_id, subscription_id) do
      {:ok, deliveries} -> json(conn, %{data: deliveries})
      {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "delivery_history_unavailable"})
    end
  end

  def history(conn, %{"subscription_id" => subscription_id}) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    case CustomerWebhookStore.list_deliveries(tenant_id, subscription_id) do
      {:ok, deliveries} -> json(conn, %{data: deliveries})
      {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "delivery_history_unavailable"})
    end
  end

  def history(conn, _params) do
    conn |> put_status(:bad_request) |> json(%{error: "subscription_id_required"})
  end

  defp valid_key?(key), do: is_binary(key) and byte_size(key) in 1..200
end
