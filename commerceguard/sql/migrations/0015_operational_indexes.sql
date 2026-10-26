-- Я индексирую реальные merchant/source/time и queue predicates, не меняя бизнес-факты.
CREATE INDEX ingest_batch_health_idx ON commerceguard.ingest_batch(merchant_id,source,published_at DESC,batch_id DESC) WHERE state='published';
CREATE INDEX ingest_attempt_merchant_latest_idx ON commerceguard.ingest_attempt(merchant_id,source,started_at DESC,attempt_id DESC);
CREATE INDEX ingest_attempt_merchant_success_idx ON commerceguard.ingest_attempt(merchant_id,source,finished_at DESC,attempt_id DESC) WHERE state IN ('published','duplicate');
CREATE INDEX settlement_advice_health_idx ON commerceguard.core_settlement_advice(merchant_id,published_at DESC,advice_id DESC);
CREATE INDEX case_last_close_idx ON commerceguard.ops_case_human_event(case_key,workflow_version DESC) INCLUDE(observed_revision) WHERE action='close';
