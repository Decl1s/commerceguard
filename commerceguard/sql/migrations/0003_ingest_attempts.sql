-- Я отделяю попытку от опубликованного batch: откат core не уничтожает диагноз.
-- Прежние миграции сохраняю побайтно; SQL пока не применял.
CREATE TABLE commerceguard.ingest_attempt (
    attempt_id uuid PRIMARY KEY,
    batch_id uuid NOT NULL,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[a-f0-9]{64}$'),
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    source text NOT NULL CHECK (source IN ('oms', 'psp')),
    raw_object_key text NOT NULL CHECK (raw_object_key ~ '^objects/[a-f0-9]{2}/[a-f0-9]{64}$'),
    manifest_object_key text NOT NULL
        CHECK (manifest_object_key ~ '^manifests/[a-f0-9]{2}/[a-f0-9]{64}\.json$'),
    state text NOT NULL CHECK (state IN ('started', 'published', 'duplicate', 'quarantined', 'failed', 'unknown')),
    category text CHECK (category IN ('structural', 'business', 'infrastructure', 'interrupted')),
    error_code text CHECK (error_code ~ '^[A-Z][A-Z0-9_]{2,63}$'),
    error_row bigint CHECK (error_row BETWEEN 1 AND 1000001),
    error_field text CHECK (error_field ~ '^[a-z][a-z0-9_]{0,63}$'),
    started_at timestamptz NOT NULL DEFAULT transaction_timestamp() CHECK (isfinite(started_at)),
    finished_at timestamptz CHECK (isfinite(finished_at)),
    published_batch_id uuid REFERENCES commerceguard.ingest_batch(batch_id),
    CHECK ((state = 'started') = (finished_at IS NULL)),
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    CHECK ((state IN ('published', 'duplicate')) = (published_batch_id IS NOT NULL)),
    CHECK (published_batch_id IS NULL OR published_batch_id = batch_id),
    CHECK ((state IN ('quarantined', 'failed', 'unknown')) = (error_code IS NOT NULL)),
    CHECK ((error_code IS NULL) = (category IS NULL)),
    CHECK (error_code IS NOT NULL OR (error_row IS NULL AND error_field IS NULL))
);
CREATE INDEX ingest_attempt_manifest_idx
    ON commerceguard.ingest_attempt (manifest_sha256, started_at DESC, attempt_id);

CREATE FUNCTION commerceguard.guard_attempt_transition() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Attempt history cannot be deleted';
    END IF;
    IF OLD.state <> 'started' OR NEW.state = 'started' THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Only started to terminal transition is allowed';
    END IF;
    IF (OLD.attempt_id, OLD.batch_id, OLD.manifest_sha256, OLD.merchant_id, OLD.source,
        OLD.raw_object_key, OLD.manifest_object_key, OLD.started_at)
        IS DISTINCT FROM
       (NEW.attempt_id, NEW.batch_id, NEW.manifest_sha256, NEW.merchant_id, NEW.source,
        NEW.raw_object_key, NEW.manifest_object_key, NEW.started_at) THEN
        RAISE EXCEPTION USING ERRCODE = '55000', MESSAGE = 'Attempt identity is immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER ingest_attempt_transition
    BEFORE UPDATE OR DELETE ON commerceguard.ingest_attempt
    FOR EACH ROW EXECUTE FUNCTION commerceguard.guard_attempt_transition();
