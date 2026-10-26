CREATE TABLE IF NOT EXISTS telixo_webhook_subscriptions (
  subscription_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  target_url TEXT NOT NULL,
  event_types JSONB NOT NULL,
  secret_ciphertext BYTEA NOT NULL,
  secret_nonce BYTEA NOT NULL,
  secret_tag BYTEA NOT NULL,
  secret_fingerprint BYTEA NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS telixo_webhook_subscriptions_tenant_created_idx
  ON telixo_webhook_subscriptions (tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS telixo_customer_webhook_deliveries (
  delivery_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  subscription_id TEXT NOT NULL REFERENCES telixo_webhook_subscriptions(subscription_id),
  event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'in_progress', 'delivered', 'dead_lettered')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  lease_expires_at TIMESTAMPTZ,
  last_http_status INTEGER,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  UNIQUE (subscription_id, event_id)
);

CREATE INDEX IF NOT EXISTS telixo_customer_webhook_deliveries_ready_idx
  ON telixo_customer_webhook_deliveries (status, next_attempt_at, created_at);

CREATE INDEX IF NOT EXISTS telixo_customer_webhook_deliveries_tenant_created_idx
  ON telixo_customer_webhook_deliveries (tenant_id, created_at DESC);
