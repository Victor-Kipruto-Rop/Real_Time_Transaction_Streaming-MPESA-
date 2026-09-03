#!/usr/bin/env python3
"""
Simple dedupe helper: finds duplicate trans_id groups and deletes older duplicates,
keeping the newest row by created_at (or by id if created_at absent).

Usage:
  - Configure DATABASE_URL env var (Postgres)
  - Run in a maintenance window; test on a staging copy first.

This script deletes duplicates in batches to avoid long transactions.
"""
import os
import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname")
BATCH_SIZE = int(os.getenv("DEDUPE_BATCH_SIZE", "1000"))

DELETE_SQL = """
WITH ranked AS (
  SELECT id, trans_id,
         ROW_NUMBER() OVER (PARTITION BY trans_id ORDER BY created_at DESC, id DESC) AS rn
  FROM transactions
)
DELETE FROM transactions
WHERE id IN (
  SELECT id FROM ranked WHERE rn > 1
)
LIMIT %(limit)s;
"""

FIND_DUP_COUNT_SQL = """
SELECT COUNT(*) FROM (
  SELECT trans_id FROM transactions GROUP BY trans_id HAVING COUNT(*) > 1
) s;
"""

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(FIND_DUP_COUNT_SQL)
            dup_groups = cur.fetchone()[0]
            print(f"Duplicate trans_id groups found: {dup_groups}")
            if dup_groups == 0:
                print("No duplicates to remove.")
                return

            confirm = input("Proceed to delete duplicates in batches? (yes/no): ")
            if confirm.lower() != "yes":
                print("Aborting.")
                return

            total_deleted = 0
            while True:
                cur.execute(DELETE_SQL, {"limit": BATCH_SIZE})
                deleted = cur.rowcount
                conn.commit()
                total_deleted += deleted
                print(f"Deleted {deleted} rows (total {total_deleted})")
                if deleted == 0:
                    break

            print("Dedupe complete. Run VACUUM ANALYZE on the table after verification.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
