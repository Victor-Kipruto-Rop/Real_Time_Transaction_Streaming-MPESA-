defmodule PesaGuard.AuditEventService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.AuditEventService.SecurityHeaders
  end

  scope "/", PesaGuard.AuditEventService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
