defmodule PesaGuard.WorkflowOrchestrator.HealthController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.WorkflowOrchestrator.Persistence.PostgresStore

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "workflow-orchestrator", version: "0.2.0"})
  end

  def ready(conn, _params) do
    case PostgresStore.ready?() do
      :ok ->
        json(conn, %{status: "ready", service: "workflow-orchestrator", checks: %{database: "ok"}})

      {:error, _reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{status: "not_ready", service: "workflow-orchestrator", checks: %{database: "unavailable"}})
    end
  end
end
