defmodule PesaGuard.ComplianceWorkflowService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.ComplianceWorkflowService.Domain.Processor

  test "rejects duplicate evidence references" do
    command = %{"policy_version" => "kyb-v1", "evidence_refs" => ["doc-1", "doc-1"]}
    assert {:error, :duplicate_evidence_reference} = Processor.prepare(command)
  end
end
