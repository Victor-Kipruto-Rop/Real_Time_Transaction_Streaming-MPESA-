CREATE TABLE IF NOT EXISTS telixo_audit_events (
  event_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  actor_type TEXT NOT NULL CHECK (actor_type IN ('user', 'service', 'system')),
  action TEXT NOT NULL CHECK (length(action) BETWEEN 1 AND 120),
  occurred_at TIMESTAMPTZ NOT NULL,
  event_payload JSONB NOT NULL,
  previous_hash TEXT,
  event_hash TEXT NOT NULL CHECK (length(event_hash) = 64),
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS telixo_audit_events_tenant_time_idx
  ON telixo_audit_events (tenant_id, recorded_at DESC, event_id DESC);

CREATE OR REPLACE FUNCTION telixo_reject_audit_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'audit events are append-only';
END;
$$;

DROP TRIGGER IF EXISTS telixo_audit_events_no_update ON telixo_audit_events;
CREATE TRIGGER telixo_audit_events_no_update
  BEFORE UPDATE OR DELETE ON telixo_audit_events
  FOR EACH ROW EXECUTE FUNCTION telixo_reject_audit_event_mutation();
