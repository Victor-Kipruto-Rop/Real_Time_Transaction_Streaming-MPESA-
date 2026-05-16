/*
Lightweight "heatmap" aggregate.

County-level mapping requires a reference lookup (e.g. merchant/county mapping)
which is project-specific. This model provides a stable default aggregate by
`account_reference` so dashboards can be wired end-to-end.
*/

select
    transaction_date,
    account_reference,
    count(*) as transaction_count,
    sum(transaction_amount) as total_amount
from {{ ref('stg_c2b_transactions') }}
group by 1, 2
