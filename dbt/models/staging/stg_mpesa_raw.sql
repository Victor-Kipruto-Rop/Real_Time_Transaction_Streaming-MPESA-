/*
dbt staging model for raw M-Pesa events.

Source table is populated by `streaming/kafka_consumer.py` inserting into
`mpesa_transactions_raw`.
*/

with src as (
    select
        received_at,
        source,
        transaction_id,
        phone_number,
        amount,
        transaction_time,
        payload
    from {{ source('mpesa', 'mpesa_transactions_raw') }}
)

select
    transaction_id,
    received_at,
    source,
    coalesce(payload ->> 'event_type', 'c2b_confirmation') as event_type,
    phone_number,
    amount::text as amount,
    coalesce(payload ->> 'account_reference', payload ->> 'AccountReference') as account_reference,
    to_char(transaction_time, 'YYYYMMDDHH24MISS') as transaction_time,
    payload
from src
