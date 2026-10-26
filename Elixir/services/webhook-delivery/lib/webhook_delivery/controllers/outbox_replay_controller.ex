defmodule PesaGuard.WebhookDelivery.OutboxReplayController do
  use Phoenix.Controller, formats: [:json]

  alias PesaGuard.WebhookDelivery.Persistence.PostgresStore

  @required_scope "outbox:replay"

  def replay(conn, %{"event_id" => event_id, "reason" => reason})
      when is_binary(event_id) and byte_size(event_id) in 1..200 and is_binary(reason) do
    context = conn.assigns.tenant_context
    claims = context.claims

    cond do
      not authorized?(claims) ->
        conn |> put_status(:forbidden) |> json(%{error: "outbox_replay_forbidden"})

      String.length(String.trim(reason)) not in 10..500 ->
        conn |> put_status(:unprocessable_entity) |> json(%{error: "replay_reason_must_be_10_to_500_characters"})

      true ->
        case PostgresStore.replay_dead_letter(context.tenant_id, event_id, context.subject, String.trim(reason)) do
          :ok ->
            json(conn, %{data: %{event_id: event_id, status: "pending"}, replay_accepted: true})

          {:error, :not_found_or_not_dead_lettered} ->
            conn |> put_status(:not_found) |> json(%{error: "dead_letter_event_not_found"})

          {:error, :unavailable} ->
            conn |> put_status(:service_unavailable) |> json(%{error: "persistence_unavailable"})
        end
    end
  end

  def replay(conn, _params) do
    conn |> put_status(:bad_request) |> json(%{error: "event_id_and_reason_required"})
  end

  defp authorized?(claims) do
    scopes = Map.get(claims, "scopes", [])
    scope_string = Map.get(claims, "scope", "")

    @required_scope in scopes or
      (is_binary(scope_string) and @required_scope in String.split(scope_string))
  end
end
