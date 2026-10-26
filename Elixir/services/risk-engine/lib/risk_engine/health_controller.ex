defmodule PesaGuard.RiskEngine.HealthController do
  use Phoenix.Controller, formats: [:json]
  import Plug.Conn

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "risk-engine", version: "0.1.0"})
  end

  def ready(conn, _params) do
    # Add dependency checks before using readiness to gate production traffic.
    json(conn, %{status: "ready", service: "risk-engine", checks: %{application: "ok"}})
  end
end
