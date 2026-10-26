defmodule PesaGuard.WorkflowOrchestrator.Domain.Processor do
  @moduledoc "Validates versioned workflow definitions before creating workflow state."

  def prepare(%{"workflow_type" => type, "version" => version} = command)
      when is_binary(type) and is_integer(version) do
    cond do
      not Regex.match?(~r/^[a-z][a-z0-9_.-]{1,79}$/, type) -> {:error, :invalid_workflow_type}
      version < 1 -> {:error, :invalid_workflow_version}
      true -> {:ok, command}
    end
  end

  def prepare(_), do: {:error, :workflow_type_and_integer_version_required}
end
