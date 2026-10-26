defmodule PesaGuard.FraudDetection.Application do
  @moduledoc """
  OTP application for Fraud Detection.

  Streaming anomaly feature evaluation and fraud case signals using versioned rules; integrate with the canonical risk decision boundary.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.FraudDetection.Endpoint,
      {PesaGuard.FraudDetection.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.FraudDetection.Supervisor)
  end
end
