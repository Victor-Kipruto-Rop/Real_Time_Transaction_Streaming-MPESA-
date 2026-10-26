defmodule PesaGuard.AuditEventService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.AuditEventService.SecurityHeaders
  end

  pipeline :authenticated_api do
    plug PesaGuard.AuditEventService.Security.JWTAuth
  end

  scope "/", PesaGuard.AuditEventService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end

  scope "/v1", PesaGuard.AuditEventService do
    pipe_through [:api, :authenticated_api]
    post "/records", RecordsController, :create
    get "/records/:id", RecordsController, :show
    patch "/records/:id/state", RecordsController, :transition
    get "/admin/retention-policy", AdminController, :get_retention_policy
    put "/admin/retention-policy", AdminController, :update_retention_policy
    post "/admin/integrity/verify", AdminController, :verify_integrity
  end
end
