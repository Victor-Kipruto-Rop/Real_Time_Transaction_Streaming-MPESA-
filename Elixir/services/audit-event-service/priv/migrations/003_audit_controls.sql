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

CREATE TABLE IF NOT EXISTS telixo_audit_chain_anchors (
  tenant_id TEXT PRIMARY KEY,
  first_retained_sequence BIGINT NOT NULL CHECK (first_retained_sequence > 0),
  previous_hash TEXT NOT NULL CHECK (length(previous_hash) = 64),
  archived_through_sequence BIGINT NOT NULL CHECK (archived_through_sequence > 0),
  archive_sha256 TEXT NOT NULL CHECK (length(archive_sha256) = 64),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS telixo_audit_retention_archives (
  archive_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  first_sequence BIGINT NOT NULL,
  last_sequence BIGINT NOT NULL,
  event_count BIGINT NOT NULL,
  archive_sha256 TEXT NOT NULL CHECK (length(archive_sha256) = 64),
  archive_uri TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  request_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (first_sequence <= last_sequence)
);

CREATE INDEX IF NOT EXISTS telixo_audit_retention_archives_tenant_created_idx
  ON telixo_audit_retention_archives (tenant_id, created_at DESC);

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

DROP TRIGGER IF EXISTS telixo_audit_retention_archives_append_only
  ON telixo_audit_retention_archives;
CREATE TRIGGER telixo_audit_retention_archives_append_only
  BEFORE UPDATE OR DELETE ON telixo_audit_retention_archives
  FOR EACH ROW EXECUTE FUNCTION telixo_reject_audit_control_mutation();

-- Only the dedicated retention executor can advance the chain anchor.
DROP RULE IF EXISTS telixo_audit_chain_anchors_no_update ON telixo_audit_chain_anchors;
CREATE RULE telixo_audit_chain_anchors_no_update AS
  ON UPDATE TO telixo_audit_chain_anchors
  WHERE session_user <> 'telixo_audit_retention_executor'
     OR current_setting('telixo.audit_retention_purge', true) IS DISTINCT FROM 'authorized'
  DO INSTEAD NOTHING;

-- Keep normal writes append-only. Physical deletion requires both the dedicated
-- database role and a transaction-local authorization marker set by the task.
DROP RULE IF EXISTS telixo_audit_events_no_delete ON telixo_audit_events;
CREATE RULE telixo_audit_events_no_delete AS
  ON DELETE TO telixo_audit_events
  WHERE session_user <> 'telixo_audit_retention_executor'
     OR current_setting('telixo.audit_retention_purge', true) IS DISTINCT FROM 'authorized'
  DO INSTEAD NOTHING;
