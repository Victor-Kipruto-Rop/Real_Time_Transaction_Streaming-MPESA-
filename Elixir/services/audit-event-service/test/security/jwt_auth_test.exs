defmodule PesaGuard.AuditEventService.Security.JWTAuthTest do
  use ExUnit.Case, async: true
  alias PesaGuard.AuditEventService.Security.JWTAuth

  test "accepts a correctly signed, unexpired tenant token" do
    secret = String.duplicate("s", 40)
    now = System.system_time(:second)
    claims = %{
      "tenant_id" => "tenant-123",
      "sub" => "service-user",
      "iss" => "telixo",
      "aud" => "telixo",
      "exp" => now + 60
    }

    header = Base.url_encode64(Jason.encode!(%{"alg" => "HS256", "typ" => "JWT"}), padding: false)
    body = Base.url_encode64(Jason.encode!(claims), padding: false)
    signature = :crypto.mac(:hmac, :sha256, secret, header <> "." <> body)
    token = header <> "." <> body <> "." <> Base.url_encode64(signature, padding: false)

    assert {:ok, ^claims} = JWTAuth.verify_token(token, secret, "telixo")
  end

  test "rejects an expired token" do
    secret = String.duplicate("s", 40)
    claims = %{
      "tenant_id" => "tenant-123",
      "sub" => "service-user",
      "iss" => "telixo",
      "aud" => "telixo",
      "exp" => System.system_time(:second) - 1
    }

    header = Base.url_encode64(Jason.encode!(%{"alg" => "HS256"}), padding: false)
    body = Base.url_encode64(Jason.encode!(claims), padding: false)
    signature = :crypto.mac(:hmac, :sha256, secret, header <> "." <> body)
    token = header <> "." <> body <> "." <> Base.url_encode64(signature, padding: false)

    assert {:error, _} = JWTAuth.verify_token(token, secret, "telixo")
  end
end
