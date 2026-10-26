defmodule PesaGuard.RiskEngine.HealthController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.RiskEngine.Persistence.PostgresStore

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "risk-engine", version: "0.2.0"})
  end

  def ready(conn, _params) do
    case PostgresStore.ready?() do
      :ok ->
        json(conn, %{status: "ready", service: "risk-engine", checks: %{database: "ok"}})

      {:error, _reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{status: "not_ready", service: "risk-engine", checks: %{database: "unavailable"}})
    end
  end
end
