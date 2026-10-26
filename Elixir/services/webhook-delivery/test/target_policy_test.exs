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

  test "rejects special-use IPv6 destinations" do
    resolver = fn _host -> {:ok, [{0x2001, 0x0DB8, 0, 0, 0, 0, 0, 1}]} end

    assert {:error, :target_url_private_host_forbidden} =
             TargetPolicy.resolve_target("https://hooks.example.test/callback", resolver)
  end

  test "pins the exact validated public address and preserves the HTTPS request target" do
    resolver = fn "hooks.example.test" -> {:ok, [{93, 184, 216, 34}]} end

    assert {:ok, target} =
             TargetPolicy.resolve_target("https://hooks.example.test/callback?version=2", resolver)

    assert target.address == {93, 184, 216, 34}
    assert target.host == "hooks.example.test"
    assert target.port == 443
    assert target.request_target == "/callback?version=2"
  end

  test "rejects mixed public and private DNS answers rather than choosing the public answer" do
    resolver = fn _host -> {:ok, [{93, 184, 216, 34}, {127, 0, 0, 1}]} end

    assert {:error, :target_url_private_host_forbidden} =
             TargetPolicy.resolve_target("https://hooks.example.test/callback", resolver)
  end

  test "a changed DNS answer is re-evaluated at dispatch and private rebinding is rejected" do
    {:ok, agent} = Agent.start_link(fn -> 0 end)

    resolver = fn _host ->
      Agent.get_and_update(agent, fn
        0 -> {{:ok, [{93, 184, 216, 34}]}, 1}
        _ -> {{:ok, [{10, 0, 0, 8}]}, 2}
      end)
    end

    assert {:ok, %{address: {93, 184, 216, 34}}} =
             TargetPolicy.resolve_target("https://hooks.example.test/callback", resolver)

    assert {:error, :target_url_private_host_forbidden} =
             TargetPolicy.resolve_target("https://hooks.example.test/callback", resolver)
  end
end
