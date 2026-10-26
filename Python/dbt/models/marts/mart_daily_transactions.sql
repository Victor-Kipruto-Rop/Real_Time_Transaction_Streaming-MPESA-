/*
dbt mart model for daily M-Pesa transaction aggregates.

Provides daily-level KPIs for transaction volume, value, and user metrics.
Used for dashboards and reporting.

Grain: One row per customer per day
*/

with daily_transactions as (
    select
        transaction_date,
        customer_phone_number,
        account_reference,
        
        -- Transaction metrics
        count(distinct transaction_id) as transaction_count,
        sum(transaction_amount) as total_transaction_value,
        avg(transaction_amount) as avg_transaction_amount,
        min(transaction_amount) as min_transaction_amount,
        max(transaction_amount) as max_transaction_amount,
        stddev(transaction_amount) as stddev_transaction_amount,
        
        -- Time-based metrics
        count(case when transaction_hour >= 6 and transaction_hour < 12 then 1 end) as morning_transactions,
        count(case when transaction_hour >= 12 and transaction_hour < 18 then 1 end) as afternoon_transactions,
        count(case when transaction_hour >= 18 or transaction_hour < 6 then 1 end) as evening_transactions,
        
        -- Amount distribution
        count(case when amount_category = 'low' then 1 end) as low_amount_count,
        count(case when amount_category = 'medium' then 1 end) as medium_amount_count,
        count(case when amount_category = 'high' then 1 end) as high_amount_count,
        
        -- Flags
        max(case when day_of_week in (6, 7) then 1 else 0 end) as is_weekend
        
    from {{ ref('stg_c2b_transactions') }}
    
    group by
        transaction_date,
        customer_phone_number,
        account_reference
)

select
    transaction_date,
    customer_phone_number,
    account_reference,
    
    -- Counts
    transaction_count,
    
    -- Amounts
    total_transaction_value,
    avg_transaction_amount,
    min_transaction_amount,
    max_transaction_amount,
    round(stddev_transaction_amount, 2) as stddev_transaction_amount,
    
    -- Time distribution
    morning_transactions,
    afternoon_transactions,
    evening_transactions,
    
    -- Amount distribution percentages
    round(
        100.0 * low_amount_count / (low_amount_count + medium_amount_count + high_amount_count),
        2
    ) as pct_low_amount,
    round(
        100.0 * medium_amount_count / (low_amount_count + medium_amount_count + high_amount_count),
        2
    ) as pct_medium_amount,
    round(
        100.0 * high_amount_count / (low_amount_count + medium_amount_count + high_amount_count),
        2
    ) as pct_high_amount,
    
    -- Flags
    is_weekend,
    
    -- Metadata
    current_timestamp as created_at,
    current_timestamp as updated_at
    
from daily_transactions

order by
    transaction_date desc,
    total_transaction_value desc
