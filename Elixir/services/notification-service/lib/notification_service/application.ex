defmodule PesaGuard.NotificationService.Application do
  @moduledoc """
  OTP application for Notification Service.

  Email/SMS/in-app notification orchestration, preferences, templates, provider adapters and delivery status.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.NotificationService.Endpoint,
      {PesaGuard.NotificationService.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.NotificationService.Supervisor)
  end
end
