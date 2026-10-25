-- Потерянный OMS JOIN или усечение JSON не должны выглядеть полной витриной.
select r.run_id from {{ ref('stg_completed_runs') }} r
left join (select run_id, count(*) n from {{ ref('stg_run_balances') }} group by run_id) b using (run_id)
left join (select run_id, count(*) n from {{ ref('stg_run_findings') }} group by run_id) f using (run_id)
where coalesce(b.n, 0) <> r.balance_count or coalesce(f.n, 0) <> r.finding_count
