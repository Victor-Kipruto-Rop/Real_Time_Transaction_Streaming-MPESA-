-- Go-owned outbox schema. Producers MUST insert their business record and this
-- outbox row in the SAME database transaction. Do not point this service at the
-- existing Python outbox until its schema and ownership are explicitly audited.
CREATE TABLE IF NOT EXISTS go_event_outbox (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL CHECK (length(topic) BETWEEN 1 AND 249),
    event_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    published_at TIMESTAMPTZ,
    dead_lettered_at TIMESTAMPTZ,
    locked_by TEXT,
    locked_until TIMESTAMPTZ,
    last_error TEXT,
    CHECK (published_at IS NULL OR dead_lettered_at IS NULL)
);
CREATE INDEX IF NOT EXISTS ix_go_event_outbox_pending
    ON go_event_outbox (next_attempt_at, created_at)
    WHERE published_at IS NULL AND dead_lettered_at IS NULL;

CREATE TABLE IF NOT EXISTS go_event_outbox_dead_letters (
    event_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    event_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    attempts INTEGER NOT NULL,
    failure_reason TEXT NOT NULL,
    dead_lettered_at TIMESTAMPTZ NOT NULL
);
