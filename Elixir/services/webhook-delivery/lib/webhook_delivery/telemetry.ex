defmodule PesaGuard.WebhookDelivery.Telemetry do
  use Supervisor
  import Telemetry.Metrics

  def start_link(_opts) do
    Supervisor.start_link(__MODULE__, :ok, name: __MODULE__)
  end

  @impl true
  def init(:ok) do
    children = [
      {:telemetry_poller, measurements: periodic_measurements(), period: 10_000}
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end

  def metrics do
    [
      last_value("vm.memory.total", unit: {:byte, :kilobyte}),
      sum("phoenix.endpoint.stop.duration", unit: {:native, :millisecond}),
      counter("phoenix.endpoint.stop.count")
    ]
  end

  def dispatch_vm_memory do
    :telemetry.execute([:vm, :memory], %{total: :erlang.memory(:total)}, %{})
  end

  defp periodic_measurements, do: [{__MODULE__, :dispatch_vm_memory, []}]
end
