defmodule PesaGuard.DataExportService.TelemetryTest do
  use ExUnit.Case, async: true

  alias PesaGuard.DataExportService.Telemetry

  test "dispatches a valid VM memory telemetry measurement" do
    handler_id = "vm-memory-test-#{System.unique_integer([:positive])}"
    test_pid = self()

    assert :ok =
             :telemetry.attach(
               handler_id,
               [:vm, :memory],
               fn event, measurements, metadata, pid ->
                 send(pid, {:telemetry_event, event, measurements, metadata})
               end,
               test_pid
             )

    on_exit(fn -> :telemetry.detach(handler_id) end)

    assert :ok = Telemetry.dispatch_vm_memory()
    assert_receive {:telemetry_event, [:vm, :memory], %{total: total}, %{}}
    assert is_integer(total) and total > 0
  end
end
