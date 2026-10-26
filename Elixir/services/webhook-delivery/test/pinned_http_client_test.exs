defmodule PesaGuard.WebhookDelivery.PinnedHttpClientTest do
  use ExUnit.Case, async: true

  alias PesaGuard.WebhookDelivery.PinnedHttpClient

  @target %{
    host: "hooks.example.test",
    port: 443,
    address: {93, 184, 216, 34},
    request_target: "/callback"
  }

  test "rejects header injection before opening a socket" do
    assert {:error, :invalid_request} =
             PinnedHttpClient.post(@target, [{"x-test", "value\r\nHost: localhost"}], "{}")
  end

  test "rejects caller-controlled framing and routing headers before opening a socket" do
    for header <- [
          {"Host", "localhost"},
          {"content-length", "999"},
          {"Transfer-Encoding", "chunked"},
          {"Connection", "keep-alive"}
        ] do
      assert {:error, :invalid_request} = PinnedHttpClient.post(@target, [header], "{}")
    end
  end

  test "rejects malformed header tuples" do
    assert {:error, :invalid_request} = PinnedHttpClient.post(@target, [:invalid], "{}")
  end

  test "rejects malformed target metadata and oversized payloads before opening a socket" do
    assert {:error, :invalid_request} =
             PinnedHttpClient.post(%{@target | request_target: "//other.example/path"}, [], "{}")

    assert {:error, :invalid_request} =
             PinnedHttpClient.post(%{@target | port: 65_536}, [], "{}")

    assert {:error, :invalid_request} =
             PinnedHttpClient.post(@target, [], :binary.copy("x", 1_048_577))
  end
end
