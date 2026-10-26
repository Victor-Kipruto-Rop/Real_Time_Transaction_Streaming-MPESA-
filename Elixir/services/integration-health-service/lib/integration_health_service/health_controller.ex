defmodule PesaGuard.IntegrationHealthService.HealthController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.IntegrationHealthService.Persistence.PostgresStore

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "integration-health-service", version: "0.2.0"})
  end

  def ready(conn, _params) do
    case PostgresStore.ready?() do
      :ok ->
        json(conn, %{status: "ready", service: "integration-health-service", checks: %{database: "ok"}})

      {:error, _reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{status: "not_ready", service: "integration-health-service", checks: %{database: "unavailable"}})
    end
  end
end
