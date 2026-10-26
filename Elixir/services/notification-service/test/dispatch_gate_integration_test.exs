if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.NotificationService.DispatchGateIntegrationTest do
    use ExUnit.Case, async: false

    alias PesaGuard.NotificationService.DispatchGate
    alias PesaGuard.NotificationService.Persistence.PolicyStore

    test "fresh persisted revocation and preference changes prevent provider invocation" do
      tenant = "dispatch-gate-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      recipient = "recipient-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      actor = "integration-test-policy-adapter"
      intent = %{
        "recipient_ref" => recipient,
        "channel" => "email",
        "purpose" => "account_activity"
      }
      parent = self()
      sender = fn _intent -> send(parent, :provider_invoked); {:ok, :accepted} end

      assert :ok =
               PolicyStore.record_consent(
                 tenant, recipient, "account_activity", true, "explicit", actor
               )

      assert :ok = PolicyStore.set_preference(tenant, recipient, "email", true, actor)

      assert {:ok, :accepted} = DispatchGate.dispatch(tenant, intent, sender)
      assert_received :provider_invoked

      assert :ok =
               PolicyStore.record_consent(
                 tenant, recipient, "account_activity", false, "revocation", actor
               )

      assert {:error, {:policy_denied, :consent_not_granted}} =
               DispatchGate.dispatch(tenant, intent, sender)

      refute_received :provider_invoked

      assert :ok =
               PolicyStore.record_consent(
                 tenant, recipient, "account_activity", true, "renewed_explicit_consent", actor
               )

      assert :ok = PolicyStore.set_preference(tenant, recipient, "email", false, actor)

      assert {:error, {:policy_denied, :channel_preference_disabled}} =
               DispatchGate.dispatch(tenant, intent, sender)

      refute_received :provider_invoked
      assert {:error, {:policy_denied, :consent_record_unavailable}} =
               DispatchGate.dispatch(tenant <> "-other", intent, sender)

      refute_received :provider_invoked
    end
  end
end
