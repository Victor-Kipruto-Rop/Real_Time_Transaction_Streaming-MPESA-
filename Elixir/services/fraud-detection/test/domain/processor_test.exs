defmodule PesaGuard.FraudDetection.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.FraudDetection.Domain.Processor

  test "produces a bounded, explainable fraud signal" do
    command = %{
      "rule_version" => "rules-v1",
      "features" => %{"amount_deviation" => 0.9, "velocity_count" => 90, "new_device" => true}
    }

    assert {:ok, result} = Processor.prepare(command)
    assert result["risk_score"] <= 1.0
    assert result["risk_band"] == "high"
  end
end
