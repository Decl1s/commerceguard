-- Я сохраняю orphan/currency findings, даже когда у валюты нет OMS balance.
select r.run_id, r.merchant_id, f->>'case_key' as case_key,
       f->>'order_id' as order_id, f->>'currency' as currency, f->>'rule' as rule,
       (f->>'expected_minor')::bigint as expected_minor,
       (f->>'actual_minor')::bigint as actual_minor,
       (f->>'delta_minor')::bigint as delta_minor
from {{ ref('stg_completed_runs') }} r
cross join lateral jsonb_array_elements(r.payload_json->'findings') f
