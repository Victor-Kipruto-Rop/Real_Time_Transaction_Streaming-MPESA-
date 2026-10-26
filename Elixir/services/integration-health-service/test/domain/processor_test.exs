defmodule PesaGuard.IntegrationHealthService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.IntegrationHealthService.Domain.Processor

  test "rejects out-of-range health-check timeouts" do
    assert {:error, :invalid_timeout} =
             Processor.prepare(%{"check_type" => "latency", "timeout_ms" => 60_000})
  end
end
