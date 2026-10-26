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

    test "serializes consent revocation with the enqueue-time policy decision" do
      tenant = "policy-lock-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      recipient = "recipient-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      actor = "internal-policy-adapter"
      intent = %{"recipient_ref" => recipient, "channel" => "email", "purpose" => "account_activity"}

      assert :ok = PolicyStore.record_consent(tenant, recipient, "account_activity", true, "explicit", actor)
      assert :ok = PolicyStore.set_preference(tenant, recipient, "email", true, actor)

      parent = self()

      authorization_task =
        Task.async(fn ->
          Postgrex.transaction(
            PesaGuard.NotificationService.Persistence.PostgresConnection,
            fn conn ->
              assert :ok = PolicyStore.authorize_with_connection(conn, tenant, intent)
              send(parent, {:policy_locked, self()})

              receive do
                :release_policy_lock -> :authorized
              after
                2_000 -> Postgrex.rollback(conn, :test_timeout)
              end
            end
          )
        end)

      assert_receive {:policy_locked, transaction_pid}, 1_000

      revocation_task =
        Task.async(fn ->
          PolicyStore.record_consent(tenant, recipient, "account_activity", false, "revocation", actor)
        end)

      assert Task.yield(revocation_task, 100) == nil
      send(transaction_pid, :release_policy_lock)
      assert {:ok, :authorized} = Task.await(authorization_task, 2_000)
      assert :ok = Task.await(revocation_task, 2_000)
      assert {:error, :consent_not_granted} = PolicyStore.authorize(tenant, intent)
    end
  end
end
