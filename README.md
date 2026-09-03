## DB Migration: Add UNIQUE index on transactions.trans_id

This branch adds a safe SQL migration and tools to create a UNIQUE index on transactions.trans_id to prevent duplicate transaction rows.

Files added:
- migrations/20260903_add_unique_index_transid.sql  — SQL pre-check + instructions (create CONCURRENTLY recommended)
- alembic/versions/000000_add_unique_index_transid.py — Alembic example migration with pre-check
- tools/dedupe_transid.py — helper script to remove duplicate rows in batches (keeps newest by created_at)

Important notes
- The migration will fail if duplicate trans_id values exist. Do not run the CREATE UNIQUE INDEX step until duplicates are resolved.
- For large production tables, prefer `CREATE UNIQUE INDEX CONCURRENTLY` to avoid long locks. CONCURRENTLY cannot be executed inside a transaction.

Quick commands
- Find duplicates:

```sql
SELECT trans_id, COUNT(*) FROM transactions GROUP BY trans_id HAVING COUNT(*) > 1;
```

- Create the index (recommended outside a transaction):

```bash
psql "$DATABASE_URL" -c "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_transactions_trans_id ON transactions (trans_id);"
```

- Drop the index (if needed):

```bash
psql "$DATABASE_URL" -c "DROP INDEX CONCURRENTLY IF EXISTS ux_transactions_trans_id;"
```

Dedupe helper
- Configure `DATABASE_URL` env var and run `python3 tools/dedupe_transid.py` in a maintenance window to remove duplicates in batches.

Production checklist (summary)
1) Backup: create a DB snapshot or logical backup.
2) Run the duplicate pre-check (see migrations/20260903_add_unique_index_transid.sql). If duplicates exist, run the dedupe helper on a staging copy and then on production during maintenance.
3) Create index with CONCURRENTLY outside a transaction, or run non-concurrent index if you can accept table locks.
4) Verify index existence and test inserts for duplicate rejection.
5) Monitor application and run VACUUM ANALYZE after large deletions.

See the migration SQL file and alembic revision for full guidance and caveats.
