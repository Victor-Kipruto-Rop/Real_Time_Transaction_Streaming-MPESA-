defmodule PesaGuard.WebhookDelivery.CustomerDeliveryWorker do
  @moduledoc """
  Polls the durable customer-delivery queue and dispatches signed HTTPS requests.
  Delivery is at least once: receivers must deduplicate x-telixo-delivery-id.
  """

  use GenServer

  alias PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStore
  alias PesaGuard.WebhookDelivery.Signing
  alias PesaGuard.WebhookDelivery.TargetPolicy

  @poll_interval_ms 1_000
  @batch_size 20
  @timeout_ms 5_000

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def children do
    if System.get_env("DATABASE_URL") do
      [Supervisor.child_spec({__MODULE__, []}, id: __MODULE__)]
    else
      []
    end
  end

  @impl true
  def init(_opts) do
    send(self(), :poll)
    {:ok, %{}}
  end

  @impl true
  def handle_info(:poll, state) do
    case CustomerWebhookStore.claim(@batch_size) do
      {:ok, deliveries} -> Enum.each(deliveries, &deliver/1)
      {:error, _reason} -> :ok
    end

    Process.send_after(self(), :poll, @poll_interval_ms)
    {:noreply, state}
  end

  defp deliver(delivery) do
    timestamp = System.system_time(:second)
    body = Jason.encode!(%{
      "id" => delivery.event_id,
      "type" => delivery.event_type,
      "delivery_id" => delivery.delivery_id,
      "data" => delivery.payload
    })

    result =
      with :ok <- TargetPolicy.validate(delivery.target_url),
           {:ok, headers} <- Signing.headers(delivery.delivery_id, delivery.secret, body, timestamp) do
        request_headers =
          Enum.map(headers, fn {name, value} ->
            {String.to_charlist(name), String.to_charlist(value)}
          end)

        request = {String.to_charlist(delivery.target_url), request_headers, ~c"application/json", body}

        try do
          :httpc.request(:post, request,
            [timeout: @timeout_ms, connect_timeout: 2_000, autoredirect: false,
             ssl: [verify: :verify_peer, cacerts: :public_key.cacerts_get()]],
            body_format: :binary
          )
        rescue
          _ -> {:error, :request_failed}
        catch
          :exit, _ -> {:error, :request_failed}
        end
      end

    case result do
      {:ok, {{_version, status, _reason}, _headers, _response}} when status >= 200 and status < 300 ->
        CustomerWebhookStore.acknowledge(delivery.tenant_id, delivery.delivery_id, status)

      {:ok, {{_version, status, _reason}, _headers, _response}} when status in [408, 425, 429] or status >= 500 ->
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, "http_status_#{status}")

      {:ok, {{_version, status, _reason}, _headers, _response}} ->
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, "http_status_#{status}", true)

      {:error, reason} ->
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, inspect(reason))

      {:error, reason} ->
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, inspect(reason))
    end
  end
end
