import Config

if config_env() == :prod do
  secret_key_base = System.get_env("SECRET_KEY_BASE") ||
    raise "SECRET_KEY_BASE must be configured from a secret manager in production"

  host = System.get_env("PHX_HOST") ||
    raise "PHX_HOST must be configured in production"

  port = String.to_integer(System.get_env("PORT", "4000"))

  config :data_export_service, PesaGuard.DataExportService.Endpoint,
    url: [host: host, port: 443, scheme: "https"],
    http: [ip: {0, 0, 0, 0}, port: port],
    secret_key_base: secret_key_base,
    server: true
end
