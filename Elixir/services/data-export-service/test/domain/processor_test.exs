defmodule PesaGuard.DataExportService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.DataExportService.Domain.Processor

  test "rejects unsupported export formats" do
    command = %{"format" => "xlsm", "scope" => ["transactions"]}
    assert {:error, :unsupported_export_format} = Processor.prepare(command)
  end
end
