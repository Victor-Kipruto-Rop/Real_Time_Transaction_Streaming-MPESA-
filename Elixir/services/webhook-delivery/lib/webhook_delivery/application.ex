defmodule PesaGuard.WebhookDelivery.Application do
  @moduledoc """
  OTP application for Webhook Delivery.

  Tenant webhook subscriptions, HMAC signing, bounded retries, replay protection and delivery history. Must not publish duplicate delivery attempts as separate business events.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.WebhookDelivery.Endpoint,
      {PesaGuard.WebhookDelivery.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.WebhookDelivery.Supervisor)
  end
end
