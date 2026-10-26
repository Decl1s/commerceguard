"""Я передаю только два явных файла, без host mounts, имён из архива и секретов."""
from pathlib import Path
import struct

MAGIC=b'CGI1'
LIMITS=(64000,100000000)

def exact(stream,size):
    parts=[]
    while size:
        value=stream.read(min(size,1048576))
        if not value:raise ValueError('IMPORT_TRUNCATED')
        parts.append(value);size-=len(value)
    return b''.join(parts)

def send(stream,manifest,data):
    # Я читаю только выбранные файлы и замораживаю их до запуска контейнера.
    values=[]
    for path,limit in zip((manifest,data),LIMITS):
        with Path(path).open('rb') as source:value=source.read(limit+1)
        if len(value)>limit:raise ValueError('IMPORT_SIZE')
        values.append(value)
    stream.write(MAGIC+struct.pack('!II',*(len(v) for v in values)))
    for value in values:stream.write(value)

def receive(stream,directory):
    if exact(stream,4)!=MAGIC:raise ValueError('IMPORT_VERSION')
    sizes=struct.unpack('!II',exact(stream,8))
    if any(size>limit for size,limit in zip(sizes,LIMITS)):raise ValueError('IMPORT_SIZE')
    paths=[]
    for name,size in zip(('manifest.json','data'),sizes):
        path=Path(directory)/name
        with path.open('xb') as target:
            while size:
                value=exact(stream,min(size,1048576));target.write(value);size-=len(value)
        paths.append(path)
    if stream.read(1):raise ValueError('IMPORT_TRAILING_BYTES')
    return paths
