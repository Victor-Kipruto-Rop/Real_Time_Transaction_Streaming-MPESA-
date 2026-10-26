CREATE TABLE IF NOT EXISTS telixo_customer_webhook_attempts (
  attempt_id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  delivery_id TEXT NOT NULL REFERENCES telixo_customer_webhook_deliveries(delivery_id) ON DELETE CASCADE,
  subscription_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
  outcome TEXT NOT NULL CHECK (outcome IN ('delivered', 'retry_scheduled', 'dead_lettered', 'permanent_failure')),
  http_status INTEGER CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
  error_code TEXT,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (delivery_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS telixo_customer_webhook_attempts_tenant_delivery_idx
  ON telixo_customer_webhook_attempts (tenant_id, subscription_id, delivery_id, attempted_at DESC);
