#!/bin/bash

################################################################################
# Database Restore Script for M-Pesa Analytics Platform
#
# This script restores PostgreSQL database from backup files.
#
# Usage:
#   ./scripts/restore_database.sh [OPTIONS] BACKUP_FILE
#
# Options:
#   -h, --help          Show this help message
#   -d, --database      Database name (default: mpesa_analytics)
#   -u, --user          Database user (default: data_engineer)
#   -H, --host          Database host (default: localhost)
#   -p, --port          Database port (default: 5432)
#   -f, --force         Force restore without confirmation
#   -c, --create        Create database if it doesn't exist
################################################################################

set -euo pipefail

# Default configuration
DB_NAME="${POSTGRES_DB:-mpesa_analytics}"
DB_USER="${POSTGRES_USER:-data_engineer}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
FORCE=false
CREATE_DB=false
BACKUP_FILE=""

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
        -f|--force)
            FORCE=true
            shift
            ;;
        -c|--create)
            CREATE_DB=true
            shift
            ;;
        *)
            if [ -z "$BACKUP_FILE" ]; then
                BACKUP_FILE="$1"
                shift
            else
                log_error "Unknown option: $1"
                show_help
            fi
            ;;
    esac
done

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    log_error "Backup file not specified."
    echo ""
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo "Try '$0 --help' for more information."
    exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

log_info "Starting database restore..."
log_info "Database: $DB_NAME"
log_info "Host: $DB_HOST:$DB_PORT"
log_info "Backup file: $BACKUP_FILE"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    log_error "psql not found. Please install PostgreSQL client tools."
    exit 1
fi

# Test database connection
log_info "Testing database connection..."
if ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" &> /dev/null; then
    log_error "Cannot connect to database server. Please check credentials and connection."
    exit 1
fi

log_info "Connection successful."

# Check if database exists
DB_EXISTS=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" = "1" ]; then
    log_warn "Database '$DB_NAME' already exists."
    
    if [ "$FORCE" = false ]; then
        echo ""
        echo -e "${YELLOW}WARNING: This will DROP and recreate the database!${NC}"
        echo -e "${YELLOW}All existing data will be LOST!${NC}"
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Restore cancelled by user."
            exit 0
        fi
    fi
    
    # Terminate existing connections
    log_info "Terminating existing connections..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" &> /dev/null || true
    
    # Drop database
    log_info "Dropping existing database..."
    if ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"; then
        log_error "Failed to drop database."
        exit 1
    fi
fi

# Create database
if [ "$CREATE_DB" = true ] || [ "$DB_EXISTS" != "1" ]; then
    log_info "Creating database..."
    if ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"; then
        log_error "Failed to create database."
        exit 1
    fi
fi

# Decompress if needed
RESTORE_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log_info "Decompressing backup file..."
    RESTORE_FILE="${BACKUP_FILE%.gz}"
    
    if ! gunzip -c "$BACKUP_FILE" > "$RESTORE_FILE"; then
        log_error "Failed to decompress backup file."
        exit 1
    fi
    
    CLEANUP_TEMP=true
else
    CLEANUP_TEMP=false
fi

# Restore database
log_info "Restoring database from backup..."
if PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$RESTORE_FILE" \
    --single-transaction \
    --set ON_ERROR_STOP=on \
    2>&1 | grep -v "^$"; then
    
    log_info "Database restored successfully."
else
    log_error "Restore failed!"
    
    # Cleanup temp file if created
    if [ "$CLEANUP_TEMP" = true ]; then
        rm -f "$RESTORE_FILE"
    fi
    
    exit 1
fi

# Cleanup temp file if created
if [ "$CLEANUP_TEMP" = true ]; then
    log_info "Cleaning up temporary files..."
    rm -f "$RESTORE_FILE"
fi

# Verify restore
log_info "Verifying restore..."
TABLE_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

log_info "Tables restored: $TABLE_COUNT"

if [ "$TABLE_COUNT" -gt 0 ]; then
    # Get row count from main table
    if PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
        "SELECT COUNT(*) as transaction_count FROM mpesa_transactions_raw;" &> /dev/null; then
        
        ROW_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
            "SELECT COUNT(*) FROM mpesa_transactions_raw;")
        log_info "Transactions restored: $ROW_COUNT"
    fi
fi

# Update statistics
log_info "Updating database statistics..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ANALYZE;" &> /dev/null

# Summary
echo ""
log_info "=== Restore Summary ==="
log_info "Database: $DB_NAME"
log_info "Backup file: $BACKUP_FILE"
log_info "Tables: $TABLE_COUNT"
log_info "Status: SUCCESS"
echo ""

exit 0
