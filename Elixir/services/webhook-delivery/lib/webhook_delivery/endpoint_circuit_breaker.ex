defmodule PesaGuard.WebhookDelivery.EndpointCircuitBreaker do
  @moduledoc """
  Process-local circuit breaker keyed by webhook origin (scheme, host and port).

  Circuit state is an optimization, not durable delivery state. The PostgreSQL
  delivery queue remains authoritative and retries deliveries after the breaker
  closes. State is bounded to avoid unbounded growth from changing destinations.
  """

  use GenServer

  @default_threshold 5
  @default_open_ms 30_000
  @default_max_entries 1_000

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def child_spec(opts) do
    %{
      id: __MODULE__,
      start: {__MODULE__, :start_link, [opts]},
      type: :worker,
      restart: :permanent,
      shutdown: 5_000
    }
  end

  def allow?(url) when is_binary(url), do: GenServer.call(__MODULE__, {:allow, origin(url)})
  def allow?(_), do: {:error, :invalid_endpoint}

  def record_success(url) when is_binary(url), do: GenServer.cast(__MODULE__, {:success, origin(url)})
  def record_success(_), do: :ok

  def record_failure(url) when is_binary(url), do: GenServer.cast(__MODULE__, {:failure, origin(url)})
  def record_failure(_), do: :ok

  @impl true
  def init(opts) do
    {:ok,
     %{
       entries: %{},
       threshold: Keyword.get(opts, :threshold, @default_threshold),
       open_ms: Keyword.get(opts, :open_ms, @default_open_ms),
       max_entries: Keyword.get(opts, :max_entries, @default_max_entries)
     }}
  end

  @impl true
  def handle_call({:allow, {:ok, key}}, _from, state) do
    now = System.monotonic_time(:millisecond)
    entry = Map.get(state.entries, key, %{failures: 0, status: :closed, touched_at: now})

    cond do
      entry.status == :closed ->
        {:reply, :ok, put_entry(state, key, %{entry | touched_at: now})}

      entry.status == :open and now >= entry.open_until and not Map.get(entry, :probe_in_flight, false) ->
        next = entry |> Map.put(:status, :half_open) |> Map.put(:probe_in_flight, true) |> Map.put(:touched_at, now)
        {:reply, :ok, put_entry(state, key, next)}

      true ->
        {:reply, {:error, :circuit_open}, put_entry(state, key, %{entry | touched_at: now})}
    end
  end

  def handle_call({:allow, :error}, _from, state), do: {:reply, {:error, :invalid_endpoint}, state}

  @impl true
  def handle_cast({:success, {:ok, key}}, state) do
    now = System.monotonic_time(:millisecond)
    entry = %{failures: 0, status: :closed, touched_at: now}
    {:noreply, put_entry(state, key, entry)}
  end

  def handle_cast({:success, :error}, state), do: {:noreply, state}

  def handle_cast({:failure, {:ok, key}}, state) do
    now = System.monotonic_time(:millisecond)
    current = Map.get(state.entries, key, %{failures: 0, status: :closed})
    failures = Map.get(current, :failures, 0) + 1

    next =
      if current.status == :half_open or failures >= state.threshold do
        %{failures: failures, status: :open, open_until: now + state.open_ms, probe_in_flight: false, touched_at: now}
      else
        %{failures: failures, status: :closed, touched_at: now}
      end

    {:noreply, put_entry(state, key, next)}
  end

  def handle_cast({:failure, :error}, state), do: {:noreply, state}

  defp put_entry(state, key, entry) do
    entries = Map.put(state.entries, key, entry)

    entries =
      if map_size(entries) <= state.max_entries do
        entries
      else
        oldest = Enum.min_by(entries, fn {_key, value} -> Map.get(value, :touched_at, 0) end) |> elem(0)
        Map.delete(entries, oldest)
      end

    %{state | entries: entries}
  end

  defp origin(url) do
    uri = URI.parse(url)

    if uri.scheme in ["http", "https"] and is_binary(uri.host) and uri.host != "" do
      {:ok, {uri.scheme, String.downcase(String.trim(uri.host, "[]")), uri.port || if(uri.scheme == "https", do: 443, else: 80)}}
    else
      :error
    end
  rescue
    _ -> :error
  end
end
