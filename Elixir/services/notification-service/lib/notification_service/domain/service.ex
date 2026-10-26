defmodule TELIXO.NotificationService.Domain.Service do
  @moduledoc "Notification Service deterministic validation and lifecycle contract; no external side effects."
  @required_fields ["event_id","tenant_id","recipient_ref","channel","template_id"]
  @terminal_states ["sent","permanently_failed"]
  @states ["queued","sending","sent","retryable_failure","permanently_failed","suppressed"]
  @transitions %{"queued" => ["sending"], "sending" => ["sent"], "sent" => ["retryable_failure"], "retryable_failure" => ["permanently_failed"], "permanently_failed" => ["suppressed"], "suppressed" => []}
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