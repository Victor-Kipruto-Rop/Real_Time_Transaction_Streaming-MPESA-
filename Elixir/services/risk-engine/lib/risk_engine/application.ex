defmodule PesaGuard.RiskEngine.Application do
  @moduledoc "OTP application for risk-engine."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.RiskEngine.Telemetry, []}] ++
        PesaGuard.RiskEngine.Persistence.PostgresStore.children() ++
        [PesaGuard.RiskEngine.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.RiskEngine.Supervisor
    )
  end
end
