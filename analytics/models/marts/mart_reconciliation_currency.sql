-- Зерно: run/merchant/currency. Я не складываю разные валюты или разные run.
with balances as (
    select run_id, merchant_id, currency, count(*) as order_count,
           count(*) filter (where state = 'blocked') as blocked_orders,
           count(*) filter (where state = 'pending') as pending_orders,
           sum(expected_capture_minor) as expected_capture_minor,
           sum(expected_refund_minor) as expected_refund_minor,
           sum(actual_capture_minor) as known_actual_capture_minor,
           sum(actual_refund_minor) as known_actual_refund_minor
    from {{ ref('fct_order_reconciliation') }}
    group by run_id, merchant_id, currency
), findings as (
    select run_id, merchant_id, currency, count(*) as finding_count
    from {{ ref('stg_run_findings') }} group by run_id, merchant_id, currency
)
select coalesce(b.run_id, f.run_id) as run_id,
       coalesce(b.merchant_id, f.merchant_id) as merchant_id,
       coalesce(b.currency, f.currency) as currency,
       coalesce(b.order_count, 0) as order_count, coalesce(b.blocked_orders, 0) as blocked_orders,
       coalesce(b.pending_orders, 0) as pending_orders, coalesce(f.finding_count, 0) as finding_count,
       b.expected_capture_minor, b.expected_refund_minor,
       b.known_actual_capture_minor, b.known_actual_refund_minor
from balances b full join findings f using (run_id, merchant_id, currency)
