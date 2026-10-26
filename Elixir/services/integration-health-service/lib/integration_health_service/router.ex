defmodule PesaGuard.IntegrationHealthService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.IntegrationHealthService.SecurityHeaders
  end

  scope "/", PesaGuard.IntegrationHealthService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
