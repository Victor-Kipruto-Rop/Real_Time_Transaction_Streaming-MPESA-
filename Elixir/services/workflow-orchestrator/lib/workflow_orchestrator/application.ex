defmodule PesaGuard.WorkflowOrchestrator.Application do
  @moduledoc """
  OTP application for Workflow Orchestrator.

  Long-running onboarding, review and operational workflows with durable state, retries, timeouts and idempotent transitions.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.WorkflowOrchestrator.Endpoint,
      {PesaGuard.WorkflowOrchestrator.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.WorkflowOrchestrator.Supervisor)
  end
end
