CREATE TABLE IF NOT EXISTS telixo_service_records (
  record_id TEXT PRIMARY KEY,
  service_name TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  state TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (service_name, tenant_id, kind, idempotency_key)
);

CREATE INDEX IF NOT EXISTS telixo_records_tenant_created_idx
  ON telixo_service_records (service_name, tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS telixo_outbox (
  event_id TEXT PRIMARY KEY,
  service_name TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  lease_expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS telixo_outbox_ready_idx
  ON telixo_outbox (service_name, status, next_attempt_at, created_at);
