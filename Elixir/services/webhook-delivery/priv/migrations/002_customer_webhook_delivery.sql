CREATE TABLE IF NOT EXISTS telixo_webhook_subscriptions (
  subscription_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  target_url TEXT NOT NULL,
  encrypted_secret TEXT NOT NULL,
  event_types TEXT[] NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, subscription_id),
  CHECK (cardinality(event_types) > 0)
);

CREATE INDEX IF NOT EXISTS telixo_webhook_subscriptions_active_idx
  ON telixo_webhook_subscriptions (tenant_id, active);

CREATE TABLE IF NOT EXISTS telixo_webhook_deliveries (
  delivery_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  subscription_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'in_progress', 'succeeded', 'dead_lettered')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  lease_expires_at TIMESTAMPTZ,
  last_status_code INTEGER,
  last_error_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  UNIQUE (tenant_id, subscription_id, event_id),
  FOREIGN KEY (tenant_id, subscription_id)
    REFERENCES telixo_webhook_subscriptions (tenant_id, subscription_id)
);

CREATE INDEX IF NOT EXISTS telixo_webhook_deliveries_ready_idx
  ON telixo_webhook_deliveries (status, next_attempt_at, created_at);

CREATE INDEX IF NOT EXISTS telixo_webhook_deliveries_tenant_history_idx
  ON telixo_webhook_deliveries (tenant_id, created_at DESC);
