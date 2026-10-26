defmodule PesaGuard.IncidentManagementService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.IncidentManagementService.Domain.Processor

  test "rejects unknown incident severities" do
    command = %{"severity" => "emergency", "summary" => "summary", "opened_at" => "2026-01-01T00:00:00Z"}
    assert {:error, :invalid_severity} = Processor.prepare(command)
  end
end
