CREATE TABLE IF NOT EXISTS telixo_notification_consents (
  tenant_id TEXT NOT NULL,
  recipient_ref TEXT NOT NULL,
  purpose TEXT NOT NULL,
  granted BOOLEAN NOT NULL,
  source TEXT NOT NULL,
  updated_by TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, recipient_ref, purpose)
);

CREATE TABLE IF NOT EXISTS telixo_notification_preferences (
  tenant_id TEXT NOT NULL,
  recipient_ref TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('email', 'sms', 'in_app')),
  enabled BOOLEAN NOT NULL,
  updated_by TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, recipient_ref, channel)
);

CREATE TABLE IF NOT EXISTS telixo_notification_suppressions (
  tenant_id TEXT NOT NULL,
  recipient_ref TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, recipient_ref)
);

CREATE INDEX IF NOT EXISTS telixo_notification_consent_lookup_idx
  ON telixo_notification_consents (tenant_id, recipient_ref, purpose);

CREATE INDEX IF NOT EXISTS telixo_notification_preference_lookup_idx
  ON telixo_notification_preferences (tenant_id, recipient_ref, channel);

CREATE INDEX IF NOT EXISTS telixo_notification_suppression_lookup_idx
  ON telixo_notification_suppressions (tenant_id, recipient_ref);
