defmodule PesaGuard.RiskEngine.Router do
  use Phoenix.Router

  pipeline :api do
    plug :accepts, ["json"]
    plug PesaGuard.RiskEngine.SecurityHeaders
  end

  scope "/", PesaGuard.RiskEngine do
    pipe_through :api
    get "/health", HealthController, :show
    get "/ready", HealthController, :ready
  end
end
