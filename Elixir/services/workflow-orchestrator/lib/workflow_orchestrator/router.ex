defmodule PesaGuard.WorkflowOrchestrator.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.WorkflowOrchestrator.SecurityHeaders
  end

  pipeline :authenticated_api do
    plug PesaGuard.WorkflowOrchestrator.Security.JWTAuth
  end

  scope "/", PesaGuard.WorkflowOrchestrator do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end

  scope "/v1", PesaGuard.WorkflowOrchestrator do
    pipe_through [:api, :authenticated_api]
    post "/records", RecordsController, :create
    get "/records/:id", RecordsController, :show
    patch "/records/:id/state", RecordsController, :transition
  end
end
