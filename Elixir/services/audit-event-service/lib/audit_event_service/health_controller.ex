defmodule PesaGuard.AuditEventService.HealthController do
  use Phoenix.Controller, formats: [:json]
  import Plug.Conn

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "audit-event-service", version: "0.1.0"})
  end

  def ready(conn, _params) do
    # Add dependency checks before using readiness to gate production traffic.
    json(conn, %{status: "ready", service: "audit-event-service", checks: %{application: "ok"}})
  end
end
