-- Я расширяю формат ожиданий, не обновляя суммы, raw и опубликованные результаты.
ALTER TABLE commerceguard.ingest_batch DROP CONSTRAINT ingest_batch_contract_version_check;
ALTER TABLE commerceguard.ingest_batch
    ADD CONSTRAINT ingest_batch_contract_v2 CHECK (
        (source = 'oms' AND contract_version IN (1, 2)) OR (source = 'psp' AND contract_version = 1)),
    ADD UNIQUE (batch_id, merchant_id, contract_version);
ALTER TABLE commerceguard.core_order_expectation
    ADD COLUMN expectation_version integer NOT NULL DEFAULT 1 CHECK (expectation_version IN (1, 2)),
    ADD COLUMN capture_due_at timestamptz,
    ADD COLUMN refund_due_at timestamptz,
    ADD CONSTRAINT core_order_deadlines_v2 CHECK (
        (expectation_version = 1 AND capture_due_at IS NULL AND refund_due_at IS NULL)
        OR (expectation_version = 2 AND capture_due_at IS NOT NULL AND refund_due_at IS NOT NULL
            AND isfinite(capture_due_at) AND isfinite(refund_due_at)
            AND settle_after = greatest(capture_due_at, refund_due_at))),
    ADD FOREIGN KEY (batch_id, merchant_id, expectation_version)
        REFERENCES commerceguard.ingest_batch(batch_id, merchant_id, contract_version);
ALTER TABLE commerceguard.ops_run_input
    ADD COLUMN contract_version integer CHECK (contract_version IN (1, 2)),
    ADD FOREIGN KEY (batch_id, merchant_id, contract_version)
        REFERENCES commerceguard.ingest_batch(batch_id, merchant_id, contract_version);
ALTER TABLE commerceguard.ops_run_manifest DROP CONSTRAINT ops_run_manifest_ruleset_version_check;
ALTER TABLE commerceguard.ops_run_manifest
    ADD CONSTRAINT ops_run_manifest_ruleset_v2 CHECK (ruleset_version IN ('balance-v1', 'balance-v2')),
    ADD CONSTRAINT ops_run_deadline_contract_v3 CHECK (COALESCE(
        (manifest_json->>'manifest_version' = '3' AND ruleset_version = 'balance-v2'
         AND manifest_json->>'deadline_version' = 'per-leg-v2')
        OR (manifest_json->>'manifest_version' IN ('1', '2') AND ruleset_version = 'balance-v1'), false));
ALTER TABLE commerceguard.ops_run_manifest DROP CONSTRAINT ops_run_manifest_request_v2;
ALTER TABLE commerceguard.ops_run_manifest
    ADD CONSTRAINT ops_run_manifest_request_v3 CHECK (COALESCE(
        (manifest_json->>'manifest_version' = '1' AND mode = 'as-was'
         AND reason_code IS NULL AND baseline_run_id IS NULL)
        OR (manifest_json->>'manifest_version' IN ('2', '3') AND reason_code IS NOT NULL
            AND ((mode = 'as-was' AND baseline_run_id IS NULL AND reason_code <> 'late-data')
                 OR (mode = 'as-known-now' AND baseline_run_id IS NOT NULL))), false));
ALTER TABLE commerceguard.ops_run_result DROP CONSTRAINT ops_run_result_version_v2;
ALTER TABLE commerceguard.ops_run_result
    ADD CONSTRAINT ops_run_result_version_v3 CHECK (result_version IN (1, 2, 3));
ALTER TABLE commerceguard.ops_case_application DROP CONSTRAINT ops_case_application_policy_check;
ALTER TABLE commerceguard.ops_case_application
    ADD CONSTRAINT ops_case_application_policy_v2 CHECK (policy IN ('canonical-as-was-v1', 'canonical-as-was-v2')),
    ADD COLUMN upgrade_from_run_id uuid,
    ADD FOREIGN KEY (upgrade_from_run_id, merchant_id)
        REFERENCES commerceguard.ops_case_application(run_id, merchant_id),
    ADD CONSTRAINT ops_case_upgrade_predecessor CHECK (
        upgrade_from_run_id IS NULL OR (previous_run_id IS NOT NULL AND upgrade_from_run_id = previous_run_id
                                       AND policy = 'canonical-as-was-v2'));
