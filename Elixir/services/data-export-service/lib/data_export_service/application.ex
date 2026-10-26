defmodule PesaGuard.DataExportService.Application do
  @moduledoc """
  OTP application for Data Export Service.

  Authorized asynchronous report/export jobs, scoped artifact access, expiry and audit trail.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PesaGuard.DataExportService.Endpoint,
      {PesaGuard.DataExportService.Telemetry, []}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: PesaGuard.DataExportService.Supervisor)
  end
end
