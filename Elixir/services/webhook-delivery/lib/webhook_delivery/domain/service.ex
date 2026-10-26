defmodule TELIXO.WebhookDelivery.Domain.Service do
  @moduledoc "Webhook Delivery deterministic validation and lifecycle contract; no external side effects."
  @required_fields ["event_id","tenant_id","subscription_id","target_url","payload"]
  @terminal_states ["delivered","dead_lettered"]
  @states ["pending","in_progress","delivered","retryable_failure","dead_lettered"]
  @transitions %{"pending" => ["in_progress"], "in_progress" => ["delivered"], "delivered" => ["retryable_failure"], "retryable_failure" => ["dead_lettered"], "dead_lettered" => []}
  @spec validate_command(term()) :: {:ok, map()} | {:error, {:missing_fields, [binary()]}}
  def validate_command(command) when is_map(command) do
    missing = Enum.filter(@required_fields, fn key -> blank?(Map.get(command, key)) end)
    if missing == [], do: {:ok, command}, else: {:error, {:missing_fields, missing}}
  end
  def validate_command(_), do: {:error, {:missing_fields, @required_fields}}
  def terminal?(state) when is_binary(state), do: state in @terminal_states
  def terminal?(_), do: false
  def transition_allowed?(from, to) when is_binary(from) and is_binary(to), do: to in Map.get(@transitions, from, [])
  def transition_allowed?(_, _), do: false
  def initial_state, do: hd(@states)
  defp blank?(nil), do: true
  defp blank?(value) when is_binary(value), do: String.trim(value) == ""
  defp blank?(_), do: false
end