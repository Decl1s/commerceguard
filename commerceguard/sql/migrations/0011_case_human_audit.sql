-- Я добавляю человеческую версию к существующей карточке, финансовую revision сохраняю отдельно.
ALTER TABLE commerceguard.ops_case
    ADD COLUMN workflow_version bigint NOT NULL DEFAULT 0 CHECK (workflow_version>=0),
    ADD COLUMN assignee text REFERENCES commerceguard.web_user(username);
CREATE TABLE commerceguard.ops_case_human_event (
    case_key text NOT NULL REFERENCES commerceguard.ops_case(case_key),
    workflow_version bigint NOT NULL CHECK (workflow_version>0),
    actor text NOT NULL REFERENCES commerceguard.web_user(username),
    request_id uuid NOT NULL,
    command_sha256 text NOT NULL CHECK (command_sha256 ~ '^[a-f0-9]{64}$'),
    command_json jsonb NOT NULL CHECK (jsonb_typeof(command_json)='object' AND octet_length(command_json::text)<=24000),
    action text NOT NULL CHECK (action IN ('assign','comment')),
    before_json jsonb NOT NULL CHECK (jsonb_typeof(before_json)='object'),
    after_json jsonb NOT NULL CHECK (jsonb_typeof(after_json)='object'),
    observed_revision bigint NOT NULL,
    observed_run_id uuid NOT NULL REFERENCES commerceguard.ops_case_application(run_id),
    finding_state text NOT NULL CHECK (finding_state IN ('present','absent')),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (case_key,workflow_version),
    UNIQUE (actor,request_id)
);
CREATE TRIGGER ops_case_human_event_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_case_human_event
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE FUNCTION commerceguard.guard_human_workflow() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF (OLD.workflow_version,OLD.assignee,OLD.workflow_status) IS DISTINCT FROM
       (NEW.workflow_version,NEW.assignee,NEW.workflow_status) THEN
        IF NEW.workflow_version<>OLD.workflow_version+1 OR NOT EXISTS (
            SELECT 1 FROM commerceguard.ops_case_human_event e
            WHERE e.case_key=NEW.case_key AND e.workflow_version=NEW.workflow_version
              AND e.before_json=jsonb_build_object('version',OLD.workflow_version,'assignee',OLD.assignee,'status',OLD.workflow_status)
              AND e.after_json=jsonb_build_object('version',NEW.workflow_version,'assignee',NEW.assignee,'status',NEW.workflow_status)
              AND e.observed_revision=NEW.revision_number AND e.observed_run_id=NEW.evaluated_run_id
              AND e.finding_state=NEW.finding_state
        ) THEN
            RAISE EXCEPTION USING ERRCODE='55000', MESSAGE='Workflow update requires matching audit';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE CONSTRAINT TRIGGER ops_case_workflow_audit AFTER UPDATE ON commerceguard.ops_case
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION commerceguard.guard_human_workflow();
