if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.NotificationService.Persistence.PolicyStoreTest do
    use ExUnit.Case, async: false

    alias PesaGuard.NotificationService.Persistence.PolicyStore

    test "authorizes only persisted consent and preferences and fails closed on suppression or revocation" do
      tenant = "policy-test-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      recipient = "recipient-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      actor = "internal-policy-adapter"
      intent = %{"recipient_ref" => recipient, "channel" => "email", "purpose" => "account_activity"}

      assert {:error, :consent_record_unavailable} = PolicyStore.authorize(tenant, intent)
      assert :ok = PolicyStore.record_consent(tenant, recipient, "account_activity", true, "explicit", actor)
      assert :ok = PolicyStore.set_preference(tenant, recipient, "email", true, actor)
      assert :ok = PolicyStore.authorize(tenant, intent)

      assert :ok = PolicyStore.set_preference(tenant, recipient, "email", false, actor)
      assert {:error, :channel_preference_disabled} = PolicyStore.authorize(tenant, intent)

      assert :ok = PolicyStore.set_preference(tenant, recipient, "email", true, actor)
      assert :ok = PolicyStore.suppress(tenant, recipient, "user_request", actor)
      assert {:error, :recipient_suppressed} = PolicyStore.authorize(tenant, intent)
      assert :ok = PolicyStore.unsuppress(tenant, recipient, actor)
      assert :ok = PolicyStore.authorize(tenant, intent)

      assert :ok = PolicyStore.record_consent(tenant, recipient, "account_activity", false, "revocation", actor)
      assert {:error, :consent_not_granted} = PolicyStore.authorize(tenant, intent)
      assert {:error, :consent_record_unavailable} = PolicyStore.authorize(tenant <> "-other", intent)
    end
  end
end
