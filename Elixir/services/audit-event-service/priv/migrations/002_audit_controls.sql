CREATE TABLE IF NOT EXISTS telixo_audit_retention_policies (
  tenant_id TEXT PRIMARY KEY,
  retention_days INTEGER NOT NULL DEFAULT 2555 CHECK (retention_days BETWEEN 30 AND 36500),
  legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
  updated_by TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS telixo_audit_privileged_access_log (
  access_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT NOT NULL,
  request_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS telixo_audit_privileged_access_tenant_created_idx
  ON telixo_audit_privileged_access_log (tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS telixo_audit_integrity_verification_runs (
  verification_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  verifier_identity TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('verified', 'failed')),
  verified_event_count BIGINT NOT NULL DEFAULT 0,
  last_verified_sequence BIGINT,
  last_verified_hash TEXT,
  failure_event_id TEXT,
  failure_code TEXT,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS telixo_audit_integrity_runs_tenant_completed_idx
  ON telixo_audit_integrity_verification_runs (tenant_id, completed_at DESC);

CREATE OR REPLACE FUNCTION telixo_reject_audit_control_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'audit control history is append-only';
END;
$$;

DROP TRIGGER IF EXISTS telixo_audit_privileged_access_append_only
  ON telixo_audit_privileged_access_log;
CREATE TRIGGER telixo_audit_privileged_access_append_only
  BEFORE UPDATE OR DELETE ON telixo_audit_privileged_access_log
  FOR EACH ROW EXECUTE FUNCTION telixo_reject_audit_control_mutation();

DROP TRIGGER IF EXISTS telixo_audit_integrity_runs_append_only
  ON telixo_audit_integrity_verification_runs;
CREATE TRIGGER telixo_audit_integrity_runs_append_only
  BEFORE UPDATE OR DELETE ON telixo_audit_integrity_verification_runs
  FOR EACH ROW EXECUTE FUNCTION telixo_reject_audit_control_mutation();
