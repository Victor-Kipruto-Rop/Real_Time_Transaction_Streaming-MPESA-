if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.WebhookDelivery.Persistence.CustomerWebhookLeaseRecoveryTest do
    use ExUnit.Case, async: false

    alias PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStore

    setup do
      original = System.get_env("WEBHOOK_SECRET_ENCRYPTION_KEY")
      System.put_env("WEBHOOK_SECRET_ENCRYPTION_KEY", Base.encode64(:crypto.strong_rand_bytes(32)))

      on_exit(fn ->
        if original,
          do: System.put_env("WEBHOOK_SECRET_ENCRYPTION_KEY", original),
          else: System.delete_env("WEBHOOK_SECRET_ENCRYPTION_KEY")
      end)

      :ok
    end

    test "reclaims an expired in-progress lease after a worker disappears" do
      tenant = "wh-lease-recovery-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      idempotency_key = "lease-subscription-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      event_id = "lease-event-" <> Base.encode16(:crypto.strong_rand_bytes(8))

      assert {:ok, subscription, :created} =
               CustomerWebhookStore.create_subscription(
                 tenant,
                 idempotency_key,
                 "https://hooks.example.test/events",
                 ["reconciliation.completed"],
                 String.duplicate("s", 32)
               )

      assert {:ok, delivery, :created} =
               CustomerWebhookStore.enqueue(
                 tenant,
                 subscription.subscription_id,
                 event_id,
                 "reconciliation.completed",
                 %{"recovery_case" => true}
               )

      assert {:ok, first_claim} = CustomerWebhookStore.claim(100)
      first_attempt = Enum.find(first_claim, &(&1.delivery_id == delivery.delivery_id))
      assert first_attempt
      assert first_attempt.attempts == 1

      # Simulate a process crash after claiming but before acknowledging or
      # recording a failure. PostgreSQL lease expiry must make the item claimable.
      assert {:ok, %{num_rows: 1}} =
               Postgrex.query(
                 PesaGuard.WebhookDelivery.Persistence.PostgresConnection,
                 """
                 UPDATE telixo_customer_webhook_deliveries
                 SET lease_expires_at = now() - interval '1 second'
                 WHERE tenant_id = $1 AND delivery_id = $2 AND status = 'in_progress'
                 """,
                 [tenant, delivery.delivery_id]
               )

      assert {:ok, recovered_batch} = CustomerWebhookStore.claim(100)
      recovered = Enum.find(recovered_batch, &(&1.delivery_id == delivery.delivery_id))
      assert recovered
      assert recovered.attempts == 2
      assert :ok = CustomerWebhookStore.acknowledge(tenant, delivery.delivery_id, 204)

      assert {:ok, history} =
               CustomerWebhookStore.list_deliveries(tenant, subscription.subscription_id)

      assert Enum.any?(history, fn row ->
               row.delivery_id == delivery.delivery_id and row.status == "delivered" and row.attempts == 2
             end)
    end
  end
end
