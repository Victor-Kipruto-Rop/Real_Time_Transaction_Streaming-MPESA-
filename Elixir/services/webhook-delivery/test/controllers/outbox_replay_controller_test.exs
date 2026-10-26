defmodule PesaGuard.WebhookDelivery.OutboxReplayControllerTest do
  use ExUnit.Case, async: false

  alias PesaGuard.WebhookDelivery.Router

  @secret String.duplicate("replay-controller-test-secret-", 2)

  setup do
    previous = System.get_env("JWT_SECRET")
    System.put_env("JWT_SECRET", @secret)

    on_exit(fn ->
      if previous do
        System.put_env("JWT_SECRET", previous)
      else
        System.delete_env("JWT_SECRET")
      end
    end)

    :ok
  end

  test "rejects replay requests without the operator scope" do
    conn =
      request(%{
        "tenant_id" => "tenant-replay-test",
        "sub" => "ordinary-user",
        "iss" => "telixo",
        "aud" => "telixo",
        "exp" => System.system_time(:second) + 60
      })

    assert conn.status == 403
    assert Jason.decode!(conn.resp_body)["error"] == "outbox_replay_forbidden"
  end

  test "validates replay reason before attempting database changes" do
    conn =
      request(%{
        "tenant_id" => "tenant-replay-test",
        "sub" => "operator-user",
        "iss" => "telixo",
        "aud" => "telixo",
        "exp" => System.system_time(:second) + 60,
        "scope" => "outbox:replay"
      }, %{"reason" => "short"})

    assert conn.status == 422
    assert Jason.decode!(conn.resp_body)["error"] == "replay_reason_must_be_10_to_500_characters"
  end

  defp request(claims, body \\ %{"reason" => "Approved replay after dependency repair"}) do
    token = sign_token(claims)

    Plug.Test.conn("POST", "/v1/outbox/event-test-id/replay", Jason.encode!(body))
    |> Plug.Conn.put_req_header("content-type", "application/json")
    |> Plug.Conn.put_req_header("authorization", "Bearer " <> token)
    |> Router.call(Router.init([]))
  end

  defp sign_token(claims) do
    header = Base.url_encode64(Jason.encode!(%{"alg" => "HS256", "typ" => "JWT"}), padding: false)
    body = Base.url_encode64(Jason.encode!(claims), padding: false)
    signature = :crypto.mac(:hmac, :sha256, @secret, header <> "." <> body)
    header <> "." <> body <> "." <> Base.url_encode64(signature, padding: false)
  end
end
