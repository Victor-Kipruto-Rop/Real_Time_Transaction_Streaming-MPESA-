defmodule PesaGuard.WebhookDelivery.TargetPolicyTest do
  use ExUnit.Case, async: true

  alias PesaGuard.WebhookDelivery.TargetPolicy

  test "rejects cleartext and IP-literal targets before DNS resolution" do
    assert {:error, :target_url_must_use_https} = TargetPolicy.validate("http://example.com/hook")
    assert {:error, :target_url_ip_literal_forbidden} = TargetPolicy.validate("https://127.0.0.1/hook")
    assert {:error, :target_url_ip_literal_forbidden} = TargetPolicy.validate("https://[::1]/hook")
  end

  test "rejects malformed targets" do
    assert {:error, :target_url_host_required} = TargetPolicy.validate("https:///hook")
  end
end
