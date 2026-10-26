defmodule PesaGuard.IncidentManagementService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.IncidentManagementService.SecurityHeaders
  end

  scope "/", PesaGuard.IncidentManagementService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
