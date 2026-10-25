#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

BACKUP_FILE="${1:-}"
: "${RESTORE_TARGET_DATABASE_URL:?Set RESTORE_TARGET_DATABASE_URL to an isolated, disposable target database}"
if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Usage: RESTORE_TARGET_DATABASE_URL=postgresql://... CONFIRM_RESTORE=YES $0 path/to/backup.dump" >&2
  exit 2
fi
if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing restore: set CONFIRM_RESTORE=YES only after verifying the target is disposable." >&2
  exit 2
fi
command -v pg_restore >/dev/null || { echo "pg_restore is required" >&2; exit 127; }
if [[ -f "$BACKUP_FILE.sha256" ]]; then
  (cd "$(dirname "$BACKUP_FILE")" && sha256sum -c "$(basename "$BACKUP_FILE").sha256")
fi

# Intentionally no --clean/--if-exists: restores must target a new/empty database.
pg_restore --exit-on-error --no-owner --no-acl --dbname "$RESTORE_TARGET_DATABASE_URL" "$BACKUP_FILE"
echo "Restore completed to the explicitly configured isolated target."
echo "Run row-count, schema, and application-readiness checks before declaring recovery successful."
