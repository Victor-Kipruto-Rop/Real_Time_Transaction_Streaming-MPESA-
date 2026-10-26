defmodule PesaGuard.WorkflowOrchestrator.Application do
  @moduledoc "OTP application for workflow-orchestrator."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.WorkflowOrchestrator.Telemetry, []}] ++
        PesaGuard.WorkflowOrchestrator.Persistence.PostgresStore.children() ++
        PesaGuard.WorkflowOrchestrator.OutboxRelay.children() ++
        [PesaGuard.WorkflowOrchestrator.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.WorkflowOrchestrator.Supervisor
    )
  end
end
