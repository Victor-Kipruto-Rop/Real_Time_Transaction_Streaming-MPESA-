defmodule PesaGuard.FraudDetection.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.FraudDetection.SecurityHeaders
  end

  scope "/", PesaGuard.FraudDetection do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
