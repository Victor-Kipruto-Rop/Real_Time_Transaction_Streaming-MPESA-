defmodule PesaGuard.RiskEngine.Endpoint do
  use Phoenix.Endpoint, otp_app: :risk_engine

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]
  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Jason

  plug Plug.MethodOverride
  plug Plug.Head
  plug PesaGuard.RiskEngine.Router
end
