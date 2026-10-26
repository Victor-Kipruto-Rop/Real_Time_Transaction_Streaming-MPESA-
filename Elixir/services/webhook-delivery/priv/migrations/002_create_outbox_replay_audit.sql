CREATE TABLE IF NOT EXISTS telixo_outbox_replay_audit (
  replay_id TEXT PRIMARY KEY,
  service_name TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  actor_subject TEXT NOT NULL,
  reason TEXT NOT NULL,
  replayed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS telixo_outbox_replay_audit_event_idx
  ON telixo_outbox_replay_audit (service_name, tenant_id, event_id, replayed_at DESC);
