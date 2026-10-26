defmodule PesaGuard.WebhookDelivery.DeliveryRequestTest do
  use ExUnit.Case, async: true

  alias PesaGuard.WebhookDelivery.DeliveryRequest
  alias PesaGuard.WebhookDelivery.Signing

  @secret String.duplicate("w", 32)
  @subscription %{
    "id" => "subscription-42",
    "target_url" => "https://merchant.example.test/hooks",
    "secret" => @secret
  }
  @event %{
    "event_id" => "evt-123",
    "event_type" => "reconciliation.completed",
    "schema_version" => 1
  }

  test "builds a signed request with deterministic delivery identity" do
    assert {:ok, first} = DeliveryRequest.build(@subscription, @event, 1_800_000_000)
    assert {:ok, second} = DeliveryRequest.build(@subscription, @event, 1_800_000_000)
    assert first.delivery_id == second.delivery_id
    assert first.url == @subscription["target_url"]
    assert {"x-telixo-delivery-id", first.delivery_id} in first.headers

    timestamp = Enum.find(first.headers, &(elem(&1, 0) == "x-telixo-timestamp")) |> elem(1)
    signature = Enum.find(first.headers, &(elem(&1, 0) == "x-telixo-signature")) |> elem(1)
    assert :ok = Signing.verify(@secret, timestamp, signature, first.body, 1_800_000_000)
  end

  test "rejects an unsafe target and events without an ID" do
    unsafe = Map.put(@subscription, "target_url", "http://merchant.example.test/hooks")
    assert {:error, :target_url_must_use_https} = DeliveryRequest.build(unsafe, @event, 1)

    assert {:error, :event_id_required} =
             DeliveryRequest.build(@subscription, Map.delete(@event, "event_id"), 1)
  end

  test "rejects weak signing secrets" do
    weak = Map.put(@subscription, "secret", "short")
    assert {:error, :invalid_secret} = DeliveryRequest.build(weak, @event, 1)
  end
end
