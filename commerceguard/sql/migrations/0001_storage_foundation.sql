-- CG-101: минимальное хранилище приёма. Все объекты только в commerceguard.
-- Контроль транзакции выполняет Python; здесь нет COMMIT, DROP или reset.
-- ingest/core — логические слои, отражённые префиксами таблиц одной схемы.

CREATE TABLE commerceguard.ingest_batch (
    batch_id uuid PRIMARY KEY,
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    source text NOT NULL CHECK (source IN ('oms', 'psp')),
    contract_version integer NOT NULL CHECK (contract_version = 1),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    declared_row_count bigint NOT NULL CHECK (declared_row_count BETWEEN 0 AND 1000000),
    raw_byte_count bigint NOT NULL CHECK (raw_byte_count BETWEEN 0 AND 100000000),
    state text NOT NULL CHECK (state IN ('received', 'staged', 'published', 'quarantined', 'failed')),
    received_at timestamptz NOT NULL CHECK (isfinite(received_at)),
    published_at timestamptz CHECK (isfinite(published_at)),
    UNIQUE (merchant_id, source, content_sha256),
    UNIQUE (batch_id, merchant_id, source),
    CHECK ((state = 'published') = (published_at IS NOT NULL)),
    CHECK (published_at IS NULL OR published_at >= received_at)
);

-- Оригинальные байты файла будущий загрузчик сохранит отдельно по content hash.
-- row_number — номер логической записи; record_text не печатается в журнал.
CREATE TABLE commerceguard.ingest_raw_record (
    batch_id uuid NOT NULL REFERENCES commerceguard.ingest_batch(batch_id),
    row_number bigint NOT NULL CHECK (row_number BETWEEN 1 AND 1000000),
    record_sha256 text NOT NULL CHECK (record_sha256 ~ '^[a-f0-9]{64}$'),
    record_text text NOT NULL CHECK (octet_length(record_text) <= 1000000),
    PRIMARY KEY (batch_id, row_number)
);

CREATE TABLE commerceguard.ingest_quarantine (
    batch_id uuid NOT NULL,
    row_number bigint NOT NULL,
    error_code text NOT NULL CHECK (error_code ~ '^[A-Z][A-Z0-9_]{2,63}$'),
    column_name text CHECK (column_name ~ '^[a-z][a-z0-9_]{0,63}$'),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    PRIMARY KEY (batch_id, row_number, error_code),
    FOREIGN KEY (batch_id, row_number)
        REFERENCES commerceguard.ingest_raw_record(batch_id, row_number)
);

-- В core появляется только полный снимок. Соответствие counts/статуса batch
-- обеспечивает будущая атомарная публикация CG-103; один FK этого не доказывает.
CREATE TABLE commerceguard.core_oms_snapshot (
    snapshot_id uuid PRIMARY KEY,
    batch_id uuid NOT NULL UNIQUE,
    merchant_id text NOT NULL,
    source text NOT NULL DEFAULT 'oms' CHECK (source = 'oms'),
    effective_at timestamptz NOT NULL CHECK (isfinite(effective_at)),
    observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
    is_complete boolean NOT NULL CHECK (is_complete),
    UNIQUE (snapshot_id, batch_id, merchant_id),
    FOREIGN KEY (batch_id, merchant_id, source)
        REFERENCES commerceguard.ingest_batch(batch_id, merchant_id, source),
    CHECK (observed_at >= effective_at)
);

CREATE TABLE commerceguard.core_order_expectation (
    snapshot_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    merchant_id text NOT NULL,
    order_id text NOT NULL CHECK (order_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    raw_row_number bigint NOT NULL,
    currency text NOT NULL CHECK (currency IN ('RUB', 'USD', 'EUR')),
    capture_due_minor bigint NOT NULL CHECK (capture_due_minor BETWEEN 0 AND 1000000000000),
    refund_due_minor bigint NOT NULL CHECK (refund_due_minor BETWEEN 0 AND capture_due_minor),
    settle_after timestamptz NOT NULL CHECK (isfinite(settle_after)),
    PRIMARY KEY (snapshot_id, merchant_id, order_id),
    FOREIGN KEY (snapshot_id, batch_id, merchant_id)
        REFERENCES commerceguard.core_oms_snapshot(snapshot_id, batch_id, merchant_id),
    FOREIGN KEY (batch_id, raw_row_number)
        REFERENCES commerceguard.ingest_raw_record(batch_id, row_number)
);

CREATE TABLE commerceguard.core_payment_event (
    merchant_id text NOT NULL,
    source_event_id text NOT NULL CHECK (source_event_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    order_id text NOT NULL CHECK (order_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    source text NOT NULL DEFAULT 'psp' CHECK (source = 'psp'),
    batch_id uuid NOT NULL,
    raw_row_number bigint NOT NULL,
    currency text NOT NULL CHECK (currency IN ('RUB', 'USD', 'EUR')),
    kind text NOT NULL CHECK (kind IN ('capture', 'refund')),
    amount_minor bigint NOT NULL CHECK (amount_minor BETWEEN 1 AND 1000000000000),
    occurred_at timestamptz NOT NULL CHECK (isfinite(occurred_at)),
    observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
    semantic_sha256 text NOT NULL CHECK (semantic_sha256 ~ '^[a-f0-9]{64}$'),
    PRIMARY KEY (merchant_id, source_event_id),
    FOREIGN KEY (batch_id, merchant_id, source)
        REFERENCES commerceguard.ingest_batch(batch_id, merchant_id, source),
    FOREIGN KEY (batch_id, raw_row_number)
        REFERENCES commerceguard.ingest_raw_record(batch_id, row_number),
    CHECK (observed_at >= occurred_at)
    -- FK на заказ намеренно нет: orphan payment должен сохраниться для разбора.
);

-- Индексы следуют запланированным фильтрам, а не несуществующим замерам EXPLAIN.
CREATE INDEX core_oms_snapshot_selection_idx
    ON commerceguard.core_oms_snapshot (merchant_id, effective_at DESC, observed_at DESC);
CREATE INDEX core_payment_order_idx
    ON commerceguard.core_payment_event (merchant_id, order_id, observed_at);
CREATE INDEX core_payment_cutoff_idx
    ON commerceguard.core_payment_event (merchant_id, observed_at, occurred_at);

-- Нормализованный смысл факта/снимка не редактируется после вставки.
-- Это защита обычного DML, не граница безопасности против владельца схемы/DBA:
-- владелец технически может изменить триггер или выполнить TRUNCATE.
CREATE FUNCTION commerceguard.reject_fact_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = '55000',
        MESSAGE = 'CommerceGuard normalized facts are append-only';
END;
$$;

CREATE TRIGGER core_order_expectation_immutable
    BEFORE UPDATE OR DELETE ON commerceguard.core_order_expectation
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER core_payment_event_immutable
    BEFORE UPDATE OR DELETE ON commerceguard.core_payment_event
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
CREATE TRIGGER core_oms_snapshot_immutable
    BEFORE UPDATE OR DELETE ON commerceguard.core_oms_snapshot
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
