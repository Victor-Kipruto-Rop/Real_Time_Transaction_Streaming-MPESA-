defmodule PesaGuard.IncidentManagementService.Application do
  @moduledoc "OTP application for incident-management-service."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.IncidentManagementService.Telemetry, []}] ++
        PesaGuard.IncidentManagementService.Persistence.PostgresStore.children() ++
        [PesaGuard.IncidentManagementService.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.IncidentManagementService.Supervisor
    )
  end
end
