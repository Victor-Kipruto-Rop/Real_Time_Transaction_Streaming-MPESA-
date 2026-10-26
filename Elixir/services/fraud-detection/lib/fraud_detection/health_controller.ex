defmodule PesaGuard.FraudDetection.HealthController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.FraudDetection.Persistence.PostgresStore

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "fraud-detection", version: "0.2.0"})
  end

  def ready(conn, _params) do
    case PostgresStore.ready?() do
      :ok ->
        json(conn, %{status: "ready", service: "fraud-detection", checks: %{database: "ok"}})

      {:error, _reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{status: "not_ready", service: "fraud-detection", checks: %{database: "unavailable"}})
    end
  end
end
