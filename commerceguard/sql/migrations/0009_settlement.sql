-- Я добавляю immutable выписку, ревизии membership и отдельный результат сверки.
CREATE TABLE commerceguard.core_settlement_advice (
    advice_id uuid PRIMARY KEY,
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    settlement_id text NOT NULL CHECK (settlement_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    revision integer NOT NULL CHECK (revision BETWEEN 1 AND 1000000),
    currency text NOT NULL CHECK (currency IN ('RUB', 'USD', 'EUR')),
    period_start timestamptz NOT NULL CHECK (isfinite(period_start)),
    period_end timestamptz NOT NULL CHECK (isfinite(period_end)),
    observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
    is_complete boolean NOT NULL,
    expected_event_count integer NOT NULL CHECK (expected_event_count BETWEEN 0 AND 10000),
    member_count integer NOT NULL CHECK (member_count BETWEEN 0 AND expected_event_count),
    canonical_sha256 text NOT NULL UNIQUE CHECK (canonical_sha256 ~ '^[a-f0-9]{64}$'),
    canonical_text text NOT NULL CHECK (octet_length(canonical_text) <= 1048576),
    canonical_json jsonb NOT NULL CHECK (jsonb_typeof(canonical_json) = 'object'),
    raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[a-f0-9]{64}$'),
    raw_object_key text NOT NULL CHECK (raw_object_key ~ '^objects/[a-f0-9]{2}/[a-f0-9]{64}$'),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK (isfinite(published_at)),
    UNIQUE (merchant_id, settlement_id, revision),
    UNIQUE (advice_id, merchant_id, settlement_id),
    UNIQUE (advice_id, merchant_id),
    CHECK (period_start < period_end AND observed_at >= period_start),
    CHECK (NOT is_complete OR observed_at >= period_end)
);
-- Я резервирую event за business batch, но допускаю новые ревизии того же batch.
-- Ссылки на отсутствующий PSP fact допустимы: это намерение выписки, не нулевой факт.
CREATE TABLE commerceguard.core_settlement_event_assignment (
    merchant_id text NOT NULL,
    source_event_id text NOT NULL CHECK (source_event_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    settlement_id text NOT NULL,
    first_advice_id uuid NOT NULL,
    PRIMARY KEY (merchant_id, source_event_id),
    UNIQUE (merchant_id, source_event_id, settlement_id),
    FOREIGN KEY (first_advice_id, merchant_id, settlement_id)
        REFERENCES commerceguard.core_settlement_advice(advice_id, merchant_id, settlement_id)
);
CREATE TABLE commerceguard.core_settlement_member (
    advice_id uuid NOT NULL,
    merchant_id text NOT NULL,
    settlement_id text NOT NULL,
    source_event_id text NOT NULL,
    PRIMARY KEY (advice_id, source_event_id),
    FOREIGN KEY (advice_id, merchant_id, settlement_id)
        REFERENCES commerceguard.core_settlement_advice(advice_id, merchant_id, settlement_id),
    FOREIGN KEY (merchant_id, source_event_id, settlement_id)
        REFERENCES commerceguard.core_settlement_event_assignment(merchant_id, source_event_id, settlement_id)
);
CREATE TABLE commerceguard.ops_settlement_result (
    report_id uuid PRIMARY KEY,
    advice_id uuid NOT NULL,
    merchant_id text NOT NULL,
    as_of timestamptz NOT NULL CHECK (isfinite(as_of)),
    fee_bps integer NOT NULL CHECK (fee_bps BETWEEN 0 AND 10000),
    engine_sha256 text NOT NULL CHECK (engine_sha256 ~ '^[a-f0-9]{64}$'),
    request_key text NOT NULL UNIQUE CHECK (request_key ~ '^[a-f0-9]{64}$'),
    request_text text NOT NULL,
    request_json jsonb NOT NULL CHECK (jsonb_typeof(request_json) = 'object'),
    result_sha256 text NOT NULL CHECK (result_sha256 ~ '^[a-f0-9]{64}$'),
    payload_text text NOT NULL CHECK (octet_length(payload_text) <= 16777216),
    payload_json jsonb NOT NULL CHECK (jsonb_typeof(payload_json) = 'object'),
    state text NOT NULL CHECK (state IN ('matched', 'discrepancy', 'unknown')),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK (isfinite(published_at)),
    FOREIGN KEY (advice_id, merchant_id) REFERENCES commerceguard.core_settlement_advice(advice_id, merchant_id),
    CHECK (COALESCE(payload_json->>'state' = state, false))
);
CREATE INDEX ops_settlement_result_advice_time_idx
    ON commerceguard.ops_settlement_result (advice_id, as_of DESC, report_id);
CREATE TRIGGER core_settlement_advice_immutable BEFORE UPDATE OR DELETE ON commerceguard.core_settlement_advice
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER core_settlement_assignment_immutable BEFORE UPDATE OR DELETE ON commerceguard.core_settlement_event_assignment
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER core_settlement_member_immutable BEFORE UPDATE OR DELETE ON commerceguard.core_settlement_member
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER ops_settlement_result_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_settlement_result
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
