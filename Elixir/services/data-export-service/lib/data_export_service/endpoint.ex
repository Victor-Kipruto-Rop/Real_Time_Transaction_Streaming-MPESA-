defmodule PesaGuard.DataExportService.Endpoint do
  use Phoenix.Endpoint, otp_app: :data_export_service

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]
  plug Plug.Parsers, parsers: [:urlencoded, :multipart, :json], pass: ["*/*"], json_decoder: Jason
  plug Plug.MethodOverride
  plug Plug.Head
  plug PesaGuard.DataExportService.Router
end
