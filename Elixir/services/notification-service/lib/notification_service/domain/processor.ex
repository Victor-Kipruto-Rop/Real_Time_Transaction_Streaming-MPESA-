defmodule PesaGuard.NotificationService.Domain.Processor do
  @moduledoc "Validates notification channel and recipient reference before queueing."

  @channels ~w(email sms in_app)

  def prepare(%{"channel" => channel, "recipient_ref" => recipient} = command)
      when is_binary(channel) and is_binary(recipient) do
    cond do
      channel not in @channels -> {:error, :unsupported_channel}
      String.trim(recipient) == "" -> {:error, :recipient_ref_required}
      String.length(recipient) > 256 -> {:error, :recipient_ref_too_long}
      true -> {:ok, command}
    end
  end

  def prepare(_), do: {:error, :recipient_and_channel_required}
end
