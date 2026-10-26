defmodule PesaGuard.WebhookDelivery.PinnedHttpClientTest do
  use ExUnit.Case, async: true

  alias PesaGuard.WebhookDelivery.PinnedHttpClient

  test "rejects header injection before opening a socket" do
    target = %{
      host: "hooks.example.test",
      port: 443,
      address: {93, 184, 216, 34},
      request_target: "/callback"
    }

    assert {:error, :invalid_request} =
             PinnedHttpClient.post(target, [{"x-test", "value\r\nHost: localhost"}], "{}")
  end

  test "rejects malformed header tuples" do
    target = %{
      host: "hooks.example.test",
      port: 443,
      address: {93, 184, 216, 34},
      request_target: "/callback"
    }

    assert {:error, :invalid_request} = PinnedHttpClient.post(target, [:invalid], "{}")
  end
  
  test "parses valid HTTP status lines from the pinned TLS response" do
    assert {:ok, 200} = PinnedHttpClient.parse_status_line("HTTP/1.1 200 OK")
    assert {:ok, 204} = PinnedHttpClient.parse_status_line("HTTP/1.0 204")
    assert {:ok, 503} = PinnedHttpClient.parse_status_line("HTTP/1.1 503 Service Unavailable")
  end

  test "rejects malformed status lines rather than treating them as delivery success" do
    assert {:error, :invalid_http_response} = PinnedHttpClient.parse_status_line("not HTTP")
    assert {:error, :invalid_http_response} = PinnedHttpClient.parse_status_line("HTTP/1.1 20 OK")
    assert {:error, :invalid_http_response} = PinnedHttpClient.parse_status_line("HTTP/1.1 2000 OK")
    assert {:error, :invalid_http_response} = PinnedHttpClient.parse_status_line("HTTP/2 503 Service Unavailable")
    assert {:error, :invalid_http_response} = PinnedHttpClient.parse_status_line("HTTP/1.1 600 Invalid")
    assert {:error, :invalid_http_response} = PinnedHttpClient.parse_status_line(nil)
  end

  test "parses the HTTP status line only after an actual CRLF delimiter" do
    assert {:ok, 204} = PinnedHttpClient.parse_status_response("HTTP/1.1 204 No Content\r\n")
    assert :more = PinnedHttpClient.parse_status_response("HTTP/1.1 204 No Content")
    assert :more = PinnedHttpClient.parse_status_response("HTTP/1.1 204 No Content\n")
  end
  
  test "rejects reserved transport headers" do
    target = %{
      host: "hooks.example.test",
      port: 443,
      address: {93, 184, 216, 34},
      request_target: "/callback"
    }

    assert {:error, :invalid_request} =
             PinnedHttpClient.post(target, [{"Host", "attacker.example"}], "{}")

    assert {:error, :invalid_request} =
             PinnedHttpClient.post(target, [{"Content-Length", "999"}], "{}")
  end

  test "rejects oversized bodies before opening a socket" do
    target = %{
      host: "hooks.example.test",
      port: 443,
      address: {93, 184, 216, 34},
      request_target: "/callback"
    }

    assert {:error, :invalid_request} =
             PinnedHttpClient.post(target, [], :binary.copy("x", 1_048_577))
  end

  test "rejects malformed target metadata before opening a socket" do
    assert {:error, :invalid_request} =
             PinnedHttpClient.post(
               %{host: "hooks.example.test", port: 443, address: {127, 0, 0, 1}, request_target: "/\r\nHost: localhost"},
               [],
               "{}"
             )
  end
end
