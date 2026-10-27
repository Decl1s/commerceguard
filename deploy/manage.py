"""Я выбираю local/HTTPS Compose по закрытым настройкам, сохраняя один project name."""
import argparse
import os
from pathlib import Path
import re
import subprocess
try:
    from .configure import domain_name
except ImportError:
    from configure import domain_name

ROOT=Path(__file__).resolve().parents[1]
KEYS={'COMMERCEGUARD_SECRETS_DIR','COMMERCEGUARD_PORT','COMMERCEGUARD_ORIGIN','COMMERCEGUARD_MERCHANT','COMMERCEGUARD_MODE','COMMERCEGUARD_DOMAIN'}

def compose_command(settings,project='commerceguard'):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}',project):raise ValueError('PROJECT_NAME')
    settings=Path(settings).resolve();values={}
    for line in settings.read_text().splitlines():
        if not line or line.startswith('#'):continue
        key,sep,value=line.partition('=')
        if not sep or key not in KEYS or key in values or any(c in value for c in '$\r\n"\''):raise ValueError('SETTINGS_FORMAT')
        values[key]=value
    if not {'COMMERCEGUARD_SECRETS_DIR','COMMERCEGUARD_PORT','COMMERCEGUARD_ORIGIN','COMMERCEGUARD_MERCHANT'}<=values.keys():raise ValueError('SETTINGS_REQUIRED')
    mode=values.get('COMMERCEGUARD_MODE','local')
    if mode=='internet':
        domain=domain_name(values['COMMERCEGUARD_DOMAIN'])
        if values['COMMERCEGUARD_ORIGIN']!='https://'+domain:raise ValueError('SETTINGS_ORIGIN')
    elif mode=='local':
        port=int(values['COMMERCEGUARD_PORT'])
        if not 1<=port<=65535 or values['COMMERCEGUARD_ORIGIN']!=f'http://127.0.0.1:{port}':raise ValueError('SETTINGS_ORIGIN')
    else:raise ValueError('SETTINGS_MODE')
    # Я не наследую ambient overrides, которые могли бы подменить mode, origin или compose files.
    env={k:v for k,v in os.environ.items() if not k.startswith(('COMPOSE_','COMMERCEGUARD_'))};env.update(values)
    command=['docker','compose','--project-name',project,'--env-file',str(settings),'-f',str(ROOT/'deploy/compose.yml')]
    if mode=='internet':command+=['-f',str(ROOT/'deploy/compose.internet.yml')]
    return command,env

def main():
    p=argparse.ArgumentParser(description='Я управляю своим CommerceGuard без ручного выбора Compose файлов')
    p.add_argument('--settings',type=Path,default=Path('workspace/deployment/.env'));p.add_argument('--project',default='commerceguard');p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args()
    if not a.arguments:p.error('Я указываю команду: up, ps, logs, stop, down или run.')
    try:
        command,env=compose_command(a.settings,a.project)
        return subprocess.run([*command,*a.arguments],cwd=ROOT,env=env).returncode
    except (OSError,ValueError,KeyError):p.exit(2,'Я не запустил Compose: проверяю файл настроек, mode, domain/origin и имя project.\n')

if __name__=='__main__':raise SystemExit(main())
