defmodule PesaGuard.DataExportService.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.DataExportService.SecurityHeaders
  end

  scope "/", PesaGuard.DataExportService do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
