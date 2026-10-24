-- Одна COPY-сессия принимает raw и типизированные поля каждой записи.
-- Таблица изолирована соединением, не переживает COMMIT и не входит в core.
CREATE TEMP TABLE cg_stage_input (
    row_number bigint PRIMARY KEY,
    record_sha256 text NOT NULL,
    record_text text NOT NULL,
    semantic_sha256 text NOT NULL,
    source_event_id text,
    order_id text NOT NULL,
    currency text NOT NULL,
    kind text,
    amount_minor bigint,
    capture_due_minor bigint,
    refund_due_minor bigint,
    settle_after timestamptz,
    occurred_at timestamptz,
    observed_at timestamptz
) ON COMMIT DROP;
