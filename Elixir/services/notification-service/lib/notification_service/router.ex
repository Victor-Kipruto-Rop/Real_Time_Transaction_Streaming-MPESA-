defmodule PesaGuard.NotificationService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.NotificationService.SecurityHeaders
  end

  scope "/", PesaGuard.NotificationService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
