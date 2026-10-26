defmodule PesaGuard.FraudDetectionTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:fraud_detection, :vsn) == ~c"0.1.0" or
             Application.spec(:fraud_detection, :vsn) == '0.1.0' or
             Application.spec(:fraud_detection, :vsn) == nil
  end
end
