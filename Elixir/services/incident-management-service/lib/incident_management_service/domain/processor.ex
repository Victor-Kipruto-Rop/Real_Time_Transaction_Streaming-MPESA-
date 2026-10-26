defmodule PesaGuard.IncidentManagementService.Domain.Processor do
  @moduledoc "Validates incident severity, summary and timestamp."

  @severities ~w(low medium high critical)

  def prepare(%{"severity" => severity, "summary" => summary, "opened_at" => opened} = command)
      when is_binary(severity) and is_binary(summary) and is_binary(opened) do
    cond do
      severity not in @severities -> {:error, :invalid_severity}
      String.trim(summary) == "" or String.length(summary) > 2_000 -> {:error, :invalid_summary}
      match?({:error, _}, DateTime.from_iso8601(opened)) -> {:error, :invalid_opened_at}
      true -> {:ok, command}
    end
  end

  def prepare(_), do: {:error, :incident_fields_required}
end
