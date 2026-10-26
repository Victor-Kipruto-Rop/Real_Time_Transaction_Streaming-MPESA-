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

end
