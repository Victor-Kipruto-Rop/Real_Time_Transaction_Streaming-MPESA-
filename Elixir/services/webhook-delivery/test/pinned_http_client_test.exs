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
end
