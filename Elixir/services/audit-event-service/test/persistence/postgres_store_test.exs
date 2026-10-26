if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.AuditEventService.Persistence.PostgresStoreTest do
    use ExUnit.Case, async: false

    alias PesaGuard.AuditEventService.Domain.Service
    alias PesaGuard.AuditEventService.Persistence.PostgresStore

    test "persists JSONB payloads, enforces idempotency, and emits an outbox event" do
      tenant_id = "test-tenant-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      idempotency_key = "test-key-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      payload = %{"value" => "jsonb-round-trip", "nested" => %{"count" => 2}}

      assert {:ok, record, :created} =
               PostgresStore.insert_once(
                 tenant_id,
                 "integration-test",
                 idempotency_key,
                 Service.initial_state(),
                 payload
               )

      assert record.payload == payload
      assert {:ok, duplicate, :duplicate} =
               PostgresStore.insert_once(
                 tenant_id,
                 "integration-test",
                 idempotency_key,
                 Service.initial_state(),
                 payload
               )

      assert duplicate.record_id == record.record_id
      assert {:error, :conflict} =
               PostgresStore.insert_once(
                 tenant_id,
                 "integration-test",
                 idempotency_key,
                 Service.initial_state(),
                 Map.put(payload, "value", "different-payload")
               )

      assert {:ok, events} = PostgresStore.claim_outbox(50)
      event = Enum.find(events, &(&1.event_id == record.record_id))
      assert event
      assert event.tenant_id == tenant_id
      assert event.payload["payload"]["data"] == payload
      assert :ok = PostgresStore.acknowledge_outbox(tenant_id, record.record_id)
    end
  end
end
