"""Я выдаю web роль только после миграции и только владельцем своей схемы."""
from .postgres import postgres_session
from .ingest_journal import schema_guard
from .migrations import _check_target,_namespace

def configure(password,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    if len(password)<32 or '\x00' in password:raise ValueError('RUNTIME_PASSWORD')
    from psycopg import sql
    with postgres_session(dsn_env,application_name='commerceguard-runtime-grants') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                role=_check_target(c,apply=True)
                if not _namespace(c,role):raise ValueError('RUNTIME_OWNER_REQUIRED')
                schema_guard(c)
                c.execute("SELECT 1 FROM pg_roles WHERE rolname='commerceguard_web'")
                if not c.fetchone():c.execute('CREATE ROLE commerceguard_web LOGIN')
                c.execute(sql.SQL('ALTER ROLE commerceguard_web WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT PASSWORD {}').format(sql.Literal(password)))
                c.execute('GRANT CONNECT ON DATABASE commerceguard TO commerceguard_web')
                c.execute('GRANT USAGE ON SCHEMA commerceguard TO commerceguard_web')
                c.execute("SELECT tablename FROM pg_tables WHERE schemaname='commerceguard' AND tablename<>'ingest_raw_record'")
                for (name,) in c.fetchall():c.execute(sql.SQL('GRANT SELECT ON commerceguard.{} TO commerceguard_web').format(sql.Identifier(name)))
                c.execute('GRANT SELECT(batch_id,row_number,record_sha256) ON commerceguard.ingest_raw_record TO commerceguard_web')
                c.execute('GRANT UPDATE(failed_logins,locked_until) ON commerceguard.web_user TO commerceguard_web')
                c.execute('GRANT INSERT,DELETE ON commerceguard.web_session TO commerceguard_web')
                # Я разрешаю одну колонку UPDATE: PostgreSQL требует это право для FOR SHARE session row.
                c.execute('GRANT UPDATE(csrf_token) ON commerceguard.web_session TO commerceguard_web')
                c.execute('GRANT UPDATE(workflow_version,assignee,workflow_status) ON commerceguard.ops_case TO commerceguard_web')
                c.execute('GRANT INSERT ON commerceguard.ops_case_human_event TO commerceguard_web')
