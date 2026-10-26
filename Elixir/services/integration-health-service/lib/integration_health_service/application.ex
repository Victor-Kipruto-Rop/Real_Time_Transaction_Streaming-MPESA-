defmodule PesaGuard.IntegrationHealthService.Application do
  @moduledoc "OTP application for integration-health-service."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.IntegrationHealthService.Telemetry, []}] ++
        PesaGuard.IntegrationHealthService.Persistence.PostgresStore.children() ++
        PesaGuard.IntegrationHealthService.OutboxRelay.children() ++
        [PesaGuard.IntegrationHealthService.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.IntegrationHealthService.Supervisor
    )
  end
end
