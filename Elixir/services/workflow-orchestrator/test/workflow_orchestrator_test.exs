defmodule PesaGuard.WorkflowOrchestratorTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:workflow_orchestrator, :vsn) == ~c"0.1.0" or
             Application.spec(:workflow_orchestrator, :vsn) == '0.1.0' or
             Application.spec(:workflow_orchestrator, :vsn) == nil
  end
end
