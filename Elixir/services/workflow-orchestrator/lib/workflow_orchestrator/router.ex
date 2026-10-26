defmodule PesaGuard.WorkflowOrchestrator.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.WorkflowOrchestrator.SecurityHeaders
  end

  scope "/", PesaGuard.WorkflowOrchestrator do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
