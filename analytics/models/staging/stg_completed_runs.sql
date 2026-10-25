-- Я включаю только сохранённые результаты известных версий, не prepared attempts.
select m.run_id, m.merchant_id, m.mode, m.as_of, m.knowledge_at,
       m.ruleset_version, m.engine_sha256, r.result_version, r.result_sha256,
       r.oms_snapshot_id, r.balance_count, r.finding_count, r.published_at,
       r.payload_json
from {{ source('commerceguard', 'ops_run_manifest') }} m
join {{ source('commerceguard', 'ops_run_result') }} r using (run_id, merchant_id)
where r.result_version in (1, 2, 3)
  and m.ruleset_version in ('balance-v1', 'balance-v2')
