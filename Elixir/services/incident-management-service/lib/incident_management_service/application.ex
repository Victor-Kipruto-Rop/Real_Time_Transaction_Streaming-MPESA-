defmodule PesaGuard.IncidentManagementService.Application do
  @moduledoc """
  OTP application for Incident Management Service.

  Internal incident lifecycle, alert acknowledgement, escalation metadata and operational postmortem tracking.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.IncidentManagementService.Endpoint,
      {PesaGuard.IncidentManagementService.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.IncidentManagementService.Supervisor)
  end
end
