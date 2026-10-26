defmodule PesaGuard.IncidentManagementService.Domain.ServiceTest do
  use ExUnit.Case, async: true
  alias PesaGuard.IncidentManagementService.Domain.Service

  test "rejects incomplete commands" do
    assert {:error, {:missing_fields, fields}} = Service.validate_command(%{})
    assert fields != []
  end

  test "accepts commands with required fields" do
    command = Map.new(["incident_id", "tenant_id", "severity", "summary", "opened_at"], fn key -> {key, "value"} end)
    assert {:ok, ^command} = Service.validate_command(command)
  end

  test "unknown lifecycle transitions are denied" do
    refute Service.transition_allowed?("unknown", "unknown")
  end
end
