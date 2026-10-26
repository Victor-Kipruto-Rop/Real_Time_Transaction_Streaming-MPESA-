defmodule PesaGuard.ComplianceWorkflowService.Application do
  @moduledoc "OTP application for compliance-workflow-service."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.ComplianceWorkflowService.Telemetry, []}] ++
        PesaGuard.ComplianceWorkflowService.Persistence.PostgresStore.children() ++
        [PesaGuard.ComplianceWorkflowService.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.ComplianceWorkflowService.Supervisor
    )
  end
end
