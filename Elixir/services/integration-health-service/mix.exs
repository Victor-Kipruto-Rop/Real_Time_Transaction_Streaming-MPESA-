defmodule PesaGuard.IntegrationHealthService.MixProject do
  use Mix.Project

  def project do
    [
      app: :integration_health_service,
      version: "0.2.0",
      elixir: "~> 1.17",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      aliases: aliases()
    ]
  end

  def application do
    [
      extra_applications: [:logger, :runtime_tools, :crypto, :inets, :ssl],
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
      {:postgrex, "~> 0.19"}
    ]
  end

  defp aliases do
    [check: ["format --check-formatted", "compile --warnings-as-errors", "test"]]
  end
end
