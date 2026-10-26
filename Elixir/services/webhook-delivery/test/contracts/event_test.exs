defmodule PesaGuard.WebhookDelivery.Contracts.EventTest do
  use ExUnit.Case, async: true
  alias PesaGuard.WebhookDelivery.Contracts.Event

  test "rejects incomplete events" do
    assert {:error, {:invalid_event, fields}} = Event.validate(%{})
    assert fields != []
  end

  test "accepts a valid versioned event" do
    event = %{
      "event_id" => "event-1",
      "tenant_id" => "tenant-1",
      "event_type" => "test.created",
      "occurred_at" => "2026-01-01T00:00:00Z",
      "schema_version" => 1,
      "payload" => %{}
    }

    assert {:ok, ^event} = Event.validate(event)
  end
end
