-- Я расширяю контракт времени, не обновляя immutable строки прежних run.
ALTER TABLE commerceguard.ops_run_manifest DROP CONSTRAINT ops_run_manifest_mode_check;
ALTER TABLE commerceguard.ops_run_manifest DROP CONSTRAINT ops_run_manifest_check;
ALTER TABLE commerceguard.ops_run_manifest
    ADD CONSTRAINT ops_run_manifest_mode_v2 CHECK (mode IN ('as-was', 'as-known-now')),
    ADD CONSTRAINT ops_run_manifest_time_v2 CHECK (
        (mode = 'as-was' AND knowledge_at = as_of)
        OR (mode = 'as-known-now' AND knowledge_at >= as_of)),
    ADD COLUMN reason_code text CHECK (reason_code IN ('manual', 'scheduled', 'late-data', 'recovery')),
    ADD COLUMN baseline_run_id uuid,
    ADD FOREIGN KEY (baseline_run_id, merchant_id)
        REFERENCES commerceguard.ops_run_result(run_id, merchant_id),
    ADD CONSTRAINT ops_run_manifest_request_v2 CHECK (COALESCE(
        (manifest_json->>'manifest_version' = '1' AND mode = 'as-was'
         AND reason_code IS NULL AND baseline_run_id IS NULL)
        OR (manifest_json->>'manifest_version' = '2' AND reason_code IS NOT NULL
            AND ((mode = 'as-was' AND baseline_run_id IS NULL AND reason_code <> 'late-data')
                 OR (mode = 'as-known-now' AND baseline_run_id IS NOT NULL))), false));
ALTER TABLE commerceguard.ops_run_result DROP CONSTRAINT ops_run_result_result_version_check;
ALTER TABLE commerceguard.ops_run_result
    ADD CONSTRAINT ops_run_result_version_v2 CHECK (result_version IN (1, 2));
CREATE INDEX ops_run_manifest_baseline_idx ON commerceguard.ops_run_manifest (baseline_run_id)
    WHERE baseline_run_id IS NOT NULL;
