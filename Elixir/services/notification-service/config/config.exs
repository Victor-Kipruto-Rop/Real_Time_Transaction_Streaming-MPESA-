import Config

config :notification_service, PesaGuard.NotificationService.Endpoint,
  url: [host: System.get_env("PHX_HOST", "localhost"), scheme: "http"],
  http: [ip: {0, 0, 0, 0}, port: String.to_integer(System.get_env("PORT", "4101"))],
  secret_key_base: System.get_env("SECRET_KEY_BASE", String.duplicate("dev-only-key-", 8)),
  server: config_env() == :prod

config :notification_service, :environment, config_env()
config :logger, :console, format: "$time $metadata[$level] $message\n", metadata: [:request_id]
import_config "#{config_env()}.exs"
