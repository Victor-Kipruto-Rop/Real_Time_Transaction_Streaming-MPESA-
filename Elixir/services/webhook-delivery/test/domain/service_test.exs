defmodule PesaGuard.WebhookDelivery.Domain.ServiceTest do
  use ExUnit.Case, async: true
  alias PesaGuard.WebhookDelivery.Domain.Service

  test "rejects incomplete commands" do
    assert {:error, {:missing_fields, fields}} = Service.validate_command(%{})
    assert fields != []
  end

  test "accepts commands with required fields" do
    command = Map.new(["event_id", "tenant_id", "subscription_id", "target_url", "payload"], fn key -> {key, "value"} end)
    assert {:ok, ^command} = Service.validate_command(command)
  end

  test "unknown lifecycle transitions are denied" do
    refute Service.transition_allowed?("unknown", "unknown")
  end
end
