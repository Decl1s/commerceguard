-- Выполняется только для отсутствующей схемы, под transaction advisory lock.
-- Не использовать IF NOT EXISTS: занятое чужое пространство нельзя присвоить.
CREATE SCHEMA commerceguard AUTHORIZATION CURRENT_USER;
REVOKE ALL ON SCHEMA commerceguard FROM PUBLIC;
COMMENT ON SCHEMA commerceguard IS 'commerceguard:storage:v1';

CREATE TABLE commerceguard.app_identity (
    singleton boolean PRIMARY KEY CHECK (singleton),
    app_id text NOT NULL CHECK (app_id = 'commerceguard:storage:v1'),
    storage_format integer NOT NULL CHECK (storage_format = 1)
);
INSERT INTO commerceguard.app_identity (singleton, app_id, storage_format)
VALUES (true, 'commerceguard:storage:v1', 1);

CREATE TABLE commerceguard.schema_migration (
    version integer PRIMARY KEY CHECK (version > 0),
    name text NOT NULL UNIQUE,
    checksum text NOT NULL CHECK (checksum ~ '^[a-f0-9]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT transaction_timestamp()
);
