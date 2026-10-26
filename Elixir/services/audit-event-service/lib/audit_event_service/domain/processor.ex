defmodule PesaGuard.AuditEventService.Domain.Processor do
  @moduledoc "Validates immutable audit event attributes."

  @actor_types ~w(user service system)

  def prepare(%{"actor_type" => actor, "action" => action, "occurred_at" => occurred} = command)
      when is_binary(actor) and is_binary(action) and is_binary(occurred) do
    cond do
      actor not in @actor_types -> {:error, :invalid_actor_type}
      String.trim(action) == "" or String.length(action) > 120 -> {:error, :invalid_action}
      match?({:error, _}, DateTime.from_iso8601(occurred)) -> {:error, :invalid_occurred_at}
      true -> {:ok, command}
    end
  end

  def prepare(_), do: {:error, :audit_attributes_required}
end
