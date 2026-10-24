-- Я фиксирую входы отдельно от будущих попыток выполнения и результатов сверки.
CREATE TABLE commerceguard.ops_run_manifest (
    run_id uuid PRIMARY KEY,
    run_key text NOT NULL UNIQUE CHECK (run_key ~ '^[a-f0-9]{64}$'),
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    mode text NOT NULL CHECK (mode = 'as-was'),
    as_of timestamptz NOT NULL CHECK (isfinite(as_of)),
    knowledge_at timestamptz NOT NULL CHECK (isfinite(knowledge_at)),
    ruleset_version text NOT NULL CHECK (ruleset_version = 'balance-v1'),
    engine_sha256 text NOT NULL CHECK (engine_sha256 ~ '^[a-f0-9]{64}$'),
    input_count integer NOT NULL CHECK (input_count BETWEEN 2 AND 10001),
    manifest_text text NOT NULL CHECK (octet_length(manifest_text) BETWEEN 1 AND 5000000),
    manifest_json jsonb NOT NULL CHECK (jsonb_typeof(manifest_json) = 'object'),
    prepared_at timestamptz NOT NULL DEFAULT transaction_timestamp() CHECK (isfinite(prepared_at)),
    UNIQUE (run_id, merchant_id),
    CHECK (knowledge_at = as_of)
);
CREATE INDEX ops_run_manifest_merchant_idx
    ON commerceguard.ops_run_manifest (merchant_id, as_of DESC, prepared_at DESC);

CREATE TABLE commerceguard.ops_run_input (
    run_id uuid NOT NULL,
    merchant_id text NOT NULL,
    ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 10001),
    source text NOT NULL CHECK (source IN ('oms', 'psp')),
    batch_id uuid NOT NULL,
    snapshot_id uuid,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[a-f0-9]{64}$'),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    PRIMARY KEY (run_id, ordinal),
    UNIQUE (run_id, batch_id),
    FOREIGN KEY (run_id, merchant_id)
        REFERENCES commerceguard.ops_run_manifest(run_id, merchant_id),
    FOREIGN KEY (batch_id, merchant_id, source)
        REFERENCES commerceguard.ingest_batch(batch_id, merchant_id, source),
    FOREIGN KEY (snapshot_id, batch_id, merchant_id)
        REFERENCES commerceguard.core_oms_snapshot(snapshot_id, batch_id, merchant_id),
    CHECK ((source = 'oms') = (snapshot_id IS NOT NULL))
);
CREATE UNIQUE INDEX ops_run_one_oms_idx
    ON commerceguard.ops_run_input (run_id) WHERE source = 'oms';

CREATE TRIGGER ops_run_manifest_immutable
    BEFORE UPDATE OR DELETE ON commerceguard.ops_run_manifest
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER ops_run_input_immutable
    BEFORE UPDATE OR DELETE ON commerceguard.ops_run_input
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
