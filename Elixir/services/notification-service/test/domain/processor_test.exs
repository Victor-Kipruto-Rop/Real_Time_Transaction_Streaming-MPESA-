defmodule PesaGuard.NotificationService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.NotificationService.Domain.Processor

  test "rejects unsupported notification channels" do
    assert {:error, :unsupported_channel} =
             Processor.prepare(%{"channel" => "carrier_pigeon", "recipient_ref" => "recipient-1"})
  end

  test "accepts a supported channel and recipient reference" do
    command = %{"channel" => "email", "recipient_ref" => "recipient-123"}
    assert {:ok, ^command} = Processor.prepare(command)
  end
end
