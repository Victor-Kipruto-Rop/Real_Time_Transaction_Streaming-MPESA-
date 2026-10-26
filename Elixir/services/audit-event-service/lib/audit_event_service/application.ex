defmodule PesaGuard.AuditEventService.Application do
  @moduledoc "OTP application for audit-event-service."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.AuditEventService.Telemetry, []}] ++
        PesaGuard.AuditEventService.Persistence.PostgresStore.children() ++
        [PesaGuard.AuditEventService.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.AuditEventService.Supervisor
    )
  end
end
