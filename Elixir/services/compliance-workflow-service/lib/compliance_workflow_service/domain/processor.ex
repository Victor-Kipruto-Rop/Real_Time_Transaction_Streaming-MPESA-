defmodule PesaGuard.ComplianceWorkflowService.Domain.Processor do
  @moduledoc "Validates compliance evidence references and policy version."

  def prepare(%{"policy_version" => version, "evidence_refs" => refs} = command)
      when is_binary(version) and is_list(refs) do
    cond do
      String.trim(version) == "" -> {:error, :policy_version_required}
      length(refs) > 100 -> {:error, :too_many_evidence_refs}
      Enum.any?(refs, &(not is_binary(&1) or String.trim(&1) == "")) ->
        {:error, :invalid_evidence_reference}
      length(Enum.uniq(refs)) != length(refs) -> {:error, :duplicate_evidence_reference}
      true -> {:ok, command}
    end
  end

  def prepare(_), do: {:error, :policy_and_evidence_refs_required}
end
