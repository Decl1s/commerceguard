-- Зерно: run/merchant/order/currency. Я не вывожу сроки старого kernel заново.
select r.run_id, r.merchant_id, r.mode, r.as_of, r.knowledge_at, r.ruleset_version,
       r.result_version, r.result_sha256, r.oms_snapshot_id,
       o.batch_id as oms_batch_id, o.raw_row_number as oms_raw_row_number,
       b->>'order_id' as order_id, b->>'currency' as currency,
       b->>'state' as state,
       (b->>'expected_capture_minor')::bigint as expected_capture_minor,
       (b->>'expected_refund_minor')::bigint as expected_refund_minor,
       (b->>'actual_capture_minor')::bigint as actual_capture_minor,
       (b->>'actual_refund_minor')::bigint as actual_refund_minor,
       (b->>'capture_delta_minor')::bigint as capture_delta_minor,
       (b->>'refund_delta_minor')::bigint as refund_delta_minor,
       (b->>'capture_due_at')::timestamptz as capture_due_at,
       (b->>'refund_due_at')::timestamptz as refund_due_at,
       b->>'capture_state' as capture_state, b->>'refund_state' as refund_state,
       (b->>'expectation_version')::integer as expectation_version,
       (r.result_version = 3) as has_per_leg_context
from {{ ref('stg_completed_runs') }} r
cross join lateral jsonb_array_elements(r.payload_json->'balances') b
join {{ source('commerceguard', 'core_order_expectation') }} o
  on o.snapshot_id = r.oms_snapshot_id and o.merchant_id = r.merchant_id
 and o.order_id = b->>'order_id' and o.currency = b->>'currency'
