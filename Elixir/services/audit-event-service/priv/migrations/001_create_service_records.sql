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

CREATE INDEX IF NOT EXISTS telixo_service_records_tenant_created_idx
  ON telixo_service_records (service_name, tenant_id, created_at DESC);
