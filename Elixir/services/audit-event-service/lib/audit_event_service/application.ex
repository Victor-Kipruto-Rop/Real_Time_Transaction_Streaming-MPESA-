defmodule PesaGuard.AuditEventService.Application do
  @moduledoc """
  OTP application for Audit Event Service.

  Durable append-oriented audit event intake, integrity metadata, controlled access and retention integration.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.AuditEventService.Endpoint,
      {PesaGuard.AuditEventService.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.AuditEventService.Supervisor)
  end
end
