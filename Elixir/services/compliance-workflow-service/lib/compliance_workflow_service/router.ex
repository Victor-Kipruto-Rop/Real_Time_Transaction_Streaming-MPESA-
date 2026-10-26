defmodule PesaGuard.ComplianceWorkflowService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.ComplianceWorkflowService.SecurityHeaders
  end

  scope "/", PesaGuard.ComplianceWorkflowService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
