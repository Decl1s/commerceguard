"""Я передаю выбранный manifest/data в owner tools через закрытый stdin."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from transfer import send
from manage import compose_command

def main():
    p=argparse.ArgumentParser(description='Я принимаю OMS/PSP пакет в работающий экземпляр')
    p.add_argument('--settings',type=Path,default=Path('workspace/deployment/.env'))
    p.add_argument('--project',default='commerceguard')
    p.add_argument('--manifest',required=True,type=Path);p.add_argument('--data',required=True,type=Path)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    if not a.settings.is_file():p.exit(2,'Я не нашёл настройки экземпляра.\n')
    try:
        with tempfile.TemporaryFile() as payload:
            send(payload,a.manifest,a.data);payload.seek(0)
            command,env=compose_command(a.settings,a.project)
            result=subprocess.run([*command,'run','--rm','--no-deps','-T','tools','import-input'],stdin=payload,env=env,cwd=root,timeout=600)
            return result.returncode
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired):p.exit(2,'Я не подтвердил импорт. Проверяю выбранные файлы и состояние экземпляра; повтор безопасен по manifest SHA.\n')

if __name__=='__main__':raise SystemExit(main())
