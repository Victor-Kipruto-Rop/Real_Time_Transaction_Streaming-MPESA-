defmodule PesaGuard.WorkflowOrchestrator.Domain.Service do
  @moduledoc "workflow-orchestrator command validation and lifecycle rules."

  @required_fields ["workflow_id", "tenant_id", "workflow_type", "version"]
  @terminal_states ["succeeded", "cancelled"]
  @states ["pending", "running", "waiting", "succeeded", "failed", "cancelled"]
  @transitions %{
    "pending" => ["running", "cancelled"],
    "running" => ["waiting", "succeeded", "failed", "cancelled"],
    "waiting" => ["running", "cancelled"],
    "succeeded" => [],
    "failed" => ["running", "cancelled"],
    "cancelled" => []
  }

  @spec validate_command(term()) :: {:ok, map()} | {:error, {:missing_fields, [binary()]}}
  def validate_command(command) when is_map(command) do
    missing =
      Enum.filter(@required_fields, fn key ->
        blank?(Map.get(command, key))
      end)

    if missing == [], do: {:ok, command}, else: {:error, {:missing_fields, missing}}
  end

  def validate_command(_), do: {:error, {:missing_fields, @required_fields}}
  def terminal?(state) when is_binary(state), do: state in @terminal_states
  def terminal?(_), do: false

  def transition_allowed?(from, to) when is_binary(from) and is_binary(to) do
    to in Map.get(@transitions, from, [])
  end

  def transition_allowed?(_, _), do: false
  def initial_state, do: hd(@states)

  defp blank?(nil), do: true
  defp blank?(value) when is_binary(value), do: String.trim(value) == ""
  defp blank?(_), do: false
end
