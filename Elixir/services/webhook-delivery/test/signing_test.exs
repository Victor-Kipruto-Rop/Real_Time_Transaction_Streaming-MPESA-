defmodule PesaGuard.WebhookDelivery.SigningTest do
  use ExUnit.Case, async: true

  alias PesaGuard.WebhookDelivery.Signing

  @secret String.duplicate("s", 32)
  @body ~s({"event":"transaction.reconciled","schema_version":1})

  test "signs exact request bytes and verifies a current timestamp" do
    timestamp = 1_800_000_000
    assert {:ok, signature} = Signing.sign(@secret, timestamp, @body)
    assert String.starts_with?(signature, "v1=")

    assert :ok = Signing.verify(@secret, Integer.to_string(timestamp), signature, @body, timestamp)
  end

  test "rejects a modified body" do
    timestamp = 1_800_000_000
    assert {:ok, signature} = Signing.sign(@secret, timestamp, @body)

    assert {:error, :timestamp_outside_tolerance} =
             Signing.verify(@secret, Integer.to_string(timestamp), signature, @body <> " ", timestamp)
  end

  test "rejects signatures outside the allowed timestamp tolerance" do
    timestamp = 1_800_000_000
    assert {:ok, signature} = Signing.sign(@secret, timestamp, @body)

    assert {:error, :timestamp_outside_tolerance} =
             Signing.verify(@secret, Integer.to_string(timestamp), signature, @body, timestamp + 301)
  end

  test "rejects short secrets and malformed timestamps" do
    assert {:error, :invalid_secret} = Signing.sign("too-short", 1, @body)

    assert {:error, :invalid_timestamp} =
             Signing.verify(@secret, "not-a-time", "v1=deadbeef", @body, 1)
  end

  test "produces stable delivery metadata headers" do
    assert {:ok, headers} = Signing.headers("delivery-123", @secret, @body, 1_800_000_000)
    assert {"x-telixo-delivery-id", "delivery-123"} in headers
    assert {"x-telixo-timestamp", "1800000000"} in headers
    assert {"x-telixo-signature", "v1=" <> _} = Enum.find(headers, &(elem(&1, 0) == "x-telixo-signature"))
  end
end
