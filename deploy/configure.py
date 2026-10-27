"""Я генерирую частные случайные секреты один раз, не перезаписывая существующий экземпляр."""
import argparse
import os
from pathlib import Path
import secrets
import ipaddress
import re

def domain_name(value):
    value=value.lower()
    if len(value)>253 or len(value.split('.'))<2 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in value.split('.')):raise ValueError('DOMAIN')
    try:ipaddress.ip_address(value)
    except ValueError:return value
    raise ValueError('DOMAIN_IP')

def configure(directory,port=8765,merchant='M01',domain=None):
    from commerceguard.domain import require_id
    require_id(merchant,'merchant_id')
    if not 1<=port<=65535:raise ValueError('PORT')
    domain=domain_name(domain) if domain is not None else None
    directory=Path(directory)
    if any(c in str(directory.resolve()) for c in '\r\n$#"\''):raise ValueError('DIRECTORY')
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name in ('owner_password','web_password','operator_password'):
        p=directory/name;p.write_text(secrets.token_hex(32)+'\n');p.chmod(0o444)
    # Я не сохраняю пароли в .env: Compose читает отдельные secret files.
    p=directory/'.env'
    origin='https://'+domain if domain else f'http://127.0.0.1:{port}'
    mode='internet' if domain else 'local'
    p.write_text(f'COMMERCEGUARD_SECRETS_DIR={directory.resolve()}\nCOMMERCEGUARD_PORT={port}\nCOMMERCEGUARD_ORIGIN={origin}\nCOMMERCEGUARD_MERCHANT={merchant}\nCOMMERCEGUARD_MODE={mode}\n'+(f'COMMERCEGUARD_DOMAIN={domain}\n' if domain else ''))
    p.chmod(0o600)
    return directory

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Я создаю новые секреты CommerceGuard');p.add_argument('--directory',type=Path,default=Path('workspace/deployment'));p.add_argument('--port',type=int,default=8765);p.add_argument('--merchant',default='M01');p.add_argument('--domain',help='Мой домен без схемы, порта и пути: включает будущий HTTPS профиль');a=p.parse_args()
    # Я запускаю этот файл из checkout без установки приложения в глобальный Python.
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    try:configure(a.directory,a.port,a.merchant,a.domain);print('Я создал закрытые настройки. Пароль первого manager находится в operator_password, не публикую его.')
    except (OSError,ValueError):p.exit(2,'Я не создал настройки: проверяю новый каталог, merchant и порт. Существующие секреты не меняю.\n')
