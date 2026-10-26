defmodule PesaGuard.RiskEngine.OutboxRelay do
  @moduledoc """
  Leased transactional-outbox relay. The configured endpoint must durably accept
  an event before it returns a 2xx response. Delivery is at least once.
  """

  use GenServer

  alias PesaGuard.RiskEngine.Persistence.PostgresStore
  alias PesaGuard.RiskEngine.Reliability.RetryPolicy

  @poll_interval_ms 1_000
  @batch_size 10

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def children do
    environment = Application.get_env(:webhook_delivery, :environment)
    url = System.get_env("EVENT_RELAY_URL")
    token = System.get_env("EVENT_RELAY_TOKEN")

    cond do
      is_binary(url) and url != "" and is_binary(token) and byte_size(token) >= 32 ->
        [Supervisor.child_spec({__MODULE__, []}, id: __MODULE__)]

      environment == :prod ->
        raise "EVENT_RELAY_URL and a 32-byte EVENT_RELAY_TOKEN are required in production"

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
    case PostgresStore.claim_outbox(@batch_size) do
      {:ok, events} -> Enum.each(events, &deliver/1)
      {:error, _reason} -> :ok
    end

    Process.send_after(self(), :poll, @poll_interval_ms)
    {:noreply, state}
  end

  defp deliver(event) do
    url = System.fetch_env!("EVENT_RELAY_URL")
    token = System.fetch_env!("EVENT_RELAY_TOKEN")
    body = Jason.encode!(event.payload)

    headers = [
      {~c"authorization", String.to_charlist("Bearer " <> token)},
      {~c"content-type", ~c"application/json"},
      {~c"idempotency-key", String.to_charlist(event.event_id)}
    ]

    request = {String.to_charlist(url), headers, ~c"application/json", body}

    result =
      try do
        :httpc.request(:post, request, [timeout: 5_000, connect_timeout: 2_000],
          body_format: :binary
        )
      rescue
        _ -> {:error, :request_failed}
      catch
        :exit, _ -> {:error, :request_failed}
      end

    case result do
      {:ok, {{_version, status, _reason}, _headers, _response}} when status >= 200 and status < 300 ->
        PostgresStore.acknowledge_outbox(event.tenant_id, event.event_id)

      {:ok, {{_version, status, _reason}, _headers, _response}} ->
        retry_or_dead_letter(event, {:http_status, status})

      {:error, reason} ->
        retry_or_dead_letter(event, {:connection_error, reason})
    end
  end

  defp retry_or_dead_letter(event, failure) do
    case RetryPolicy.next_delay(event.attempts) do
      {:retry, delay_ms} ->
        retry_at = System.system_time(:second) + max(div(delay_ms, 1_000), 1)
        permanent? = RetryPolicy.classify(failure, event.attempts) in [:permanent, :security]

        PostgresStore.fail_outbox(
          event.tenant_id,
          event.event_id,
          retry_at,
          inspect(failure),
          permanent?
        )

      :dead_letter ->
        PostgresStore.fail_outbox(
          event.tenant_id,
          event.event_id,
          System.system_time(:second),
          inspect(failure),
          true
        )
    end
  end
end
