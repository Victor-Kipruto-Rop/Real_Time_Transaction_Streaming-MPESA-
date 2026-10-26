defmodule PesaGuard.ComplianceWorkflowService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.ComplianceWorkflowService.Domain.Processor

  test "rejects duplicate evidence references" do
    command = %{"policy_version" => "kyb-v1", "evidence_refs" => ["doc-1", "doc-1"]}
    assert {:error, :duplicate_evidence_reference} = Processor.prepare(command)
  end

  test "accepts unique evidence references and a policy version" do
    command = %{"policy_version" => "kyb-v1", "evidence_refs" => ["registration-doc", "tax-pin"]}
    assert {:ok, ^command} = Processor.prepare(command)
  end
end
