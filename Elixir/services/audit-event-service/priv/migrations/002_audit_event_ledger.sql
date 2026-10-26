CREATE TABLE IF NOT EXISTS telixo_audit_events (
  event_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  tenant_sequence BIGINT NOT NULL CHECK (tenant_sequence > 0),
  idempotency_key TEXT NOT NULL,
  actor_type TEXT NOT NULL CHECK (actor_type IN ('user', 'service', 'system')),
  action TEXT NOT NULL CHECK (length(action) BETWEEN 1 AND 120),
  occurred_at TIMESTAMPTZ NOT NULL,
  event_payload JSONB NOT NULL,
  previous_hash TEXT,
  event_hash TEXT NOT NULL CHECK (length(event_hash) = 64),
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, idempotency_key),
  UNIQUE (tenant_id, tenant_sequence)
);

CREATE TABLE IF NOT EXISTS telixo_audit_tenant_heads (
  tenant_id TEXT PRIMARY KEY,
  last_event_id TEXT NOT NULL,
  last_hash TEXT NOT NULL CHECK (length(last_hash) = 64),
  last_sequence BIGINT NOT NULL CHECK (last_sequence > 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS telixo_audit_events_tenant_time_idx
  ON telixo_audit_events (tenant_id, tenant_sequence DESC);

DROP RULE IF EXISTS telixo_audit_events_no_update ON telixo_audit_events;
CREATE RULE telixo_audit_events_no_update AS
  ON UPDATE TO telixo_audit_events DO INSTEAD NOTHING;

DROP RULE IF EXISTS telixo_audit_events_no_delete ON telixo_audit_events;
CREATE RULE telixo_audit_events_no_delete AS
  ON DELETE TO telixo_audit_events DO INSTEAD NOTHING;

DROP RULE IF EXISTS telixo_audit_tenant_heads_no_delete ON telixo_audit_tenant_heads;
CREATE RULE telixo_audit_tenant_heads_no_delete AS
  ON DELETE TO telixo_audit_tenant_heads DO INSTEAD NOTHING;
