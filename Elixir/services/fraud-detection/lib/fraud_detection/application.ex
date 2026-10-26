defmodule PesaGuard.FraudDetection.Application do
  @moduledoc "OTP application for fraud-detection."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.FraudDetection.Telemetry, []}] ++
        PesaGuard.FraudDetection.Persistence.PostgresStore.children() ++
        PesaGuard.FraudDetection.OutboxRelay.children() ++
        [PesaGuard.FraudDetection.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.FraudDetection.Supervisor
    )
  end
end
