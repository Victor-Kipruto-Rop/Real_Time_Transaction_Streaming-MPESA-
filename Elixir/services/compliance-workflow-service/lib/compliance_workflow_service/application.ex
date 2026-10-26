defmodule PesaGuard.ComplianceWorkflowService.Application do
  @moduledoc """
  OTP application for Compliance Workflow Service.

  Compliance case routing, evidence requests, retention and policy workflow coordination; no fabricated verification results.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.ComplianceWorkflowService.Endpoint,
      {PesaGuard.ComplianceWorkflowService.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.ComplianceWorkflowService.Supervisor)
  end
end
