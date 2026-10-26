if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.WebhookDelivery.Persistence.PostgresStoreTest do
    use ExUnit.Case, async: false

    alias PesaGuard.WebhookDelivery.Domain.Service
    alias PesaGuard.WebhookDelivery.Persistence.PostgresStore

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

      assert {:ok, %{rows: [[1]]}} =
               Postgrex.query(
                 PesaGuard.WebhookDelivery.Persistence.PostgresConnection,
                 "SELECT count(*)::int FROM telixo_schema_migrations WHERE service_name = $1 AND version = '001'",
                 [record.service_name]
               )
      assert {:error, :not_found} = PostgresStore.get(tenant_id <> "-other", record.record_id)

      assert {:ok, updated} =
               PostgresStore.transition(
                 tenant_id,
                 record.record_id,
                 Service.initial_state(),
                 "integration-test-transition"
               )

      assert updated.state == "integration-test-transition"
      assert {:error, :conflict} =
               PostgresStore.transition(
                 tenant_id,
                 record.record_id,
                 Service.initial_state(),
                 "stale-transition"
               )

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

      assert {:ok, _result} =
               Postgrex.query(
                 PesaGuard.WebhookDelivery.Persistence.PostgresConnection,
                 "UPDATE telixo_outbox SET lease_expires_at = now() - interval '1 second' WHERE service_name = $1 AND tenant_id = $2 AND event_id = $3",
                 [record.service_name, tenant_id, record.record_id]
               )

      assert {:ok, reclaimed_events} = PostgresStore.claim_outbox(50)
      reclaimed_event = Enum.find(reclaimed_events, &(&1.event_id == record.record_id))
      assert reclaimed_event.attempts == event.attempts + 1
      assert :ok = PostgresStore.acknowledge_outbox(tenant_id, record.record_id)

      transition_event =
        Enum.find(events, &(&1.event_type == "#{record.service_name}.record_state_changed"))

      assert transition_event
      assert transition_event.payload["payload"]["from_state"] == Service.initial_state()
      assert transition_event.payload["payload"]["to_state"] == "integration-test-transition"
      assert :ok = PostgresStore.acknowledge_outbox(tenant_id, transition_event.event_id)
    end

    test "replays a dead-lettered event atomically and records the operator reason" do
      tenant_id = "replay-tenant-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      idempotency_key = "replay-key-" <> Base.encode16(:crypto.strong_rand_bytes(8))

      assert {:ok, record, :created} =
               PostgresStore.insert_once(
                 tenant_id,
                 "replay-integration-test",
                 idempotency_key,
                 Service.initial_state(),
                 %{"purpose" => "dead-letter-replay"}
               )

      assert {:ok, claimed} = PostgresStore.claim_outbox(100)
      event =
        Enum.find(claimed, &(&1.event_id == record.record_id and &1.tenant_id == tenant_id))
      assert event
      assert :ok =
               PostgresStore.fail_outbox(
                 tenant_id,
                 record.record_id,
                 System.system_time(:second),
                 "permanent test failure",
                 true
               )

      assert :ok =
               PostgresStore.replay_dead_letter(
                 tenant_id,
                 record.record_id,
                 "operator-test",
                 "Approved recovery after correcting the downstream dependency"
               )

      assert {:ok, %{rows: [[status, attempts, last_error]]}} =
               Postgrex.query(
                 PesaGuard.WebhookDelivery.Persistence.PostgresConnection,
                 "SELECT status, attempts, last_error FROM telixo_outbox WHERE service_name = $1 AND tenant_id = $2 AND event_id = $3",
                 [record.service_name, tenant_id, record.record_id]
               )

      assert status == "pending"
      assert attempts == 0
      assert is_nil(last_error)

      assert {:ok, %{rows: [[actor, reason]]}} =
               Postgrex.query(
                 PesaGuard.WebhookDelivery.Persistence.PostgresConnection,
                 "SELECT actor_subject, reason FROM telixo_outbox_replay_audit WHERE service_name = $1 AND tenant_id = $2 AND event_id = $3",
                 [record.service_name, tenant_id, record.record_id]
               )

      assert actor == "operator-test"
      assert reason == "Approved recovery after correcting the downstream dependency"

      assert {:ok, replayed_events} = PostgresStore.claim_outbox(100)
      replayed =
        Enum.find(replayed_events, &(&1.event_id == record.record_id and &1.tenant_id == tenant_id))
      assert replayed
      assert replayed.attempts == 1
      assert :ok = PostgresStore.acknowledge_outbox(tenant_id, record.record_id)
    end
  end
end
