defmodule TELIXO.IntegrationHealthService.Contracts.EventTest do
  use ExUnit.Case, async: true
  alias TELIXO.IntegrationHealthService.Contracts.Event
  test "accepts a valid versioned event" do
    assert {:ok, _} = Event.validate(%{"event_id" => "evt-1", "tenant_id" => "t-1", "event_type" => "example.created", "occurred_at" => "2026-01-01T00:00:00Z", "schema_version" => 1, "payload" => %{}})
  end
  test "rejects invalid envelope and payload" do
    assert {:error, {:invalid_event, errors}} = Event.validate(%{"payload" => []})
    assert "event_id" in errors
    assert "payload" in errors
  end
end