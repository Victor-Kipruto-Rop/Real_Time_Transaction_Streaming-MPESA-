defmodule PesaGuard.WebhookDelivery.CustomerDeliveryWorker do
  @moduledoc """
  Polls the durable customer-delivery queue and dispatches signed HTTPS requests.
  Delivery is at least once: receivers must deduplicate x-telixo-delivery-id.
  """

  use GenServer

  alias PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStore
  alias PesaGuard.WebhookDelivery.Signing
  alias PesaGuard.WebhookDelivery.TargetPolicy
  alias PesaGuard.WebhookDelivery.PinnedHttpClient
  alias PesaGuard.WebhookDelivery.EndpointCircuitBreaker

  @poll_interval_ms 1_000
  @batch_size 5
  
  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def children do
    environment = Application.get_env(:webhook_delivery, :environment)
    database_url = System.get_env("DATABASE_URL")
    key = System.get_env("WEBHOOK_SECRET_ENCRYPTION_KEY")

    key_valid? =
      case Base.decode64(key || "") do
        {:ok, decoded} -> byte_size(decoded) == 32
        _ -> false
      end

    cond do
      is_binary(database_url) and database_url != "" and key_valid? ->
        [EndpointCircuitBreaker, Supervisor.child_spec({__MODULE__, []}, id: __MODULE__)]

      environment == :prod ->
        raise "DATABASE_URL and a base64-encoded 32-byte WEBHOOK_SECRET_ENCRYPTION_KEY are required in production"

      true ->
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
    body =
      Jason.encode!(%{
        "id" => delivery.event_id,
        "type" => delivery.event_type,
        "delivery_id" => delivery.delivery_id,
        "data" => delivery.payload
      })

    result =
      with {:ok, target} <- TargetPolicy.resolve_target(delivery.target_url),
           :ok <- EndpointCircuitBreaker.allow?(delivery.target_url),
           {:ok, headers} <- Signing.headers(delivery.delivery_id, delivery.secret, body, timestamp) do
        request_headers = Enum.reject(headers, fn {name, _value} -> name == "content-type" end)
        PinnedHttpClient.post(target, request_headers, body)
      end

    case result do
      {:ok, {{_version, status, _reason}, _headers, _response}} when status >= 200 and status < 300 ->
        EndpointCircuitBreaker.record_success(delivery.target_url)
        CustomerWebhookStore.acknowledge(delivery.tenant_id, delivery.delivery_id, status)

      {:ok, {{_version, status, _reason}, _headers, _response}}
      when status in [408, 425, 429] or status >= 500 ->
        EndpointCircuitBreaker.record_failure(delivery.target_url)
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, "http_status_#{status}")

      {:ok, {{_version, status, _reason}, _headers, _response}} ->
        # A permanent 4xx response proves the endpoint is reachable; do not
        # open the circuit for an application-level rejection.
        EndpointCircuitBreaker.record_success(delivery.target_url)
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, "http_status_#{status}", true)

      {:error, :circuit_open} ->
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, "circuit_open")

      {:error, reason}
      when reason in [
             :target_url_must_use_https,
             :target_url_host_required,
             :target_url_credentials_forbidden,
             :target_url_port_forbidden,
             :target_url_private_host_forbidden,
             :target_url_ip_literal_forbidden,
             :invalid_secret
           ] ->
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, inspect(reason), true)

      {:error, reason} ->
        EndpointCircuitBreaker.record_failure(delivery.target_url)
        CustomerWebhookStore.fail(delivery.tenant_id, delivery.delivery_id, inspect(reason))
    end
  end
end
