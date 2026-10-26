defmodule PesaGuard.IntegrationHealthService.Endpoint do
  use Phoenix.Endpoint, otp_app: :integration_health_service

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]
  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Jason

  plug Plug.MethodOverride
  plug Plug.Head
  plug PesaGuard.IntegrationHealthService.Router
end
