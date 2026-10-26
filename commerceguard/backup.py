"""Я резервирую согласованный DB+raw и восстанавливаю только в пустую свою БД."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4,UUID
from .ingest_journal import MAINTENANCE_LOCK,schema_guard
from .migrations import LOCK_KEY,_check_target
from .postgres import postgres_session
from .raw_store import RawStore
from .workbench_store import WorkbenchError

MAX_FILES=100000
MAX_BYTES=10*1024**3

def digest(path):
    if path.is_symlink() or not path.is_file():raise WorkbenchError('BACKUP_REGULAR_FILE_REQUIRED')
    h=hashlib.sha256();size=0
    with path.open('rb') as f:
        while block:=f.read(1024*1024):h.update(block);size+=len(block)
    return h.hexdigest(),size

def _key(name):
    return name==RawStore.MARKER or bool(re.fullmatch(r'(?:objects/[a-f0-9]{2}/[a-f0-9]{64}|manifests/[a-f0-9]{2}/[a-f0-9]{64}\.json)',name))

@contextmanager
def cli_environment(dsn_env):
    from psycopg.conninfo import conninfo_to_dict
    value=conninfo_to_dict(os.environ.get(dsn_env,''))
    allowed={'host','port','user','password','dbname','sslmode','connect_timeout','application_name'}
    if set(value)-allowed or value.get('dbname')!='commerceguard' or not value.get('host') or ',' in value['host'] or not value.get('user'):
        raise WorkbenchError('BACKUP_DSN_EXPLICIT_SINGLE_HOST')
    env={k:v for k,v in os.environ.items() if not k.startswith('PG')}
    for field in ('host','port','user','dbname','sslmode'): 
        if field in value:env[{'dbname':'PGDATABASE'}.get(field,'PG'+field.upper())]=value[field]
    env.update(PGCONNECT_TIMEOUT='5',PGOPTIONS='-c statement_timeout=600000 -c lock_timeout=5000')
    with tempfile.TemporaryDirectory(prefix='cg-pgpass-') as tmp:
        password=value.get('password','')
        if password:
            esc=lambda s:s.replace('\\','\\\\').replace(':','\\:')
            p=Path(tmp)/'pass';p.write_text('*:*:commerceguard:'+esc(value['user'])+':'+esc(password)+'\n');p.chmod(0o600);env['PGPASSFILE']=str(p)
        yield env

def _tool(bin_dir,name,args,env):
    executable=bin_dir/name
    if not executable.is_file():raise WorkbenchError('BACKUP_POSTGRES16_TOOLS_REQUIRED')
    version=subprocess.run([str(executable),'--version'],check=True,capture_output=True,text=True).stdout
    if not re.search(r'\b16\.',version):raise WorkbenchError('BACKUP_TOOL_VERSION')
    result=subprocess.run([str(executable),*args],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=600)
    if result.returncode:raise WorkbenchError('BACKUP_COMMAND_UNCONFIRMED')

@contextmanager
def maintenance(dsn_env,*,empty=False):
    with postgres_session(dsn_env,application_name='commerceguard-backup') as conn:
        with conn.cursor() as c:
            _check_target(c,apply=True)
            for lock,shared in [(LOCK_KEY,True),(MAINTENANCE_LOCK,False)]:
                c.execute('SELECT '+('pg_try_advisory_lock_shared' if shared else 'pg_try_advisory_lock')+'(%s,%s)',lock)
                if not c.fetchone()[0]:raise WorkbenchError('BACKUP_BUSY',409)
            if empty:
                c.execute("SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('information_schema','public')")
                if c.fetchone()[0]:raise WorkbenchError('RESTORE_EMPTY_DATABASE_REQUIRED',409)
                c.execute("SELECT count(*) FROM pg_class cl JOIN pg_namespace ns ON ns.oid=cl.relnamespace WHERE ns.nspname='public'")
                if c.fetchone()[0]:raise WorkbenchError('RESTORE_EMPTY_DATABASE_REQUIRED',409)
            else:
                with conn.transaction():schema_guard(c,write=False)
            yield c
        # Я закрываю dedicated connection: все session locks освобождаются и при исключении.

def _write_json(path,value):
    with path.open('x',encoding='utf-8') as f:
        os.chmod(path,0o600);json.dump(value,f,sort_keys=True,ensure_ascii=True);f.write('\n');f.flush();os.fsync(f.fileno())

def _sync_tree(root):
    for path in root.rglob('*'):
        if path.is_file():
            with path.open('rb') as f:os.fsync(f.fileno())
    for path in [*sorted((p for p in root.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True),root]:
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

def create_backup(raw_root,output,*,dsn_env='COMMERCEGUARD_DATABASE_URL',pg_bin=Path('/usr/lib/postgresql/16/bin')):
    raw_root=Path(raw_root);output=Path(output)
    RawStore(raw_root).require_owned_root()
    if output.exists() or output.is_symlink() or raw_root.resolve() in output.resolve().parents:raise WorkbenchError('BACKUP_NEW_OUTPUT_REQUIRED')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cg-backup-',dir=output.parent) as temporary:
        stage=Path(temporary)/'bundle';stage.mkdir(mode=0o700);(stage/'raw').mkdir(mode=0o700)
        with maintenance(dsn_env) as c,cli_environment(dsn_env) as env:
            c.execute('SELECT raw_object_key,manifest_object_key FROM commerceguard.ingest_batch');required=set()
            for raw,manifest in c.fetchall():required.update([raw,manifest])
            c.execute('SELECT raw_object_key FROM commerceguard.core_settlement_advice');required.update(r[0] for r in c.fetchall())
            _tool(Path(pg_bin),'pg_dump',['--format=custom','--no-owner','--no-acl','--file',str(stage/'database.dump')],env)
            files={};total=0
            # Я копирую только завершённые immutable raw objects; .pending не часть контракта.
            for path in sorted(raw_root.rglob('*')):
                name=path.relative_to(raw_root).as_posix()
                if path.is_symlink():raise WorkbenchError('BACKUP_SYMLINK')
                if path.is_dir():continue
                if not _key(name):
                    if path.name.startswith('.pending-'):continue
                    raise WorkbenchError('BACKUP_RAW_LAYOUT')
                sha,size=digest(path);total+=size
                if total>MAX_BYTES or len(files)>=MAX_FILES:raise WorkbenchError('BACKUP_LIMIT')
                if name.startswith(('objects/','manifests/')) and path.name.removesuffix('.json')!=sha:raise WorkbenchError('BACKUP_RAW_HASH')
                target=stage/'raw'/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(path,target);target.chmod(0o600)
                files['raw/'+name]={'sha256':sha,'bytes':size}
            if not required<=set(n.removeprefix('raw/') for n in files):raise WorkbenchError('BACKUP_MISSING_REFERENCED_RAW')
            sha,size=digest(stage/'database.dump');files['database.dump']={'sha256':sha,'bytes':size}
            c.execute('SELECT version,checksum FROM commerceguard.schema_migration ORDER BY version');migrations=[list(r) for r in c.fetchall()]
            _write_json(stage/'manifest.json',{'version':1,'postgres_major':16,'migrations':migrations,'files':files})
            verify_backup(stage)
        _sync_tree(stage)
        os.rename(stage,output)
        fd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    return {'files':len(files),'manifest_sha256':digest(output/'manifest.json')[0]}

def verify_backup(bundle):
    bundle=Path(bundle)
    if bundle.is_symlink():raise WorkbenchError('BACKUP_SYMLINK')
    path=bundle/'manifest.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_size>16*1024*1024:raise WorkbenchError('BACKUP_MANIFEST')
    try:manifest=json.loads(path.read_text())
    except (ValueError,UnicodeError):raise WorkbenchError('BACKUP_MANIFEST') from None
    if set(manifest)!={'version','postgres_major','migrations','files'} or manifest['version']!=1 or manifest['postgres_major']!=16 or type(manifest['files']) is not dict or not 2<=len(manifest['files'])<=MAX_FILES+1:raise WorkbenchError('BACKUP_MANIFEST')
    names=set(manifest['files']);actual=set()
    for p in bundle.rglob('*'):
        if p.is_symlink():raise WorkbenchError('BACKUP_SYMLINK')
        if p.is_file():actual.add(p.relative_to(bundle).as_posix())
    if actual!=names|{'manifest.json'} or 'database.dump' not in names or 'raw/'+RawStore.MARKER not in names:raise WorkbenchError('BACKUP_FILE_SET')
    for name,expected in manifest['files'].items():
        if name!='database.dump' and (not name.startswith('raw/') or not _key(name[4:])):raise WorkbenchError('BACKUP_PATH')
        if Path(name).is_absolute() or '..' in Path(name).parts:raise WorkbenchError('BACKUP_PATH')
        sha,size=digest(bundle/name)
        if expected!={'sha256':sha,'bytes':size}:raise WorkbenchError('BACKUP_CHECKSUM')
    return manifest

def _intent(raw_root):return raw_root.with_name('.'+raw_root.name+'.restore.json')

def restore_backup(bundle,raw_root,*,dsn_env='COMMERCEGUARD_DATABASE_URL',pg_bin=Path('/usr/lib/postgresql/16/bin')):
    bundle=Path(bundle);raw_root=Path(raw_root);verify_backup(bundle);bundle_sha=digest(bundle/'manifest.json')[0]
    if raw_root.exists() or raw_root.is_symlink() or _intent(raw_root).exists():raise WorkbenchError('RESTORE_NEW_RAW_REQUIRED')
    raw_root.parent.mkdir(parents=True,exist_ok=True)
    restore_id=str(uuid4());stage=raw_root.with_name('.'+raw_root.name+'.restore-'+restore_id)
    with maintenance(dsn_env,empty=True),cli_environment(dsn_env) as env:
        shutil.copytree(bundle/'raw',stage)
        _sync_tree(stage)
        _write_json(_intent(raw_root),{'restore_id':restore_id,'bundle_sha256':bundle_sha,'stage':stage.name})
        # Я объединяю dump, отзыв sessions и DB receipt одним psql transaction.
        with tempfile.TemporaryDirectory(prefix='cg-restore-sql-') as tmp:
            sql=Path(tmp)/'restore.sql'
            _tool(Path(pg_bin),'pg_restore',['--no-owner','--no-acl','--file',str(sql),str(bundle/'database.dump')],env)
            with sql.open('a') as f:
                f.write("\nDELETE FROM commerceguard.web_session;\nINSERT INTO commerceguard.ops_restore_receipt(restore_id,bundle_sha256) VALUES ('"+restore_id+"','"+bundle_sha+"');\n")
            _tool(Path(pg_bin),'psql',['--no-psqlrc','--single-transaction','--set','ON_ERROR_STOP=1','--file',str(sql)],env)
    return finish_restore(bundle,raw_root,dsn_env=dsn_env)

def finish_restore(bundle,raw_root,*,dsn_env='COMMERCEGUARD_DATABASE_URL'):
    bundle=Path(bundle);raw_root=Path(raw_root);manifest=verify_backup(bundle);intent=_intent(raw_root)
    if intent.is_symlink() or not intent.is_file() or intent.stat().st_size>4096:raise WorkbenchError('RESTORE_INTENT_REQUIRED')
    record=json.loads(intent.read_text());rid=str(UUID(record['restore_id']))
    if set(record)!={'restore_id','bundle_sha256','stage'} or record['bundle_sha256']!=digest(bundle/'manifest.json')[0] or record['stage']!='.'+raw_root.name+'.restore-'+rid:raise WorkbenchError('RESTORE_INTENT')
    with maintenance(dsn_env) as c:
        c.execute('SELECT bundle_sha256 FROM commerceguard.ops_restore_receipt WHERE restore_id=%s',(rid,));row=c.fetchone()
        if not row or row[0]!=record['bundle_sha256']:raise WorkbenchError('RESTORE_COMMIT_UNCONFIRMED')
        stage=raw_root.parent/record['stage']
        candidate=raw_root if raw_root.is_dir() else stage
        if candidate.is_symlink() or not candidate.is_dir():raise WorkbenchError('RESTORE_STAGE_MISSING')
        expected={n[4:]:v for n,v in manifest['files'].items() if n.startswith('raw/')}
        actual={p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
        if actual!=set(expected):raise WorkbenchError('RESTORE_RAW_SET')
        for name,entry in expected.items():
            sha,size=digest(candidate/name)
            if entry!={'sha256':sha,'bytes':size}:raise WorkbenchError('RESTORE_RAW_CHECKSUM')
        if candidate==stage:
            if raw_root.exists():raise WorkbenchError('RESTORE_TARGET_EXISTS')
            os.rename(stage,raw_root)
        RawStore(raw_root).require_owned_root();intent.unlink()
    return {'restored':True,'restore_id':rid,'manifest_sha256':record['bundle_sha256'],'sessions_revoked':True}

def main():
    p=argparse.ArgumentParser(description='Я сохраняю/проверяю/восстанавливаю DB+raw, не перезаписывая существующую БД')
    p.add_argument('action',choices=['create','verify','restore','finish-restore']);p.add_argument('--raw-root',type=Path);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--dsn-env',default='COMMERCEGUARD_DATABASE_URL');p.add_argument('--pg-bin',type=Path,default=Path('/usr/lib/postgresql/16/bin'));a=p.parse_args()
    try:
        if a.action=='verify':result={'verified':True,'files':len(verify_backup(a.bundle)['files'])}
        elif not a.raw_root:raise WorkbenchError('RAW_ROOT_REQUIRED')
        elif a.action=='create':result=create_backup(a.raw_root,a.bundle,dsn_env=a.dsn_env,pg_bin=a.pg_bin)
        elif a.action=='restore':result=restore_backup(a.bundle,a.raw_root,dsn_env=a.dsn_env,pg_bin=a.pg_bin)
        else:result=finish_restore(a.bundle,a.raw_root,dsn_env=a.dsn_env)
        print(json.dumps(result))
    except Exception:p.exit(2,'Я не подтвердил резервирование/восстановление. Сохраняю bundle и restore intent для диагностики, не удаляю целевую БД.\n')
if __name__=='__main__':main()
