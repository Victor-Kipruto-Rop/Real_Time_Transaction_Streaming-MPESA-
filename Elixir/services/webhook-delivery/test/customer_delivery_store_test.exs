if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.WebhookDelivery.CustomerDeliveryStoreTest do
    use ExUnit.Case, async: false
    alias PesaGuard.WebhookDelivery.CustomerDeliveryStore

    setup do
      System.put_env("WEBHOOK_ENCRYPTION_KEY", Base.encode64(:crypto.strong_rand_bytes(32)))
      :ok
    end

    test "creates tenant-scoped subscriptions and idempotently queues matching events" do
      tenant = "webhook-test-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      secret = String.duplicate("s", 40)
      assert {:ok, subscription} =
        CustomerDeliveryStore.create_subscription(
          tenant, "https://hooks.example.test/telixo", ["reconciliation.completed"], secret
        )
      assert subscription.tenant_id == tenant
      assert {:ok, [listed]} = CustomerDeliveryStore.list_subscriptions(tenant)
      assert listed.subscription_id == subscription.subscription_id
      refute Map.has_key?(listed, :secret)

      event = %{
        "event_id" => "evt-" <> Base.encode16(:crypto.strong_rand_bytes(8)),
        "event_type" => "reconciliation.completed",
        "schema_version" => 1,
        "payload" => %{"matched_count" => 3}
      }
      assert {:ok, [delivery_id]} = CustomerDeliveryStore.enqueue_event(tenant, event)
      assert {:ok, []} = CustomerDeliveryStore.enqueue_event(tenant, event)
      assert {:ok, history} = CustomerDeliveryStore.get_delivery(tenant, delivery_id)
      assert history.status == "pending"
      assert {:error, :not_found} = CustomerDeliveryStore.get_delivery(tenant <> "-other", delivery_id)
    end
  end
end
