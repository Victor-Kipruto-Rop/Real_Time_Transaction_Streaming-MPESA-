#!/bin/bash

################################################################################
# Database Backup Script for M-Pesa Analytics Platform
#
# This script creates backups of the PostgreSQL database with rotation.
#
# Usage:
#   ./scripts/backup_database.sh [OPTIONS]
#
# Options:
#   -h, --help          Show this help message
#   -d, --database      Database name (default: mpesa_analytics)
#   -u, --user          Database user (default: data_engineer)
#   -H, --host          Database host (default: localhost)
#   -p, --port          Database port (default: 5432)
#   -o, --output        Output directory (default: ./backups)
#   -r, --retention     Retention days (default: 30)
#   -c, --compress      Compress backup (default: true)
#   -s, --s3            Upload to S3 bucket
################################################################################

set -euo pipefail

# Default configuration
DB_NAME="${POSTGRES_DB:-mpesa_analytics}"
DB_USER="${POSTGRES_USER:-data_engineer}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS=30
COMPRESS=true
S3_BUCKET=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help message
show_help() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# //g'
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        -u|--user)
            DB_USER="$2"
            shift 2
            ;;
        -H|--host)
            DB_HOST="$2"
            shift 2
            ;;
        -p|--port)
            DB_PORT="$2"
            shift 2
            ;;
        -o|--output)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -c|--compress)
            COMPRESS="$2"
            shift 2
            ;;
        -s|--s3)
            S3_BUCKET="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log_info "Starting database backup..."
log_info "Database: $DB_NAME"
log_info "Host: $DB_HOST:$DB_PORT"
log_info "Backup directory: $BACKUP_DIR"

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    log_error "pg_dump not found. Please install PostgreSQL client tools."
    exit 1
fi

# Test database connection
log_info "Testing database connection..."
if ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &> /dev/null; then
    log_error "Cannot connect to database. Please check credentials and connection."
    exit 1
fi

log_info "Connection successful."

# Create backup
log_info "Creating backup: $BACKUP_FILE"
if PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    > "$BACKUP_FILE" 2>&1; then
    
    log_info "Backup created successfully."
    
    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "Backup size: $BACKUP_SIZE"
else
    log_error "Backup failed!"
    exit 1
fi

# Compress backup if enabled
if [ "$COMPRESS" = true ]; then
    log_info "Compressing backup..."
    if gzip "$BACKUP_FILE"; then
        BACKUP_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_info "Backup compressed: $COMPRESSED_SIZE"
    else
        log_warn "Compression failed, keeping uncompressed backup."
    fi
fi

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log_info "Uploading backup to S3: s3://$S3_BUCKET/"
    
    if command -v aws &> /dev/null; then
        if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$(basename "$BACKUP_FILE")"; then
            log_info "Backup uploaded to S3 successfully."
        else
            log_warn "S3 upload failed, backup saved locally only."
        fi
    else
        log_warn "AWS CLI not found, skipping S3 upload."
    fi
fi

# Cleanup old backups
log_info "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql*" -type f -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql*" -type f | wc -l)
log_info "Remaining backups: $REMAINING"

# Create backup metadata
METADATA_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.meta"
cat > "$METADATA_FILE" << EOF
{
  "database": "$DB_NAME",
  "host": "$DB_HOST",
  "port": $DB_PORT,
  "timestamp": "$TIMESTAMP",
  "backup_file": "$(basename "$BACKUP_FILE")",
  "size": "$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")",
  "compressed": $COMPRESS,
  "s3_uploaded": $([ -n "$S3_BUCKET" ] && echo "true" || echo "false")
}
EOF

log_info "Backup metadata saved: $METADATA_FILE"

# Summary
echo ""
log_info "=== Backup Summary ==="
log_info "Backup file: $BACKUP_FILE"
log_info "Timestamp: $TIMESTAMP"
log_info "Status: SUCCESS"
echo ""

exit 0
