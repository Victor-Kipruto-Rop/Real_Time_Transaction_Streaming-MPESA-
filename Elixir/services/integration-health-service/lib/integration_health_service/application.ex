defmodule PesaGuard.IntegrationHealthService.Application do
  @moduledoc """
  OTP application for Integration Health Service.

  Provider dependency health, circuit state and operational diagnostics; must not expose credentials or sensitive response bodies.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.IntegrationHealthService.Endpoint,
      {PesaGuard.IntegrationHealthService.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.IntegrationHealthService.Supervisor)
  end
end
