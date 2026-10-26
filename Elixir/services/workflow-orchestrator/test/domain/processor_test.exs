defmodule PesaGuard.WorkflowOrchestrator.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.WorkflowOrchestrator.Domain.Processor

  test "rejects non-integer workflow versions" do
    assert {:error, :workflow_type_and_integer_version_required} =
             Processor.prepare(%{"workflow_type" => "kyb.review", "version" => "1"})
  end

  test "accepts a versioned workflow type" do
    command = %{"workflow_type" => "kyb.review", "version" => 1}
    assert {:ok, ^command} = Processor.prepare(command)
  end
end
