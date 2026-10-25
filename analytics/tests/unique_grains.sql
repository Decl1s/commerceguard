-- Я проверяю зерно финансового JOIN, events и валютной витрины.
select 'orders' as relation_name from {{ ref('fct_order_reconciliation') }}
group by run_id, merchant_id, order_id, currency having count(*) <> 1
union all
select 'events' from {{ ref('stg_run_events') }}
group by run_id, merchant_id, source_event_id having count(*) <> 1
union all
select 'currency' from {{ ref('mart_reconciliation_currency') }}
group by run_id, merchant_id, currency having count(*) <> 1
union all
select 'findings' from {{ ref('stg_run_findings') }}
group by run_id, case_key having count(*) <> 1
