-- Я отделяю локальную identity от финансовых фактов. Учётные записи создаю только CLI.
CREATE TABLE commerceguard.web_user (
    username text PRIMARY KEY CHECK (username ~ '^[a-z][a-z0-9_-]{2,31}$'),
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('analyst','manager','observer','engineer')),
    active boolean NOT NULL DEFAULT true,
    failed_logins integer NOT NULL DEFAULT 0 CHECK (failed_logins BETWEEN 0 AND 5),
    locked_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE commerceguard.web_user_merchant (
    username text NOT NULL REFERENCES commerceguard.web_user(username),
    merchant_id text NOT NULL CHECK (merchant_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'),
    PRIMARY KEY (username,merchant_id)
);
CREATE TABLE commerceguard.web_session (
    token_hash text PRIMARY KEY CHECK (token_hash ~ '^[a-f0-9]{64}$'),
    username text NOT NULL REFERENCES commerceguard.web_user(username),
    csrf_token text NOT NULL CHECK (csrf_token ~ '^[a-f0-9]{64}$'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    CHECK (expires_at>created_at AND expires_at<=created_at+interval '8 hours')
);
CREATE INDEX web_session_user_idx ON commerceguard.web_session(username);
