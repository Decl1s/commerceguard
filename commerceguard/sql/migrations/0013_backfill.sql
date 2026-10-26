-- Я храню неизменяемый план и точные run IDs, состояние выполнения веду отдельно.
CREATE TABLE commerceguard.ops_backfill_job (
    job_id text PRIMARY KEY CHECK (job_id ~ '^[a-f0-9]{64}$'),
    plan_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE commerceguard.ops_backfill_item (
    job_id text NOT NULL REFERENCES commerceguard.ops_backfill_job(job_id),
    business_date date NOT NULL,
    run_id uuid NOT NULL REFERENCES commerceguard.ops_run_manifest(run_id),
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','failed','published')),
    result_sha256 text,
    error_code text,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 100),
    PRIMARY KEY(job_id,business_date),
    CHECK ((state='published')=(result_sha256 IS NOT NULL)),
    CHECK ((state='failed')=(error_code IS NOT NULL))
);
CREATE TRIGGER ops_backfill_job_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_backfill_job
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE FUNCTION commerceguard.guard_backfill_item() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF TG_OP='DELETE' OR (OLD.job_id,OLD.business_date,OLD.run_id) IS DISTINCT FROM (NEW.job_id,NEW.business_date,NEW.run_id)
       OR OLD.state='published' OR NEW.attempts<>OLD.attempts+1 THEN
        RAISE EXCEPTION USING ERRCODE='55000',MESSAGE='Invalid backfill item transition';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER ops_backfill_item_guard BEFORE UPDATE OR DELETE ON commerceguard.ops_backfill_item
    FOR EACH ROW EXECUTE FUNCTION commerceguard.guard_backfill_item();
