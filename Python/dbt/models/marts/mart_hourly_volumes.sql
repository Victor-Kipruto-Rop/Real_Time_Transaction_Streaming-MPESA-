/*
Hourly volumes for confirmed C2B transactions.

Grain: one row per hour.
*/

with base as (
    select
        date_trunc('hour', transaction_timestamp) as hour_bucket,
        count(*) as transaction_count,
        sum(transaction_amount) as total_amount,
        count(distinct customer_phone_number) as unique_customers
    from {{ ref('stg_c2b_transactions') }}
    group by 1
)

select
    hour_bucket,
    transaction_count,
    total_amount,
    unique_customers,
    current_timestamp as created_at
from base
order by hour_bucket desc
