"""Я проверяю серверную identity; роли из формы и cookie не считаю полномочиями."""
import argparse
import getpass
import hashlib
import hmac
import re
import secrets
from .domain import require_id
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .workbench_store import WorkbenchError

ROLES={'analyst','manager','observer','engineer'}
ITERATIONS=600000

def username(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9_-]{2,31}',value): raise WorkbenchError('ACCOUNT_NAME')
    return value

def password_hash(password):
    if type(password) is not str or not 12<=len(password)<=256 or '\x00' in password: raise WorkbenchError('PASSWORD_LENGTH_12_256')
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'

def verify_password(password,encoded):
    if type(password) is not str or not 1<=len(password)<=256 or '\x00' in password: return False
    if not re.fullmatch(r'pbkdf2_sha256\$600000\$[a-f0-9]{32}\$[a-f0-9]{64}',encoded):return False
    _,rounds,salt,digest=encoded.split('$')
    actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)).hex()
    return hmac.compare_digest(actual,digest)

# Я использую dummy KDF и для неизвестного имени; реальной учётной записи здесь нет.
DUMMY='pbkdf2_sha256$600000$'+'0'*32+'$'+'0'*64

def token_hash(token):
    if type(token) is not str or not re.fullmatch('[a-f0-9]{64}',token): raise WorkbenchError('LOGIN_REQUIRED',401)
    return hashlib.sha256(token.encode('ascii')).hexdigest()

def create_user(name,password,role,merchants,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    username(name)
    if role not in ROLES or not 1<=len(merchants)<=100 or len(set(merchants))!=len(merchants):raise WorkbenchError('ACCOUNT_SCOPE')
    for merchant in merchants:require_id(merchant,'merchant_id')
    encoded=password_hash(password)
    with postgres_session(dsn_env,application_name='commerceguard-account') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c)
                c.execute('INSERT INTO commerceguard.web_user(username,password_hash,role) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING RETURNING username',(name,encoded,role))
                if not c.fetchone():raise WorkbenchError('ACCOUNT_EXISTS',409)
                c.executemany('INSERT INTO commerceguard.web_user_merchant(username,merchant_id) VALUES(%s,%s)',[(name,m) for m in merchants])
    return {'username':name,'role':role,'merchants':merchants}

def disable_user(name,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    username(name)
    with postgres_session(dsn_env,application_name='commerceguard-account') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c)
                c.execute('UPDATE commerceguard.web_user SET active=false WHERE username=%s RETURNING username',(name,))
                if not c.fetchone():raise WorkbenchError('ACCOUNT_NOT_FOUND',404)
                c.execute('DELETE FROM commerceguard.web_session WHERE username=%s',(name,))

def login(name,password,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    # Я сохраняю failed counter отдельным успешным COMMIT, даже когда вход отвергнут.
    accepted=False;token=None
    if not isinstance(name,str) or len(name)>32:raise WorkbenchError('LOGIN_FAILED',403)
    with postgres_session(dsn_env,application_name='commerceguard-login') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c)
                c.execute('SELECT password_hash,active,failed_logins,locked_until,clock_timestamp() FROM commerceguard.web_user WHERE username=%s FOR UPDATE',(name,))
                row=c.fetchone()
                matches=verify_password(password,row[0] if row else DUMMY)
                if row and row[1] and (row[3] is None or row[3]<=row[4]):
                    if matches:
                        c.execute('UPDATE commerceguard.web_user SET failed_logins=0,locked_until=NULL WHERE username=%s',(name,))
                        c.execute('DELETE FROM commerceguard.web_session WHERE username=%s AND expires_at<=clock_timestamp()',(name,))
                        c.execute('SELECT count(*) FROM commerceguard.web_session WHERE username=%s',(name,))
                        if c.fetchone()[0]>=20:raise WorkbenchError('SESSION_LIMIT',429)
                        token=secrets.token_hex(32);csrf=secrets.token_hex(32)
                        c.execute("INSERT INTO commerceguard.web_session(token_hash,username,csrf_token,created_at,expires_at) SELECT %s,%s,%s,t,t+interval '8 hours' FROM (SELECT clock_timestamp() t) x",(token_hash(token),name,csrf))
                        accepted=True
                    else:
                        failures=(0 if row[3] is not None else row[2])+1
                        c.execute("UPDATE commerceguard.web_user SET failed_logins=%s,locked_until=CASE WHEN %s>=5 THEN clock_timestamp()+interval '5 minutes' ELSE NULL END WHERE username=%s",(failures,failures,name))
    if not accepted:raise WorkbenchError('LOGIN_FAILED',403)
    return token

