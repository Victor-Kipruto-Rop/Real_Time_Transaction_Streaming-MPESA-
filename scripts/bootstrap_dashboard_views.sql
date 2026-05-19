-- Bootstrap the local/EC2 warehouse for live demos.
-- This keeps dashboard schemas available even when dbt is not installed on a
-- small free-tier host.

\i /tmp/schema.sql

CREATE SCHEMA IF NOT EXISTS public_staging;
CREATE SCHEMA IF NOT EXISTS public_marts;

CREATE OR REPLACE VIEW public_staging.stg_mpesa_raw AS
SELECT
  transaction_id,
  received_at,
  source,
  COALESCE(payload ->> 'event_type', 'c2b_confirmation') AS event_type,
  phone_number,
  amount::text AS amount,
  COALESCE(payload ->> 'account_reference', payload ->> 'AccountReference', account_reference) AS account_reference,
  TO_CHAR(transaction_time, 'YYYYMMDDHH24MISS') AS transaction_time,
  payload
FROM public.mpesa_transactions_raw;

CREATE OR REPLACE VIEW public_staging.stg_c2b_transactions AS
SELECT
  transaction_id,
  phone_number AS customer_phone_number,
  COALESCE(payload ->> 'account_reference', payload ->> 'AccountReference', account_reference) AS account_reference,
  amount::numeric(12, 2) AS transaction_amount,
  transaction_time AS transaction_timestamp,
  DATE(transaction_time) AS transaction_date,
  EXTRACT(hour FROM transaction_time)::int AS transaction_hour,
  EXTRACT(isodow FROM DATE(transaction_time))::int AS day_of_week,
  received_at AS loaded_at,
  CASE
    WHEN amount >= 100000 THEN 'high'
    WHEN amount >= 10000 THEN 'medium'
    ELSE 'low'
  END AS amount_category,
  ROW_NUMBER() OVER (
    PARTITION BY phone_number
    ORDER BY transaction_time
  ) AS transaction_sequence_per_customer,
  CURRENT_TIMESTAMP AS processed_at
FROM public.mpesa_transactions_raw
WHERE COALESCE(payload ->> 'event_type', 'c2b_confirmation') = 'c2b_confirmation'
  AND transaction_id IS NOT NULL
  AND phone_number IS NOT NULL
  AND amount IS NOT NULL
  AND transaction_time IS NOT NULL;

CREATE OR REPLACE VIEW public_marts.mart_hourly_volumes AS
SELECT
  DATE_TRUNC('hour', transaction_timestamp) AS hour_bucket,
  COUNT(*)::int AS transaction_count,
  COALESCE(SUM(transaction_amount), 0)::numeric(15, 2) AS total_amount,
  COUNT(DISTINCT customer_phone_number)::int AS unique_customers,
  CURRENT_TIMESTAMP AS created_at
FROM public_staging.stg_c2b_transactions
GROUP BY 1;

CREATE OR REPLACE VIEW public_marts.mart_daily_transactions AS
SELECT
  transaction_date,
  customer_phone_number,
  account_reference,
  COUNT(DISTINCT transaction_id)::int AS transaction_count,
  COALESCE(SUM(transaction_amount), 0)::numeric(15, 2) AS total_transaction_value,
  COALESCE(AVG(transaction_amount), 0)::numeric(12, 2) AS avg_transaction_amount,
  MIN(transaction_amount)::numeric(12, 2) AS min_transaction_amount,
  MAX(transaction_amount)::numeric(12, 2) AS max_transaction_amount,
  ROUND(STDDEV(transaction_amount), 2) AS stddev_transaction_amount,
  COUNT(*) FILTER (WHERE transaction_hour >= 6 AND transaction_hour < 12)::int AS morning_transactions,
  COUNT(*) FILTER (WHERE transaction_hour >= 12 AND transaction_hour < 18)::int AS afternoon_transactions,
  COUNT(*) FILTER (WHERE transaction_hour >= 18 OR transaction_hour < 6)::int AS evening_transactions,
  ROUND(100.0 * COUNT(*) FILTER (WHERE amount_category = 'low') / NULLIF(COUNT(*), 0), 2) AS pct_low_amount,
  ROUND(100.0 * COUNT(*) FILTER (WHERE amount_category = 'medium') / NULLIF(COUNT(*), 0), 2) AS pct_medium_amount,
  ROUND(100.0 * COUNT(*) FILTER (WHERE amount_category = 'high') / NULLIF(COUNT(*), 0), 2) AS pct_high_amount,
  MAX(CASE WHEN day_of_week IN (6, 7) THEN 1 ELSE 0 END)::int AS is_weekend,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM public_staging.stg_c2b_transactions
GROUP BY transaction_date, customer_phone_number, account_reference;

CREATE OR REPLACE VIEW public_marts.mart_county_heatmap AS
SELECT
  transaction_date,
  account_reference,
  COUNT(*)::int AS transaction_count,
  COALESCE(SUM(transaction_amount), 0)::numeric(15, 2) AS total_amount
FROM public_staging.stg_c2b_transactions
GROUP BY 1, 2;
