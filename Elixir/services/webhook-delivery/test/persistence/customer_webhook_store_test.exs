if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStoreTest do
    use ExUnit.Case, async: false

    alias PesaGuard.WebhookDelivery.Persistence.CustomerWebhookStore

    setup do
      original = System.get_env("WEBHOOK_SECRET_ENCRYPTION_KEY")
      key = :crypto.strong_rand_bytes(32) |> Base.encode64()
      System.put_env("WEBHOOK_SECRET_ENCRYPTION_KEY", key)
      on_exit(fn ->
        if original, do: System.put_env("WEBHOOK_SECRET_ENCRYPTION_KEY", original),
          else: System.delete_env("WEBHOOK_SECRET_ENCRYPTION_KEY")
      end)
      :ok
    end

    test "persists tenant-scoped subscriptions, encrypts secrets, and deduplicates delivery events" do
      tenant = "wh-test-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      key = "subscription-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      target = "https://hooks.example.test/telixo"
      events = ["reconciliation.completed", "risk.flagged"]
      secret = String.duplicate("s", 32)

      assert {:ok, subscription, :created} =
               CustomerWebhookStore.create_subscription(tenant, key, target, events, secret)
      assert subscription.tenant_id == tenant
      refute Map.has_key?(subscription, :secret)
      assert {:ok, duplicate, :duplicate} =
               CustomerWebhookStore.create_subscription(tenant, key, target, events, secret)
      assert duplicate.subscription_id == subscription.subscription_id
      assert {:error, :idempotency_conflict} =
               CustomerWebhookStore.create_subscription(tenant, key, target, events, String.duplicate("z", 32))
      assert {:ok, []} = CustomerWebhookStore.list_subscriptions(tenant <> "-other")

      event_id = "event-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      payload = %{"amount" => 150, "currency" => "KES"}
      assert {:ok, delivery, :created} =
               CustomerWebhookStore.enqueue(tenant, subscription.subscription_id, event_id,
                 "reconciliation.completed", payload)
      assert delivery.status == "pending"
      assert {:ok, replay, :duplicate} =
               CustomerWebhookStore.enqueue(tenant, subscription.subscription_id, event_id,
                 "reconciliation.completed", payload)
      assert replay.delivery_id == delivery.delivery_id
      fanout_event_id = "fanout-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      assert {:ok, fanout_deliveries} =
               CustomerWebhookStore.enqueue_for_event(tenant, fanout_event_id,
                 "reconciliation.completed", %{"origin" => "internal-event-relay"})
      assert length(fanout_deliveries) == 1
      assert {:ok, fanout_replay} =
               CustomerWebhookStore.enqueue_for_event(tenant, fanout_event_id,
                 "reconciliation.completed", %{"origin" => "internal-event-relay"})
      assert Enum.map(fanout_replay, & &1.delivery_id) == Enum.map(fanout_deliveries, & &1.delivery_id)
      assert {:error, :event_conflict} =
               CustomerWebhookStore.enqueue(tenant, subscription.subscription_id, event_id,
                 "reconciliation.completed", %{"amount" => 151})
      assert {:error, :event_conflict} =
               CustomerWebhookStore.enqueue(tenant, subscription.subscription_id, event_id,
                 "risk.flagged", payload)

      assert {:ok, claimed} = CustomerWebhookStore.claim(100)
      item = Enum.find(claimed, &(&1.delivery_id == delivery.delivery_id))
      assert item
      assert item.secret == secret
      assert :ok = CustomerWebhookStore.acknowledge(tenant, delivery.delivery_id, 204)
      assert {:ok, history} = CustomerWebhookStore.list_deliveries(tenant, subscription.subscription_id)
      assert Enum.any?(history, &(&1.delivery_id == delivery.delivery_id and &1.status == "delivered"))


      fanout_item = Enum.find(claimed, &(&1.delivery_id == hd(fanout_deliveries).delivery_id))
      assert fanout_item
      assert :ok = CustomerWebhookStore.acknowledge(tenant, fanout_item.delivery_id, 204)
      assert {:ok, history} = CustomerWebhookStore.list_deliveries(tenant, subscription.subscription_id)
      assert Enum.any?(history, &(&1.delivery_id == delivery.delivery_id))

      failed_event_id = "failed-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      assert {:ok, failed_delivery, :created} =
               CustomerWebhookStore.enqueue(tenant, subscription.subscription_id, failed_event_id,
                 "reconciliation.completed", %{"case" => "dead-letter"})
      assert {:ok, claimed_again} = CustomerWebhookStore.claim(100)
      assert Enum.any?(claimed_again, &(&1.delivery_id == failed_delivery.delivery_id))
      assert :ok = CustomerWebhookStore.fail(tenant, failed_delivery.delivery_id, "permanent test failure", true)
      assert {:ok, %{rows: [["dead_lettered"]]}} =
               Postgrex.query(
                 PesaGuard.WebhookDelivery.Persistence.PostgresConnection,
                 "SELECT status FROM telixo_customer_webhook_deliveries WHERE tenant_id = $1 AND delivery_id = $2",
                 [tenant, failed_delivery.delivery_id]
               )
    end

    test "rejects weak secrets and event types outside the subscription allowlist" do
      tenant = "wh-test-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      assert {:error, :invalid_secret} =
               CustomerWebhookStore.create_subscription(tenant, "weak-key",
                 "https://hooks.example.test/events", ["event.ok"], "short")
    end
  end
end
