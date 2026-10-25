-- Я агрегирую capture до JOIN: несколько refunds не размножают поступления.
select run_id, merchant_id, order_id, currency,
       sum(amount_minor) as capture_minor, count(*) as capture_events
from {{ ref('stg_run_events') }}
where kind = 'capture'
group by run_id, merchant_id, order_id, currency
