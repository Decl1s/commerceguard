"""Я генерирую частные случайные секреты один раз, не перезаписывая существующий экземпляр."""
import argparse
import os
from pathlib import Path
import secrets


def configure(directory,port=8765,merchant='M01'):
    from commerceguard.domain import require_id
    require_id(merchant,'merchant_id')
    if not 1<=port<=65535:raise ValueError('PORT')
    directory=Path(directory)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name in ('owner_password','web_password','operator_password'):
        p=directory/name;p.write_text(secrets.token_hex(32)+'\n');p.chmod(0o444)
    # Я не сохраняю пароли в .env: Compose читает отдельные secret files.
    p=directory/'.env'
    p.write_text(f'COMMERCEGUARD_SECRETS_DIR={directory.resolve()}\nCOMMERCEGUARD_PORT={port}\nCOMMERCEGUARD_ORIGIN=http://127.0.0.1:{port}\nCOMMERCEGUARD_MERCHANT={merchant}\n')
    p.chmod(0o600)
    return directory

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Я создаю новые секреты CommerceGuard');p.add_argument('--directory',type=Path,default=Path('workspace/deployment'));p.add_argument('--port',type=int,default=8765);p.add_argument('--merchant',default='M01');a=p.parse_args()
    # Я запускаю этот файл из checkout без установки приложения в глобальный Python.
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    try:configure(a.directory,a.port,a.merchant);print('Я создал закрытые настройки. Пароль первого manager находится в operator_password, не публикую его.')
    except (OSError,ValueError):p.exit(2,'Я не создал настройки: проверяю новый каталог, merchant и порт. Существующие секреты не меняю.\n')
