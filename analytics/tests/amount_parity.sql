-- Я сравниваю независимую SQL агрегацию receipts с сохранённым Python result.
select run_id, merchant_id, order_id, currency
from {{ ref('fct_order_reconciliation') }}
where actual_capture_minor is distinct from receipt_capture_minor
   or actual_refund_minor is distinct from receipt_refund_minor
