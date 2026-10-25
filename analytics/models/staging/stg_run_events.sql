-- Я выбираю один видимый receipt на event внутри run, а не глобальный latest.
with ranked as (
    select r.run_id, r.merchant_id, p.source_event_id, p.order_id, p.currency,
           p.kind, p.amount_minor, p.occurred_at, receipt.observed_at,
           e.batch_id, e.raw_row_number, e.record_sha256,
           row_number() over (
               partition by r.run_id, r.merchant_id, p.source_event_id
               order by receipt.observed_at, e.batch_id, e.raw_row_number
           ) as receipt_rank
    from {{ ref('stg_completed_runs') }} r
    join {{ source('commerceguard', 'ops_run_evidence') }} e
      on e.run_id = r.run_id and e.merchant_id = r.merchant_id
    join {{ source('commerceguard', 'core_payment_receipt') }} receipt
      on receipt.batch_id = e.batch_id and receipt.raw_row_number = e.raw_row_number
     and receipt.merchant_id = r.merchant_id
    join {{ source('commerceguard', 'core_payment_event') }} p
      on p.merchant_id = e.merchant_id and p.source_event_id = e.source_event_id
    where p.occurred_at <= r.as_of and receipt.observed_at <= r.knowledge_at
)
select run_id, merchant_id, source_event_id, order_id, currency, kind, amount_minor,
       occurred_at, observed_at, batch_id, raw_row_number, record_sha256
from ranked where receipt_rank = 1