def authorize(c,token,*,merchant=None,action='read',csrf=None):
    """Я удерживаю SHARE locks до COMMIT, чтобы disable не гонялся с mutation."""
    c.execute('SELECT u.username,u.role,s.csrf_token FROM commerceguard.web_session s JOIN commerceguard.web_user u USING(username) '
              'WHERE s.token_hash=%s AND s.expires_at>clock_timestamp() AND u.active FOR SHARE OF u,s',(token_hash(token),))
    row=c.fetchone()
    if not row:raise WorkbenchError('LOGIN_REQUIRED',401)
    if action not in ('read','logout','assign','comment','close','reopen'):raise WorkbenchError('ACTION_FORBIDDEN',403)
    if action!='read' and (type(csrf) is not str or re.fullmatch('[a-f0-9]{64}',csrf) is None or not hmac.compare_digest(row[2],csrf)):raise WorkbenchError('CSRF_REJECTED',403)
    allowed={'read':ROLES,'logout':ROLES,'assign':{'analyst','manager'},'comment':{'analyst','manager'},'close':{'manager'},'reopen':{'manager'}}
    if row[1] not in allowed[action]:raise WorkbenchError('ROLE_FORBIDDEN',403)
    c.execute('SELECT merchant_id FROM commerceguard.web_user_merchant WHERE username=%s ORDER BY merchant_id',(row[0],))
    merchants=[r[0] for r in c.fetchall()]
    if merchant is not None and merchant not in merchants:raise WorkbenchError('SCOPE_FORBIDDEN',403)
    return {'username':row[0],'role':row[1],'csrf':row[2],'merchants':merchants}

def session(token,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    with postgres_session(dsn_env,application_name='commerceguard-session') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c,write=False);return authorize(c,token)

def logout(token,csrf,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    with postgres_session(dsn_env,application_name='commerceguard-logout') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c);authorize(c,token,action='logout',csrf=csrf)
                c.execute('DELETE FROM commerceguard.web_session WHERE token_hash=%s',(token_hash(token),))

def reset_password(name,password,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    username(name);encoded=password_hash(password)
    with postgres_session(dsn_env,application_name='commerceguard-account-reset') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c)
                c.execute('UPDATE commerceguard.web_user SET password_hash=%s,failed_logins=0,locked_until=NULL WHERE username=%s RETURNING username',(encoded,name))
                if not c.fetchone():raise WorkbenchError('ACCOUNT_NOT_FOUND',404)
                c.execute('DELETE FROM commerceguard.web_session WHERE username=%s',(name,))

def enable_user(name,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    username(name)
    with postgres_session(dsn_env,application_name='commerceguard-account-enable') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                schema_guard(c)
                c.execute('UPDATE commerceguard.web_user SET active=true,failed_logins=0,locked_until=NULL WHERE username=%s RETURNING username',(name,))
                if not c.fetchone():raise WorkbenchError('ACCOUNT_NOT_FOUND',404)

def main():
    p=argparse.ArgumentParser(description='Я управляю локальными учётными записями; пароль ввожу скрыто')
    p.add_argument('action',choices=['create','disable','reset','enable']);p.add_argument('username');p.add_argument('--role',choices=sorted(ROLES));p.add_argument('--merchant',action='append',default=[]);p.add_argument('--dsn-env',default='COMMERCEGUARD_DATABASE_URL')
    a=p.parse_args()
    try:
        if a.action in ('create','reset'):
            first=getpass.getpass('Новый пароль (12–256 символов): ');second=getpass.getpass('Повтор пароля: ')
            if first!=second:raise WorkbenchError('PASSWORD_MISMATCH')
            if a.action=='create':create_user(a.username,first,a.role,a.merchant,dsn_env=a.dsn_env)
            else:reset_password(a.username,first,dsn_env=a.dsn_env)
        elif a.action=='enable':enable_user(a.username,dsn_env=a.dsn_env)
        else:disable_user(a.username,dsn_env=a.dsn_env)
        print('Я сохранил изменение учётной записи.')
    except (ValueError,EOFError):p.exit(2,'Я не подтвердил изменение. Проверяю имя, роль, scope и соединение локально.\n')
if __name__=='__main__':main()
