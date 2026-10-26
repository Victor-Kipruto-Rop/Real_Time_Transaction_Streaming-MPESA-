defmodule PesaGuard.DataExportService.Domain.Processor do
  @moduledoc "Validates export format, requested data scope and bounded row limits."

  @formats ~w(csv jsonl)
  @scopes ~w(transactions reconciliation risk webhooks audit incidents)

  def prepare(%{"format" => format, "scope" => scope} = command)
      when is_binary(format) and is_list(scope) do
    row_limit = Map.get(command, "row_limit", 100_000)

    cond do
      format not in @formats -> {:error, :unsupported_export_format}
      scope == [] or Enum.any?(scope, &(&1 not in @scopes)) -> {:error, :invalid_export_scope}
      not is_integer(row_limit) or row_limit < 1 or row_limit > 1_000_000 -> {:error, :invalid_row_limit}
      true -> {:ok, Map.put(command, "row_limit", row_limit)}
    end
  end

  def prepare(_), do: {:error, :format_and_scope_required}
end
