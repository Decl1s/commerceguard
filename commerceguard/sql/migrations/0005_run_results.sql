-- Я сохраняю один immutable результат на manifest и отдельную историю попыток.
ALTER TABLE commerceguard.ops_run_input ADD UNIQUE (run_id, snapshot_id);
CREATE TABLE commerceguard.ops_run_attempt (
    attempt_id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES commerceguard.ops_run_manifest(run_id),
    state text NOT NULL CHECK (state IN ('started', 'published', 'duplicate', 'failed', 'unknown')),
    error_code text CHECK (error_code ~ '^[A-Z][A-Z0-9_]{2,63}$'),
    started_at timestamptz NOT NULL DEFAULT transaction_timestamp() CHECK (isfinite(started_at)),
    finished_at timestamptz CHECK (isfinite(finished_at)),
    UNIQUE (attempt_id, run_id),
    CHECK ((state = 'started') = (finished_at IS NULL)),
    CHECK ((state IN ('failed', 'unknown')) = (error_code IS NOT NULL)),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX ops_run_attempt_run_idx ON commerceguard.ops_run_attempt (run_id, started_at DESC);
CREATE FUNCTION commerceguard.guard_run_attempt() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Run attempt history cannot be deleted';
    END IF;
    IF OLD.state <> 'started' OR NEW.state = 'started' OR
       (OLD.attempt_id, OLD.run_id, OLD.started_at) IS DISTINCT FROM
       (NEW.attempt_id, NEW.run_id, NEW.started_at) THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Invalid run attempt transition';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER ops_run_attempt_transition BEFORE UPDATE OR DELETE ON commerceguard.ops_run_attempt
    FOR EACH ROW EXECUTE FUNCTION commerceguard.guard_run_attempt();

CREATE TABLE commerceguard.ops_run_result (
    run_id uuid PRIMARY KEY REFERENCES commerceguard.ops_run_manifest(run_id),
    attempt_id uuid NOT NULL UNIQUE,
    merchant_id text NOT NULL,
    oms_snapshot_id uuid NOT NULL,
    result_version integer NOT NULL CHECK (result_version = 1),
    result_sha256 text NOT NULL CHECK (result_sha256 ~ '^[a-f0-9]{64}$'),
    executor_sha256 text NOT NULL CHECK (executor_sha256 ~ '^[a-f0-9]{64}$'),
    payload_text text NOT NULL CHECK (octet_length(payload_text) BETWEEN 1 AND 16777216),
    payload_json jsonb NOT NULL CHECK (jsonb_typeof(payload_json) = 'object'),
    balance_count integer NOT NULL CHECK (balance_count BETWEEN 0 AND 10000),
    finding_count integer NOT NULL CHECK (finding_count BETWEEN 0 AND 100000),
    evidence_count integer NOT NULL CHECK (evidence_count BETWEEN 0 AND 50000),
    published_at timestamptz NOT NULL DEFAULT transaction_timestamp() CHECK (isfinite(published_at)),
    FOREIGN KEY (attempt_id, run_id) REFERENCES commerceguard.ops_run_attempt(attempt_id, run_id),
    FOREIGN KEY (run_id, merchant_id) REFERENCES commerceguard.ops_run_manifest(run_id, merchant_id),
    FOREIGN KEY (run_id, oms_snapshot_id) REFERENCES commerceguard.ops_run_input(run_id, snapshot_id)
);
CREATE TABLE commerceguard.ops_run_evidence (
    run_id uuid NOT NULL REFERENCES commerceguard.ops_run_result(run_id),
    merchant_id text NOT NULL,
    source_event_id text NOT NULL,
    batch_id uuid NOT NULL,
    raw_row_number bigint NOT NULL,
    record_sha256 text NOT NULL CHECK (record_sha256 ~ '^[a-f0-9]{64}$'),
    PRIMARY KEY (run_id, batch_id, raw_row_number),
    FOREIGN KEY (run_id, batch_id) REFERENCES commerceguard.ops_run_input(run_id, batch_id),
    FOREIGN KEY (batch_id, raw_row_number)
        REFERENCES commerceguard.core_payment_receipt(batch_id, raw_row_number),
    FOREIGN KEY (batch_id, raw_row_number)
        REFERENCES commerceguard.ingest_raw_record(batch_id, row_number),
    FOREIGN KEY (merchant_id, source_event_id)
        REFERENCES commerceguard.core_payment_event(merchant_id, source_event_id)
);
CREATE INDEX ops_run_evidence_event_idx
    ON commerceguard.ops_run_evidence (run_id, merchant_id, source_event_id);
CREATE TRIGGER ops_run_result_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_run_result
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER ops_run_evidence_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_run_evidence
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
