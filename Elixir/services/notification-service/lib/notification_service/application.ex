defmodule PesaGuard.NotificationService.Application do
  @moduledoc "OTP application for notification-service."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.NotificationService.Telemetry, []}] ++
        PesaGuard.NotificationService.Persistence.PostgresStore.children() ++
        [PesaGuard.NotificationService.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.NotificationService.Supervisor
    )
  end
end
