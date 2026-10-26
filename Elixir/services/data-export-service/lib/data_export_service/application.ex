defmodule PesaGuard.DataExportService.Application do
  @moduledoc "OTP application for data-export-service."
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{PesaGuard.DataExportService.Telemetry, []}] ++
        PesaGuard.DataExportService.Persistence.PostgresStore.children() ++
        [PesaGuard.DataExportService.Endpoint]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PesaGuard.DataExportService.Supervisor
    )
  end
end
