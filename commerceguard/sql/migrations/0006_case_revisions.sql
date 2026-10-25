-- Я применяю результат явно; ledger и карточки фиксирую одним COMMIT.
ALTER TABLE commerceguard.ops_run_result ADD UNIQUE (run_id, merchant_id);
CREATE TABLE commerceguard.ops_case_application (
    run_id uuid PRIMARY KEY,
    merchant_id text NOT NULL,
    generation bigint NOT NULL CHECK (generation > 0),
    previous_run_id uuid,
    policy text NOT NULL CHECK (policy = 'canonical-as-was-v1'),
    projector_sha256 text NOT NULL CHECK (projector_sha256 ~ '^[a-f0-9]{64}$'),
    revision_count integer NOT NULL CHECK (revision_count BETWEEN 0 AND 10000),
    case_count integer NOT NULL CHECK (case_count BETWEEN 0 AND 10000),
    applied_at timestamptz NOT NULL DEFAULT transaction_timestamp() CHECK (isfinite(applied_at)),
    UNIQUE (merchant_id, generation),
    UNIQUE (run_id, merchant_id),
    UNIQUE (run_id, merchant_id, generation),
    CHECK ((generation = 1) = (previous_run_id IS NULL)),
    FOREIGN KEY (run_id, merchant_id) REFERENCES commerceguard.ops_run_result(run_id, merchant_id),
    FOREIGN KEY (previous_run_id, merchant_id)
        REFERENCES commerceguard.ops_case_application(run_id, merchant_id)
);
CREATE TABLE commerceguard.ops_case_stream (
    merchant_id text PRIMARY KEY,
    current_run_id uuid NOT NULL,
    generation bigint NOT NULL,
    FOREIGN KEY (current_run_id, merchant_id, generation)
        REFERENCES commerceguard.ops_case_application(run_id, merchant_id, generation)
);
CREATE TABLE commerceguard.ops_case (
    case_key text PRIMARY KEY CHECK (case_key ~ '^[a-f0-9]{64}$'),
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    order_id text NOT NULL CHECK (order_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    currency text NOT NULL CHECK (currency IN ('RUB', 'USD', 'EUR')),
    rule_code text NOT NULL CHECK (rule_code IN ('payment_shortfall', 'payment_excess',
        'refund_missing', 'refund_excess', 'currency_mismatch', 'orphan_payment')),
    finding_state text NOT NULL CHECK (finding_state IN ('present', 'absent')),
    workflow_status text NOT NULL DEFAULT 'open' CHECK (workflow_status = 'open'),
    first_run_id uuid NOT NULL,
    last_seen_run_id uuid NOT NULL,
    evaluated_run_id uuid NOT NULL,
    revision_number bigint NOT NULL CHECK (revision_number > 0),
    UNIQUE (case_key, merchant_id),
    FOREIGN KEY (first_run_id, merchant_id) REFERENCES commerceguard.ops_case_application(run_id, merchant_id),
    FOREIGN KEY (last_seen_run_id, merchant_id) REFERENCES commerceguard.ops_case_application(run_id, merchant_id),
    FOREIGN KEY (evaluated_run_id, merchant_id) REFERENCES commerceguard.ops_case_application(run_id, merchant_id)
);
CREATE INDEX ops_case_merchant_state_idx ON commerceguard.ops_case (merchant_id, finding_state, case_key);
CREATE TABLE commerceguard.ops_case_revision (
    case_key text NOT NULL,
    merchant_id text NOT NULL,
    revision_number bigint NOT NULL CHECK (revision_number > 0),
    run_id uuid NOT NULL,
    finding_state text NOT NULL CHECK (finding_state IN ('present', 'absent')),
    finding_sha256 text CHECK (finding_sha256 ~ '^[a-f0-9]{64}$'),
    finding_json jsonb CHECK (jsonb_typeof(finding_json) = 'object'),
    PRIMARY KEY (case_key, revision_number),
    UNIQUE (case_key, revision_number, finding_state),
    UNIQUE (case_key, run_id),
    FOREIGN KEY (case_key, merchant_id) REFERENCES commerceguard.ops_case(case_key, merchant_id),
    FOREIGN KEY (run_id, merchant_id) REFERENCES commerceguard.ops_case_application(run_id, merchant_id),
    CHECK ((finding_state = 'present' AND finding_sha256 IS NOT NULL AND finding_json IS NOT NULL)
        OR (finding_state = 'absent' AND finding_sha256 IS NULL AND finding_json IS NULL))
);
ALTER TABLE commerceguard.ops_case ADD FOREIGN KEY (case_key, revision_number, finding_state)
    REFERENCES commerceguard.ops_case_revision(case_key, revision_number, finding_state) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE commerceguard.ops_case_event (
    case_key text NOT NULL,
    revision_number bigint NOT NULL,
    event_kind text NOT NULL CHECK (event_kind IN ('detected', 'changed', 'absent', 'reappeared')),
    actor_kind text NOT NULL DEFAULT 'system' CHECK (actor_kind = 'system'),
    PRIMARY KEY (case_key, revision_number),
    FOREIGN KEY (case_key, revision_number)
        REFERENCES commerceguard.ops_case_revision(case_key, revision_number)
);
CREATE FUNCTION commerceguard.guard_case_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Case history cannot be deleted';
    END IF;
    IF (OLD.case_key, OLD.merchant_id, OLD.order_id, OLD.currency, OLD.rule_code,
        OLD.first_run_id, OLD.workflow_status) IS DISTINCT FROM
       (NEW.case_key, NEW.merchant_id, NEW.order_id, NEW.currency, NEW.rule_code,
        NEW.first_run_id, NEW.workflow_status) OR NEW.revision_number < OLD.revision_number THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Invalid case identity transition';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER ops_case_identity BEFORE UPDATE OR DELETE ON commerceguard.ops_case
    FOR EACH ROW EXECUTE FUNCTION commerceguard.guard_case_identity();
CREATE TRIGGER ops_case_application_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_case_application
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER ops_case_revision_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_case_revision
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER ops_case_event_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_case_event
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
