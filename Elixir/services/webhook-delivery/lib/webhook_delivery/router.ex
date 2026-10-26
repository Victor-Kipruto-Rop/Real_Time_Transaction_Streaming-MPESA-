defmodule PesaGuard.WebhookDelivery.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.WebhookDelivery.SecurityHeaders
  end

  scope "/", PesaGuard.WebhookDelivery do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
