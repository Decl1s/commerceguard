-- Я подтверждаю DB COMMIT восстановления тем же transaction, что и импорт dump.
CREATE TABLE commerceguard.ops_restore_receipt (
    restore_id uuid PRIMARY KEY,
    bundle_sha256 text NOT NULL CHECK (bundle_sha256 ~ '^[a-f0-9]{64}$'),
    restored_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER ops_restore_receipt_immutable BEFORE UPDATE OR DELETE ON commerceguard.ops_restore_receipt
    FOR EACH ROW EXECUTE FUNCTION commerceguard.reject_fact_mutation();
