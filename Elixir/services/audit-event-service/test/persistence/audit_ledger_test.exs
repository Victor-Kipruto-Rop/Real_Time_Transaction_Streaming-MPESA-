if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.AuditEventService.Persistence.AuditLedgerTest do
    use ExUnit.Case, async: false

    alias PesaGuard.AuditEventService.Persistence.AuditLedger

    test "appends a tenant hash chain, deduplicates idempotently, and emits an outbox event" do
      tenant = "audit-ledger-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      idempotency_key = "audit-key-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      event = %{
        "actor_type" => "service",
        "action" => "reconciliation.completed",
        "occurred_at" => "2026-10-27T00:00:00Z",
        "metadata" => %{"source" => "test"}
      }

      assert {:ok, first, :created} = AuditLedger.append(tenant, idempotency_key, event)
      assert first.tenant_sequence == 1
      assert first.previous_hash == nil
      assert byte_size(first.event_hash) == 64
      assert :ok = AuditLedger.verify_chain(tenant)

      assert {:ok, duplicate, :duplicate} = AuditLedger.append(tenant, idempotency_key, event)
      assert duplicate.event_id == first.event_id
      assert {:error, :conflict} =
               AuditLedger.append(tenant, idempotency_key, Map.put(event, "action", "different.action"))

      next_event = Map.put(event, "action", "risk.flagged")
      assert {:ok, second, :created} =
               AuditLedger.append(tenant, idempotency_key <> "-next", next_event)
      assert second.tenant_sequence == 2
      assert second.previous_hash == first.event_hash
      assert :ok = AuditLedger.verify_chain(tenant)

      assert {:ok, fetched} = AuditLedger.get(tenant, first.event_id)
      assert fetched.event_hash == first.event_hash
      assert {:error, :not_found} = AuditLedger.get(tenant <> "-other", first.event_id)

      assert {:ok, %{rows: [[2]]}} =
               Postgrex.query(
                 PesaGuard.AuditEventService.Persistence.PostgresConnection,
                 "SELECT count(*)::int FROM telixo_outbox WHERE service_name = 'audit-event-service' AND tenant_id = $1",
                 [tenant]
               )
    end

    test "database trigger rejects audit event mutation" do
      tenant = "audit-immutable-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      event = %{
        "actor_type" => "system",
        "action" => "security.policy_checked",
        "occurred_at" => "2026-10-27T00:00:00Z"
      }

      assert {:ok, record, :created} = AuditLedger.append(tenant, "immutable-key", event)

      assert {:ok, %{num_rows: 0}} =
               Postgrex.query(
                 PesaGuard.AuditEventService.Persistence.PostgresConnection,
                 "UPDATE telixo_audit_events SET action = 'tampered' WHERE tenant_id = $1 AND event_id = $2",
                 [tenant, record.event_id]
               )

      assert {:ok, unchanged} = AuditLedger.get(tenant, record.event_id)
      assert unchanged.action == "security.policy_checked"
      assert :ok = AuditLedger.verify_chain(tenant)
    end
  end
end
