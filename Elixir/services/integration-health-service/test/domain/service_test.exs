defmodule PesaGuard.IntegrationHealthService.Domain.ServiceTest do
  use ExUnit.Case, async: true
  alias PesaGuard.IntegrationHealthService.Domain.Service

  test "rejects incomplete commands" do
    assert {:error, {:missing_fields, fields}} = Service.validate_command(%{})
    assert fields != []
  end

  test "accepts commands with required fields" do
    command = Map.new(["check_id","tenant_id","integration_id","check_type"], fn key -> {key, "value"} end)
    assert {:ok, ^command} = Service.validate_command(command)
  end

  test "unknown lifecycle transitions are denied" do
    refute Service.transition_allowed?("unknown", "unknown")
  end
end
