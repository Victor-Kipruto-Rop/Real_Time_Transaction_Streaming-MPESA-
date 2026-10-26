import Config

config :integration_health_service, PesaGuard.IntegrationHealthService.Endpoint,
  server: false,
  http: [ip: {127, 0, 0, 1}, port: 0],
  secret_key_base: String.duplicate("test-only-secret-", 8)

config :logger, level: :warning
