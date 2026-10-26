defmodule PesaGuard.WebhookDelivery.CustomerWebhooksControllerTest do
  use ExUnit.Case, async: true

  test "event types allow documented identifiers and wildcard" do
    assert String.match?("reconciliation.completed", ~r/\A[a-zA-Z0-9._*-]+\z/)
    assert String.match?("*", ~r/\A[a-zA-Z0-9._*-]+\z/)
    refute String.match?("../secret", ~r/\A[a-zA-Z0-9._*-]+\z/)
  end
end
