defmodule PesaGuard.IntegrationHealthService.MixProject do
  use Mix.Project

  def project do
    [
      app: :integration_health_service,
      version: "0.1.0",
      elixir: "~> 1.17",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      aliases: aliases()
    ]
  end

  def application do
    [
      extra_applications: [:logger, :runtime_tools],
      mod: {PesaGuard.IntegrationHealthService.Application, []}
    ]
  end

  defp deps do
    [
      {:phoenix, "~> 1.7.21"},
      {:plug_cowboy, "~> 2.7"},
      {:jason, "~> 1.4"},
      {:telemetry_metrics, "~> 1.1"},
      {:telemetry_poller, "~> 1.2"},
      {:plug, "~> 1.16"},
      {:bandit, "~> 1.5", optional: true},
      {:ex_unit, "~> 1.0", only: :test}
    ]
  end

  defp aliases do
    [
      check: ["format --check-formatted", "compile --warnings-as-errors", "test"]
    ]
  end
end
