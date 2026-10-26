defmodule PesaGuard.NotificationService.Domain.DispatchPolicy do
  @moduledoc """
  Evaluates notification policy using a policy snapshot loaded by a trusted
  internal adapter. Do not populate this context directly from the public
  notification request; it must come from the tenant's authoritative consent,
  preference, and suppression records.
  """

  @type policy_context :: %{
          required(:consent) => %{required(:granted) => boolean(), optional(:purpose) => binary()},
          required(:channel_enabled) => boolean(),
          required(:suppressed) => boolean()
        }

  @spec authorize(map(), policy_context()) :: :ok | {:error, atom()}
  def authorize(%{"channel" => channel}, context) when is_binary(channel) and is_map(context) do
    consent = Map.get(context, :consent) || Map.get(context, "consent")
    channel_enabled = Map.get(context, :channel_enabled, Map.get(context, "channel_enabled"))
    suppressed = Map.get(context, :suppressed, Map.get(context, "suppressed"))

    cond do
      not is_map(consent) ->
        {:error, :consent_record_unavailable}

      Map.get(consent, :granted, Map.get(consent, "granted")) !== true ->
        {:error, :consent_not_granted}

      not non_empty_binary(Map.get(consent, :purpose, Map.get(consent, "purpose"))) ->
        {:error, :consent_purpose_missing}

      channel_enabled !== true ->
        {:error, :channel_preference_disabled}

      suppressed !== false ->
        {:error, :recipient_suppressed}

      true ->
        :ok
    end
  end

  def authorize(_, _), do: {:error, :invalid_policy_context}

  defp non_empty_binary(value), do: is_binary(value) and String.trim(value) != ""
end
