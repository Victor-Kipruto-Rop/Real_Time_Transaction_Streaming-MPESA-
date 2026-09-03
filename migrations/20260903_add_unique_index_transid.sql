-- migrations/20260903_add_unique_index_transid.sql
-- Purpose: Add a UNIQUE index on transactions(trans_id) to prevent duplicate rows.
-- Safety: This file first checks for duplicates and will report them; do not run until duplicates are resolved.
--
-- IMPORTANT:
-- - For large tables, prefer to create the index WITH CONCURRENTLY to avoid locks:
--   CREATE UNIQUE INDEX CONCURRENTLY ux_transactions_trans_id ON transactions (trans_id);
-- - CONCURRENTLY cannot run inside a transaction block. Use psql or your DB tool to run it outside a transaction.
-- - This SQL file includes a pre-check. If rows are returned from the SELECT below, dedupe first.

-- 1) Pre-check: are there duplicates?
-- If this query returns any rows, stop and dedupe before creating the unique index.
SELECT trans_id, COUNT(*) AS cnt
FROM transactions
GROUP BY trans_id
HAVING COUNT(*) > 1
LIMIT 10;

-- If the above returned zero rows, you may proceed to create the unique index.
-- Recommended (Postgres): run the following outside a transaction to avoid locking writes:
--   CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_transactions_trans_id ON transactions (trans_id);

-- Fallback (non-concurrent) — may lock the table for writes for the duration:
--   CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_trans_id ON transactions (trans_id);

-- Rollback (if needed):
--   DROP INDEX CONCURRENTLY IF EXISTS ux_transactions_trans_id;
