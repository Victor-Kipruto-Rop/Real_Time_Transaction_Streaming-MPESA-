defmodule PesaGuard.AuditEventService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.AuditEventService.Domain.Processor

  test "rejects unknown audit actor types" do
    command = %{"actor_type" => "anonymous", "action" => "read", "occurred_at" => "2026-01-01T00:00:00Z"}
    assert {:error, :invalid_actor_type} = Processor.prepare(command)
  end
end
