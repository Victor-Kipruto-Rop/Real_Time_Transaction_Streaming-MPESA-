defmodule PesaGuard.WebhookDelivery.Domain.ProcessorTest do
  use ExUnit.Case, async: true
  alias PesaGuard.WebhookDelivery.Domain.Processor

  test "rejects cleartext webhook destinations" do
    command = %{"target_url" => "http://example.com/hook", "payload" => %{}}
    assert {:error, :target_url_must_use_https} = Processor.prepare(command)
  end

  test "rejects IP literal webhook destinations" do
    command = %{"target_url" => "https://192.168.1.10/hook", "payload" => %{}}
    assert {:error, :target_url_ip_literal_forbidden} = Processor.prepare(command)
  end

  test "accepts HTTPS webhook targets with object payloads" do
    command = %{"target_url" => "https://hooks.example.com/events", "payload" => %{"ok" => true}}
    assert {:ok, ^command} = Processor.prepare(command)
  end
end
