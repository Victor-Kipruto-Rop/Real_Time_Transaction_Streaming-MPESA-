defmodule PesaGuard.WorkflowOrchestrator.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.WorkflowOrchestrator.Domain.Processor

  test "rejects non-integer workflow versions" do
    assert {:error, :workflow_type_and_integer_version_required} =
             Processor.prepare(%{"workflow_type" => "kyb.review", "version" => "1"})
  end
end
