defmodule PesaGuard.DataExportService.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.DataExportService.Domain.Processor

  test "rejects unsupported export formats" do
    command = %{"format" => "xlsm", "scope" => ["transactions"]}
    assert {:error, :unsupported_export_format} = Processor.prepare(command)
  end

  test "accepts bounded export scopes and formats" do
    command = %{"format" => "csv", "scope" => ["transactions"], "row_limit" => 500}
    assert {:ok, ^command} = Processor.prepare(command)
  end
end
