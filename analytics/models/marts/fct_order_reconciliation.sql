-- Зерно: один OMS balance на run/merchant/order/currency.
select b.*,
       case when b.state <> 'blocked' then coalesce(c.capture_minor, 0) end as receipt_capture_minor,
       case when b.state <> 'blocked' then coalesce(r.refund_minor, 0) end as receipt_refund_minor,
       case when b.state <> 'blocked' then coalesce(c.capture_events, 0) end as capture_events,
       case when b.state <> 'blocked' then coalesce(r.refund_events, 0) end as refund_events
from {{ ref('stg_run_balances') }} b
left join {{ ref('int_capture_by_order') }} c using (run_id, merchant_id, order_id, currency)
left join {{ ref('int_refund_by_order') }} r using (run_id, merchant_id, order_id, currency)
