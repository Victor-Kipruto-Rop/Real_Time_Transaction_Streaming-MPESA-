defmodule PesaGuard.WebhookDelivery.DeliveryRequest do
  @moduledoc """
  Builds deterministic, signed customer-webhook HTTP requests.

  This module does not perform network I/O or persist delivery attempts. Callers
  must durably claim a delivery before dispatch and record the response through
  the delivery lifecycle.
  """

  alias PesaGuard.WebhookDelivery.Domain.Processor
  alias PesaGuard.WebhookDelivery.Signing

  @spec build(map(), map(), integer()) ::
          {:ok, %{url: binary(), body: binary(), headers: [{binary(), binary()}], delivery_id: binary()}}
          | {:error, term()}
  def build(subscription, event, timestamp \\ System.system_time(:second))

  def build(%{"id" => subscription_id, "target_url" => target_url, "secret" => secret}, event, timestamp)
      when is_binary(subscription_id) and byte_size(subscription_id) > 0 and
             is_binary(target_url) and is_binary(secret) and is_map(event) and
             is_integer(timestamp) do
    event_id = Map.get(event, "event_id")
    payload = %{"event" => event}

    with true <- is_binary(event_id) and byte_size(event_id) > 0,
         {:ok, _validated} <- Processor.prepare(%{"target_url" => target_url, "payload" => payload}),
         {:ok, body} <- Jason.encode(payload),
         delivery_id <- stable_delivery_id(subscription_id, event_id),
         {:ok, headers} <- Signing.headers(delivery_id, secret, body, timestamp) do
      {:ok, %{url: target_url, body: body, headers: headers, delivery_id: delivery_id}}
    else
      false -> {:error, :event_id_required}
      {:error, reason} -> {:error, reason}
    end
  end

  def build(_, _, _), do: {:error, :invalid_subscription_or_event}

  defp stable_delivery_id(subscription_id, event_id) do
    :crypto.hash(:sha256, subscription_id <> ":" <> event_id)
    |> Base.url_encode64(padding: false)
  end
end
