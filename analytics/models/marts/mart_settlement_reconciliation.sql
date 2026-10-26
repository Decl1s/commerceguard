-- Зерно: report_id, то есть конкретная выписка/ревизия/cutoff/тариф/engine.
-- Я не выбираю latest и не складываю ревизии одного business batch.
select r.report_id, r.advice_id, r.merchant_id, a.settlement_id, a.revision, a.currency,
       a.period_start, a.period_end, r.as_of, r.fee_bps, r.engine_sha256, r.result_sha256,
       r.state, r.published_at, a.raw_sha256 as advice_raw_sha256,
       a.raw_object_key as advice_raw_object_key,
       (r.payload_json->'reported'->>'gross')::bigint as reported_gross_minor,
       (r.payload_json->'reported'->>'refund')::bigint as reported_refund_minor,
       (r.payload_json->'reported'->>'fee')::bigint as reported_fee_minor,
       (r.payload_json->'reported'->>'net')::bigint as reported_net_minor,
       (r.payload_json->'expected'->>'gross')::bigint as expected_gross_minor,
       (r.payload_json->'expected'->>'refund')::bigint as expected_refund_minor,
       (r.payload_json->'expected'->>'fee')::bigint as expected_fee_minor,
       (r.payload_json->'expected'->>'net')::bigint as expected_net_minor,
       r.payload_json->'completeness'->'reason_codes' as unknown_reasons,
       (r.payload_json->'completeness'->>'expected_event_count')::integer as expected_event_count,
       (r.payload_json->'completeness'->>'member_count')::integer as member_count,
       (r.payload_json->'completeness'->>'visible_event_count')::integer as visible_event_count,
       r.payload_json->'discrepancies' as discrepancies
from {{ source('commerceguard', 'ops_settlement_result') }} r
join {{ source('commerceguard', 'core_settlement_advice') }} a using (advice_id, merchant_id)
