defmodule PesaGuard.RiskEngine.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.RiskEngine.Domain.Processor

  test "returns a risk band and signal explanation without a payment action" do
    command = %{"signals" => %{"velocity" => 0.8, "device" => 0.6}, "model_or_rule_version" => "v1"}
    assert {:ok, result} = Processor.prepare(command)
    assert result["risk_band"] == "high"
    assert result["signal_names"] == ["device", "velocity"]
    refute Map.has_key?(result, "payment_action")
  end
end
