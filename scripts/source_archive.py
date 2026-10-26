"""Я проверяю явный список публикации и упаковываю только разрешённые исходники."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib

ROOT=Path(__file__).resolve().parents[1]

def sources():
    root=subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip()
    if Path(root).resolve()!=ROOT:raise ValueError('SOURCE_GIT_ROOT')
    names=(ROOT/'PUBLIC_FILES.txt').read_text().splitlines()
    if names!=sorted(set(names)) or 'PUBLIC_FILES.txt' not in names:raise ValueError('SOURCE_LIST')
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    if set(tracked)-set(names):raise ValueError('SOURCE_TRACKED_EXTRA')
    private=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|gh[pousr]_[A-Za-z0-9_]{20,}|github'+r'_pat_|-----BE'+r'GIN .*PRIVATE KEY-----')
    result=[]
    for name in names:
        path=ROOT/name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.is_file():raise ValueError('SOURCE_PATH')
        if name=='AGENTS.md' or Path(name).parts[0] in {'.git','workspace','artifacts','.venv','sources'}:raise ValueError('SOURCE_PRIVATE_PATH')
        raw=path.read_bytes();text=raw.decode('utf-8')
        if private.search(text) or '/ho'+'me/' in text or '/Us'+'ers/' in text:raise ValueError('SOURCE_PRIVATE_CONTENT:'+name)
        result.append((name,raw))
    return result

def archive(output):
    values=sources();version=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version']
    if not re.fullmatch(r'[0-9A-Za-z.]+',version):raise ValueError('SOURCE_VERSION')
    output.mkdir(parents=True,exist_ok=True);path=output/f'commerceguard-{version}-sources.tar.gz'
    # Я обнуляю timestamp/owner; одинаковые исходники дают одинаковый архив.
    with path.open('wb') as file,gzip.GzipFile(filename='',mode='wb',fileobj=file,mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w|') as tar:
        for name,raw in values:
            info=tarfile.TarInfo('commerceguard-'+version+'/'+name);info.size=len(raw);info.mode=0o644;info.mtime=0
            tar.addfile(info,io.BytesIO(raw))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (output/(path.name+'.sha256')).write_text(digest+'  '+path.name+'\n')
    with tarfile.open(path,'r:gz') as tar:
        members=tar.getmembers()
        if [m.name for m in members]!=['commerceguard-'+version+'/'+n for n,_ in values]:raise ValueError('SOURCE_ARCHIVE_LIST')
        for member,(_,raw) in zip(members,values):
            if not member.isfile() or tar.extractfile(member).read()!=raw:raise ValueError('SOURCE_ARCHIVE_BYTES')
    return {'version':version,'files':len(values),'archive':path.name,'sha256':digest}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'artifacts');a=parser.parse_args()
    print(json.dumps(archive(a.output)))
