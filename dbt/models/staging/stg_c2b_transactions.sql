/*
dbt staging model for C2B confirmation events.

Grain: one row per transaction_id.
*/

with raw as (
    select *
    from {{ ref('stg_mpesa_raw') }}
    where event_type = 'c2b_confirmation'
),

typed as (
    select
        transaction_id,
        phone_number as customer_phone_number,
        account_reference,
        cast(amount as numeric(12, 2)) as transaction_amount,
        to_timestamp(transaction_time, 'YYYYMMDDHH24MISS') as transaction_timestamp,
        date(to_timestamp(transaction_time, 'YYYYMMDDHH24MISS')) as transaction_date,
        extract(hour from to_timestamp(transaction_time, 'YYYYMMDDHH24MISS')) as transaction_hour,
        extract(isodow from date(to_timestamp(transaction_time, 'YYYYMMDDHH24MISS'))) as day_of_week,
        received_at as loaded_at
    from raw
    where transaction_id is not null
      and phone_number is not null
      and amount is not null
)

select
    *,
    case
        when transaction_amount >= 100000 then 'high'
        when transaction_amount >= 10000 then 'medium'
        else 'low'
    end as amount_category,
    row_number() over (
        partition by customer_phone_number
        order by transaction_timestamp
    ) as transaction_sequence_per_customer,
    current_timestamp as processed_at
from typed
