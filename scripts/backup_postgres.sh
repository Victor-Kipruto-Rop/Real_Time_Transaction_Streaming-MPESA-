#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

PGHOST="${PGHOST:-${POSTGRES_HOST:-localhost}}"
PGPORT="${PGPORT:-${POSTGRES_PORT:-5432}}"
PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-mpesa_analytics}}"
PGUSER="${PGUSER:-${POSTGRES_USER:-data_engineer}}"
PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"
export PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD

: "${PGPASSWORD:?Set PGPASSWORD or POSTGRES_PASSWORD}"
command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 127; }

BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="$BACKUP_DIR/${PGDATABASE}_${STAMP}.dump"

pg_dump --format=custom --no-owner --no-acl --file "$OUTPUT"
sha256sum "$OUTPUT" > "$OUTPUT.sha256"
chmod 600 "$OUTPUT" "$OUTPUT.sha256"
echo "Backup created: $OUTPUT"
echo "Checksum created: $OUTPUT.sha256"
echo "Restore is not proven until scripts/restore_postgres.sh succeeds against an isolated target database."
