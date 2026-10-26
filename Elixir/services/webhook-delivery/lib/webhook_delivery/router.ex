defmodule PesaGuard.WebhookDelivery.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.WebhookDelivery.SecurityHeaders
  end

  pipeline :authenticated_api do
    plug PesaGuard.WebhookDelivery.Security.JWTAuth
  end

  scope "/", PesaGuard.WebhookDelivery do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end

  scope "/v1", PesaGuard.WebhookDelivery do
    pipe_through [:api, :authenticated_api]
    post "/records", RecordsController, :create
    get "/records/:id", RecordsController, :show
    patch "/records/:id/state", RecordsController, :transition

    post "/outbox/:event_id/replay", OutboxReplayController, :replay
    post "/events", CustomerWebhooksController, :fanout
    get "/subscriptions", CustomerWebhooksController, :index
    post "/subscriptions", CustomerWebhooksController, :create
    post "/subscriptions/:subscription_id/deliveries", CustomerWebhooksController, :enqueue
    get "/subscriptions/:subscription_id/deliveries", CustomerWebhooksController, :history
  end
end
