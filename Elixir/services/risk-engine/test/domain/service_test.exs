defmodule TELIXO.RiskEngine.Domain.ServiceTest do
  use ExUnit.Case, async: true
  alias TELIXO.RiskEngine.Domain.Service
  test "rejects incomplete commands" do
    assert {:error, {:missing_fields, fields}} = Service.validate_command(%{})
    assert fields != []
  end
  test "accepts commands with required fields" do
    command = Map.new(["assessment_id","tenant_id","subject_ref","model_or_rule_version"], fn key -> {key, "value"} end)
    assert {:ok, ^command} = Service.validate_command(command)
  end
  test "unknown lifecycle transitions are denied" do
    refute Service.transition_allowed?("unknown", "unknown")
  end
end