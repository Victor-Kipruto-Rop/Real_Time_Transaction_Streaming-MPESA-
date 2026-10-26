defmodule PesaGuard.WebhookDelivery.CustomerWebhooksController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.WebhookDelivery.CustomerDeliveryStore

  def create_subscription(conn, params) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    with true <- not supplied_tenant_mismatch?(params, tenant_id),
         target when is_binary(target) <- Map.get(params, "target_url"),
         event_types when is_list(event_types) <- Map.get(params, "event_types"),
         secret when is_binary(secret) <- Map.get(params, "secret"),
         {:ok, subscription} <- CustomerDeliveryStore.create_subscription(tenant_id, target, event_types, secret) do
      conn |> put_status(:created) |> json(%{data: subscription})
    else
      false -> conn |> put_status(:forbidden) |> json(%{error: "tenant_mismatch"})
      {:error, :invalid_secret} -> conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_secret"})
      {:error, :encryption_key_missing} -> conn |> put_status(:service_unavailable) |> json(%{error: "webhook_secret_encryption_unavailable"})
      {:error, :encryption_key_invalid} -> conn |> put_status(:service_unavailable) |> json(%{error: "webhook_secret_encryption_unavailable"})
      {:error, :target_url_must_use_https} -> conn |> put_status(:unprocessable_entity) |> json(%{error: "https_required"})
      {:error, reason} -> conn |> put_status(:unprocessable_entity) |> json(%{error: safe_error(reason)})
      _ -> conn |> put_status(:bad_request) |> json(%{error: "invalid_subscription"})
    end
  end

  def list_subscriptions(conn, _params) do
    tenant_id = conn.assigns.tenant_context.tenant_id
    case CustomerDeliveryStore.list_subscriptions(tenant_id) do
      {:ok, subscriptions} -> json(conn, %{data: subscriptions})
      {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
    end
  end

  def enqueue_event(conn, params) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    with true <- not supplied_tenant_mismatch?(params, tenant_id),
         event_id when is_binary(event_id) <- Map.get(params, "event_id"),
         event_type when is_binary(event_type) <- Map.get(params, "event_type"),
         true <- is_integer(Map.get(params, "schema_version")) and is_map(Map.get(params, "payload")),
         event <- Map.drop(params, ["tenant_id"]),
         event <- Map.put(event, "tenant_id", tenant_id),
         {:ok, delivery_ids} <- CustomerDeliveryStore.enqueue_event(tenant_id, event) do
      conn |> put_status(:accepted) |> json(%{data: %{event_id: event_id, queued_count: length(delivery_ids)}})
    else
      false -> conn |> put_status(:forbidden) |> json(%{error: "tenant_mismatch_or_invalid_event"})
      {:error, :invalid_event} -> conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_event"})
      {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
      _ -> conn |> put_status(:bad_request) |> json(%{error: "invalid_event"})
    end
  end

  def show_delivery(conn, %{"id" => id}) do
    tenant_id = conn.assigns.tenant_context.tenant_id
    case CustomerDeliveryStore.get_delivery(tenant_id, id) do
      {:ok, delivery} -> json(conn, %{data: delivery})
      {:error, :not_found} -> conn |> put_status(:not_found) |> json(%{error: "not_found"})
      {:error, _} -> conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
    end
  end

  defp supplied_tenant_mismatch?(params, tenant_id) do
    case Map.get(params, "tenant_id") do
      nil -> false
      supplied -> supplied != tenant_id
    end
  end

  defp safe_error(reason) when is_atom(reason), do: Atom.to_string(reason)
  defp safe_error(_), do: "invalid_subscription"
end
