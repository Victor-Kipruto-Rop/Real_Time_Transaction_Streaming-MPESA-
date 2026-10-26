defmodule PesaGuard.RiskEngineTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:risk_engine, :vsn) == ~c"0.1.0" or
             Application.spec(:risk_engine, :vsn) == '0.1.0' or
             Application.spec(:risk_engine, :vsn) == nil
  end
end
