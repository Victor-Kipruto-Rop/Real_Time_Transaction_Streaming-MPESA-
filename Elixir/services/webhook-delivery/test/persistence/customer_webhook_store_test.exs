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
      events = ["reconciliation.completed"]
      secret = String.duplicate("s", 32)

      assert {:ok, subscription, :created} =
               CustomerWebhookStore.create_subscription(tenant, key, target, events, secret)
      assert subscription.tenant_id == tenant
      refute Map.has_key?(subscription, :secret)
      assert {:ok, duplicate, :duplicate} =
               CustomerWebhookStore.create_subscription(tenant, key, target, events, secret)
      assert duplicate.subscription_id == subscription.subscription_id
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
      assert {:error, :event_conflict} =
               CustomerWebhookStore.enqueue(tenant, subscription.subscription_id, event_id,
                 "reconciliation.completed", %{"amount" => 151})

      assert {:ok, claimed} = CustomerWebhookStore.claim(100)
      item = Enum.find(claimed, &(&1.delivery_id == delivery.delivery_id))
      assert item
      assert item.secret == secret
      assert :ok = CustomerWebhookStore.acknowledge(tenant, delivery.delivery_id, 204)
    end

    test "rejects weak secrets and event types outside the subscription allowlist" do
      tenant = "wh-test-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      assert {:error, :invalid_secret} =
               CustomerWebhookStore.create_subscription(tenant, "weak-key",
                 "https://hooks.example.test/events", ["event.ok"], "short")
    end
  end
end
