defmodule PesaGuard.WebhookDelivery.CustomerWebhooksController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.WebhookDelivery.CustomerDeliveryStore

  def create_subscription(conn, params) do
    tenant_id = conn.assigns.tenant_context.tenant_id

    cond do
      supplied_tenant_mismatch?(params, tenant_id) ->
        conn |> put_status(:forbidden) |> json(%{error: "tenant_mismatch"})

      not is_binary(Map.get(params, "target_url")) or
          not is_list(Map.get(params, "event_types")) or
          not is_binary(Map.get(params, "secret")) ->
        conn |> put_status(:bad_request) |> json(%{error: "invalid_subscription"})

      true ->
        case CustomerDeliveryStore.create_subscription(
               tenant_id,
               params["target_url"],
               params["event_types"],
               params["secret"]
             ) do
          {:ok, subscription} ->
            conn |> put_status(:created) |> json(%{data: subscription})

          {:error, :invalid_secret} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_secret"})

          {:error, reason} when reason in [:encryption_key_missing, :encryption_key_invalid, :encryption_failed] ->
            conn |> put_status(:service_unavailable) |> json(%{error: "webhook_secret_encryption_unavailable"})

          {:error, reason} when reason in [
            :target_url_must_use_https,
            :target_url_host_required,
            :target_url_credentials_forbidden,
            :target_url_port_forbidden,
            :target_url_private_host_forbidden,
            :target_url_ip_literal_forbidden,
            :invalid_event_types
          ] ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: safe_error(reason)})

          {:error, _} ->
            conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
        end
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

    cond do
      supplied_tenant_mismatch?(params, tenant_id) ->
        conn |> put_status(:forbidden) |> json(%{error: "tenant_mismatch"})

      not valid_event_shape?(params) ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_event"})

      true ->
        event = params |> Map.drop(["tenant_id"]) |> Map.put("tenant_id", tenant_id)

        case CustomerDeliveryStore.enqueue_event(tenant_id, event) do
          {:ok, delivery_ids} ->
            conn |> put_status(:accepted) |> json(%{data: %{event_id: event["event_id"], queued_count: length(delivery_ids)}})

          {:error, :invalid_event} ->
            conn |> put_status(:unprocessable_entity) |> json(%{error: "invalid_event"})

          {:error, _} ->
            conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
        end
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

  defp valid_event_shape?(params) do
    is_binary(Map.get(params, "event_id")) and byte_size(params["event_id"]) in 1..200 and
      is_binary(Map.get(params, "event_type")) and
      is_integer(Map.get(params, "schema_version")) and params["schema_version"] > 0 and
      is_map(Map.get(params, "payload"))
  end

  defp supplied_tenant_mismatch?(params, tenant_id) do
    case Map.get(params, "tenant_id") do
      nil -> false
      supplied -> supplied != tenant_id
    end
  end

  defp safe_error(reason) when is_atom(reason), do: Atom.to_string(reason)
  defp safe_error(_), do: "invalid_request"
end
