-- Я разрешаю только явные human transitions. System presence остаётся независимым.
ALTER TABLE commerceguard.ops_case DROP CONSTRAINT ops_case_workflow_status_check;
ALTER TABLE commerceguard.ops_case ADD CHECK (workflow_status IN ('open','closed'));
ALTER TABLE commerceguard.ops_case_human_event DROP CONSTRAINT ops_case_human_event_action_check;
ALTER TABLE commerceguard.ops_case_human_event ADD CHECK (action IN ('assign','comment','close','reopen'));
CREATE OR REPLACE FUNCTION commerceguard.guard_case_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        RAISE EXCEPTION USING ERRCODE='55000', MESSAGE='Case history cannot be deleted';
    END IF;
    IF (OLD.case_key,OLD.merchant_id,OLD.order_id,OLD.currency,OLD.rule_code,OLD.first_run_id)
       IS DISTINCT FROM
       (NEW.case_key,NEW.merchant_id,NEW.order_id,NEW.currency,NEW.rule_code,NEW.first_run_id)
       OR NEW.revision_number<OLD.revision_number THEN
        RAISE EXCEPTION USING ERRCODE='55000', MESSAGE='Invalid case identity transition';
    END IF;
    RETURN NEW;
END;
$$;
-- Я расширяю audit guard переходами, обязательной причиной и проверкой роли на момент записи.
CREATE OR REPLACE FUNCTION commerceguard.guard_human_workflow() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ev commerceguard.ops_case_human_event;
BEGIN
    IF (OLD.workflow_version,OLD.assignee,OLD.workflow_status) IS DISTINCT FROM
       (NEW.workflow_version,NEW.assignee,NEW.workflow_status) THEN
        SELECT * INTO ev FROM commerceguard.ops_case_human_event
            WHERE case_key=NEW.case_key AND workflow_version=NEW.workflow_version;
        IF NOT FOUND OR NEW.workflow_version<>OLD.workflow_version+1
           OR ev.before_json<>jsonb_build_object('version',OLD.workflow_version,'assignee',OLD.assignee,'status',OLD.workflow_status)
           OR ev.after_json<>jsonb_build_object('version',NEW.workflow_version,'assignee',NEW.assignee,'status',NEW.workflow_status)
           OR ev.observed_revision<>NEW.revision_number OR ev.observed_run_id<>NEW.evaluated_run_id
           OR ev.finding_state<>NEW.finding_state THEN
            RAISE EXCEPTION USING ERRCODE='55000', MESSAGE='Workflow update requires matching audit';
        END IF;
        IF OLD.workflow_status IS DISTINCT FROM NEW.workflow_status THEN
            IF NOT ((ev.action='close' AND OLD.workflow_status='open' AND NEW.workflow_status='closed')
                 OR (ev.action='reopen' AND OLD.workflow_status='closed' AND NEW.workflow_status='open'))
                 OR NOT EXISTS (SELECT 1 FROM commerceguard.web_user WHERE username=ev.actor AND role='manager' AND active)
                 OR COALESCE(ev.command_json->>'reason_code','') NOT IN
                   ('source_corrected','confirmed_external','accepted_difference','duplicate_investigation','new_evidence','decision_revised')
                 OR length(btrim(COALESCE(ev.command_json->>'value','')))=0 THEN
                RAISE EXCEPTION USING ERRCODE='55000', MESSAGE='Decision requires manager and reason';
            END IF;
        ELSIF ev.action IN ('close','reopen') THEN
            RAISE EXCEPTION USING ERRCODE='55000', MESSAGE='Decision requires state transition';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE INDEX ops_case_workflow_queue_idx ON commerceguard.ops_case(merchant_id,workflow_status,currency,case_key);
