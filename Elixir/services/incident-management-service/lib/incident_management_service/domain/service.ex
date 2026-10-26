defmodule PesaGuard.IncidentManagementService.Domain.Service do
  @moduledoc "incident-management-service command validation and lifecycle contract. No external side effects."

  @required_fields ["incident_id","tenant_id","severity","summary","opened_at"]
  @terminal_states ["resolved","closed"]
  @states ["open","acknowledged","investigating","mitigating","resolved","closed"]
  @transitions Enum.zip(@states, Enum.drop(@states, 1))
    |> Map.new(fn {from, to} -> {from, [to]} end)
    |> Map.put(List.last(@states), [])

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
