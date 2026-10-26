defmodule PesaGuard.WebhookDelivery.CustomerDeliveryWorker do
  @moduledoc """
  Dispatches durable customer webhook deliveries. Each request is signed over
  the exact bytes sent. Redirects are disabled to prevent credential leakage.
  """

  use GenServer
  alias PesaGuard.WebhookDelivery.{CustomerDeliveryStore, DeliveryRequest, SecretBox}

  @poll_ms 1_000
  @batch_size 20

  def start_link(opts \\ []), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)

  def children do
    if is_binary(System.get_env("DATABASE_URL")) and System.get_env("DATABASE_URL") != "" do
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
    case CustomerDeliveryStore.claim_deliveries(@batch_size) do
      {:ok, deliveries} -> Enum.each(deliveries, &dispatch/1)
      {:error, _} -> :ok
    end

    Process.send_after(self(), :poll, @poll_ms)
    {:noreply, state}
  end

  defp dispatch(delivery) do
    with {:ok, secret} <- SecretBox.decrypt(delivery.encrypted_secret),
         {:ok, request} <- DeliveryRequest.build(
           %{"id" => delivery.subscription_id, "target_url" => delivery.target_url, "secret" => secret},
           delivery.event,
           System.system_time(:second)
         ),
         result <- post(request) do
      case result do
        {:ok, status} when status >= 200 and status < 300 ->
          CustomerDeliveryStore.complete_delivery(delivery.tenant_id, delivery.delivery_id, status)
        {:ok, status} ->
          CustomerDeliveryStore.fail_delivery(delivery.tenant_id, delivery.delivery_id, delivery.attempts, "http_#{status}", status)
        {:error, reason} ->
          CustomerDeliveryStore.fail_delivery(delivery.tenant_id, delivery.delivery_id, delivery.attempts, reason)
      end
    else
      {:error, :decryption_failed} ->
        CustomerDeliveryStore.fail_delivery(delivery.tenant_id, delivery.delivery_id, delivery.attempts, "secret_decryption_failed", 400)
      {:error, reason} ->
        CustomerDeliveryStore.fail_delivery(delivery.tenant_id, delivery.delivery_id, delivery.attempts, safe_reason(reason), 400)
    end
  rescue
    _ -> CustomerDeliveryStore.fail_delivery(delivery.tenant_id, delivery.delivery_id, delivery.attempts, "dispatch_failed")
  catch
    :exit, _ -> CustomerDeliveryStore.fail_delivery(delivery.tenant_id, delivery.delivery_id, delivery.attempts, "dispatch_failed")
  end

  defp post(request) do
    headers = Enum.map(request.headers, fn {name, value} -> {String.to_charlist(name), String.to_charlist(value)} end)
    http_request = {String.to_charlist(request.url), headers, ~c"application/json", request.body}

    case :httpc.request(:post, http_request,
           [timeout: 5_000, connect_timeout: 2_000, autoredirect: false,
            ssl: [verify: :verify_peer, cacerts: :public_key.cacerts_get()]],
           body_format: :binary) do
      {:ok, {{_version, status, _reason}, _headers, _body}} -> {:ok, status}
      {:error, :timeout} -> {:error, "timeout"}
      {:error, _} -> {:error, "connection_error"}
    end
  end

  defp safe_reason(reason) when is_atom(reason), do: Atom.to_string(reason)
  defp safe_reason(_), do: "invalid_delivery_request"
end
