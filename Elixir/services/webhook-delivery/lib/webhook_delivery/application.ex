defmodule PesaGuard.WebhookDelivery.Application do
  @moduledoc "OTP application for webhook-delivery."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.WebhookDelivery.Telemetry, []}] ++
        PesaGuard.WebhookDelivery.Persistence.PostgresStore.children() ++
        [PesaGuard.WebhookDelivery.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.WebhookDelivery.Supervisor
    )
  end
end
