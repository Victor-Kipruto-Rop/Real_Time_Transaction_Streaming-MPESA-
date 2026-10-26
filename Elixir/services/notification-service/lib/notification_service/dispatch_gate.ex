defmodule PesaGuard.NotificationService.DispatchGate do
  @moduledoc """
  Last-mile authorization gate for notification provider adapters.

  Every adapter must call this immediately before the provider side effect. The
  policy is loaded from authoritative PostgreSQL records on every call; queued
  payload fields never stand in for consent or preferences. This gate does not
  itself send notifications or claim that a provider delivery occurred.
  """

  alias PesaGuard.NotificationService.Persistence.PolicyStore

  @type sender_result :: {:ok, term()} | {:error, term()}

  @spec dispatch(binary(), map(), (map() -> sender_result())) :: sender_result() | {:error, term()}
  def dispatch(tenant_id, intent, sender) when is_function(sender, 1) do
    dispatch_with(tenant_id, intent, &PolicyStore.authorize/2, sender)
  end

  def dispatch(_, _, _), do: {:error, :invalid_dispatch_request}

  @doc false
  def dispatch_with(tenant_id, intent, policy_check, sender)
      when is_binary(tenant_id) and is_map(intent) and is_function(policy_check, 2) and
             is_function(sender, 1) do
    case policy_check.(tenant_id, intent) do
      :ok ->
        invoke_sender(sender, intent)

      {:error, reason} ->
        {:error, {:policy_denied, reason}}

      _ ->
        {:error, {:policy_denied, :invalid_policy_result}}
    end
  rescue
    _ -> {:error, :dispatch_gate_unavailable}
  catch
    :exit, _ -> {:error, :dispatch_gate_unavailable}
  end

  def dispatch_with(_, _, _, _), do: {:error, :invalid_dispatch_request}

  defp invoke_sender(sender, intent) do
    case sender.(intent) do
      {:ok, _} = result -> result
      {:error, _} = result -> result
      _ -> {:error, :invalid_provider_result}
    end
  rescue
    _ -> {:error, :provider_dispatch_failed}
  catch
    :exit, _ -> {:error, :provider_dispatch_failed}
  end
end
