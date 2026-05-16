#!/bin/bash
# M-Pesa Project 01: Database setup script
# Initializes database schema and loads sample data

set -e

echo "=== M-Pesa Transaction Streaming Database Setup ==="

# Source environment variables
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-mpesa}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-}

echo "Creating database schema..."

# Avoid interactive password prompts in CI/local runs.
if [ -n "${POSTGRES_PASSWORD}" ]; then
    export PGPASSWORD="${POSTGRES_PASSWORD}"
fi

# Create main transactions table
psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" << 'EOF'
-- Drop existing tables if they exist (for clean slate)
DROP TABLE IF EXISTS mpesa_transactions_raw CASCADE;
DROP TABLE IF EXISTS stg_mpesa_raw CASCADE;
DROP TABLE IF EXISTS stg_c2b_transactions CASCADE;
DROP TABLE IF EXISTS mart_daily_transactions CASCADE;
DROP TABLE IF EXISTS mart_hourly_volumes CASCADE;
DROP TABLE IF EXISTS mart_county_heatmap CASCADE;

-- Raw M-Pesa transactions table
CREATE TABLE IF NOT EXISTS mpesa_transactions_raw (
    transaction_id VARCHAR(20) PRIMARY KEY,
    phone_number VARCHAR(15) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    account_reference VARCHAR(255),
    transaction_time TIMESTAMP NOT NULL,
    source VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_phone_number ON mpesa_transactions_raw(phone_number);
CREATE INDEX idx_transaction_time ON mpesa_transactions_raw(transaction_time);
CREATE INDEX idx_source ON mpesa_transactions_raw(source);

-- Staging table for C2B transactions
CREATE TABLE IF NOT EXISTS stg_c2b_transactions (
    transaction_id VARCHAR(20) PRIMARY KEY,
    phone_number VARCHAR(15) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    county VARCHAR(50),
    merchant_name VARCHAR(255),
    transaction_date DATE NOT NULL,
    transaction_hour INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_c2b_phone ON stg_c2b_transactions(phone_number);
CREATE INDEX idx_c2b_date ON stg_c2b_transactions(transaction_date);
CREATE INDEX idx_c2b_hour ON stg_c2b_transactions(transaction_hour);

-- Mart tables
CREATE TABLE IF NOT EXISTS mart_hourly_volumes (
    date_hour TIMESTAMP PRIMARY KEY,
    transaction_count INT NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    unique_customers INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mart_daily_transactions (
    transaction_date DATE PRIMARY KEY,
    transaction_count INT NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    average_amount DECIMAL(10, 2) NOT NULL,
    min_amount DECIMAL(10, 2),
    max_amount DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mart_county_heatmap (
    date_hour TIMESTAMP NOT NULL,
    county VARCHAR(50) NOT NULL,
    transaction_count INT NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    PRIMARY KEY (date_hour, county),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_county_hour ON mart_county_heatmap(county, date_hour);
EOF

echo "✓ Database setup complete!"
