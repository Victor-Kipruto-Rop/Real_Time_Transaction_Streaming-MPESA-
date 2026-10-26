defmodule PesaGuard.RiskEngine.Application do
  @moduledoc """
  OTP application for Risk Engine.

  Low-latency risk signal evaluation and explainable risk assessments; never autonomously reverse payments or move funds.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.RiskEngine.Endpoint,
      {PesaGuard.RiskEngine.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.RiskEngine.Supervisor)
  end
end
