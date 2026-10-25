-- Я сохраняю возврат отдельным плечом; net не заменяет сверку двух обязательств.
select run_id, merchant_id, order_id, currency,
       sum(amount_minor) as refund_minor, count(*) as refund_events
from {{ ref('stg_run_events') }}
where kind = 'refund'
group by run_id, merchant_id, order_id, currency
