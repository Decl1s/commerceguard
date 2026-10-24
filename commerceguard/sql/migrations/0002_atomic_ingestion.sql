-- CG-103. Старый 0001 не редактируется: checksum остаётся частью истории.
-- До этого среза ingestion не существовал. Не угадываем отсутствующий envelope
-- для вручную вставленных legacy-пакетов и не удаляем их ради миграции.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM commerceguard.ingest_batch) THEN
        RAISE EXCEPTION USING ERRCODE = '55000',
            MESSAGE = 'CG-103 requires empty legacy ingest_batch; manual migration required';
    END IF;
END;
$$;

ALTER TABLE commerceguard.ingest_batch
    DROP CONSTRAINT ingest_batch_merchant_id_source_content_sha256_key,
    ADD COLUMN manifest_sha256 text NOT NULL UNIQUE CHECK (manifest_sha256 ~ '^[a-f0-9]{64}$'),
    ADD COLUMN manifest_json jsonb NOT NULL CHECK (jsonb_typeof(manifest_json) = 'object'),
    ADD COLUMN raw_object_key text NOT NULL
        CHECK (raw_object_key ~ '^objects/[a-f0-9]{2}/[a-f0-9]{64}$'),
    ADD COLUMN manifest_object_key text NOT NULL
        CHECK (manifest_object_key ~ '^manifests/[a-f0-9]{2}/[a-f0-9]{64}\.json$'),
    ADD COLUMN parsed_row_count bigint NOT NULL DEFAULT 0
        CHECK (parsed_row_count BETWEEN 0 AND declared_row_count),
    ADD COLUMN new_fact_count bigint NOT NULL DEFAULT 0
        CHECK (new_fact_count BETWEEN 0 AND parsed_row_count),
    ADD COLUMN known_event_count bigint NOT NULL DEFAULT 0
        CHECK (known_event_count BETWEEN 0 AND parsed_row_count),
    ADD COLUMN duplicate_rows bigint NOT NULL DEFAULT 0
        CHECK (duplicate_rows BETWEEN 0 AND parsed_row_count),
    ADD CONSTRAINT ingest_batch_published_counts CHECK (
        state <> 'published' OR (
            parsed_row_count = declared_row_count AND
            new_fact_count + known_event_count + duplicate_rows = declared_row_count
        )
    );

-- Каждый факт один, но подтверждений его поступления может быть много.
CREATE TABLE commerceguard.core_payment_receipt (
    merchant_id text NOT NULL,
    source_event_id text NOT NULL,
    batch_id uuid NOT NULL,
    raw_row_number bigint NOT NULL,
    source text NOT NULL DEFAULT 'psp' CHECK (source = 'psp'),
    observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
    PRIMARY KEY (batch_id, raw_row_number),
    FOREIGN KEY (merchant_id, source_event_id)
        REFERENCES commerceguard.core_payment_event(merchant_id, source_event_id),
    FOREIGN KEY (batch_id, raw_row_number)
        REFERENCES commerceguard.ingest_raw_record(batch_id, row_number),
    FOREIGN KEY (batch_id, merchant_id, source)
        REFERENCES commerceguard.ingest_batch(batch_id, merchant_id, source)
);
CREATE INDEX core_payment_receipt_event_idx
    ON commerceguard.core_payment_receipt (merchant_id, source_event_id);
CREATE TRIGGER core_payment_receipt_immutable
    BEFORE UPDATE OR DELETE ON commerceguard.core_payment_receipt
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
