defmodule PesaGuard.NotificationService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.NotificationService.Domain.Processor

  test "rejects unsupported notification channels" do
    assert {:error, :unsupported_channel} =
             Processor.prepare(%{"channel" => "carrier_pigeon", "recipient_ref" => "recipient-1"})
  end
end
