"""Я проверяю каталог рядом с SQL: пропущенная модель и ошибочный lineage дают отказ."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'name','kind','path','grain','key','currency_scope','currency_policy','time_policy',
          'lineage','meaning_owner','limitations','metrics'}

class CatalogError(ValueError):
    """Я возвращаю фиксированные коды, без произвольного пути файла."""

def validate(document: dict, root: Path = ROOT) -> dict:
    if type(document) is not dict or set(document) != {'version','entries'} or document['version'] != 1:
        raise CatalogError('CATALOG_VERSION')
    entries = document['entries']
    if type(entries) is not list or not 1 <= len(entries) <= 100:
        raise CatalogError('CATALOG_SIZE')
    names, paths = set(), set()
    for e in entries:
        if type(e) is not dict or set(e) != FIELDS:
            raise CatalogError('CATALOG_SHAPE')
        if not isinstance(e['name'], str) or not re.fullmatch('[a-z][a-z0-9_]{1,80}', e['name']) or e['name'] in names:
            raise CatalogError('CATALOG_IDENTITY')
        names.add(e['name'])
        for field in ('grain','currency_policy','time_policy','meaning_owner'):
            if type(e[field]) is not str or not e[field].strip():
                raise CatalogError('CATALOG_MEANING')
        if e['kind'] != 'dbt-view' or e['currency_scope'] not in ('currency-column','mixed-in-row'):
            raise CatalogError('CATALOG_CURRENCY')
        for field in ('key','lineage','limitations'):
            if type(e[field]) is not list or not e[field] or any(type(x) is not str or not x.strip() for x in e[field]):
                raise CatalogError('CATALOG_LIST')
        if type(e['metrics']) is not dict or not e['metrics'] or any(type(x) is not str or not x.strip() for pair in e['metrics'].items() for x in pair):
            raise CatalogError('CATALOG_METRICS')
        p = Path(e['path'])
        if p.is_absolute() or '..' in p.parts or p.parts[:2] != ('analytics','models') or p.stem != e['name'] or p.suffix != '.sql' or (root/p).is_symlink() or not (root/p).is_file():
            raise CatalogError('CATALOG_PATH')
        paths.add(p.as_posix())
    sql_paths = {p.relative_to(root).as_posix() for p in (root/'analytics/models').rglob('*.sql')}
    if paths != sql_paths:
        raise CatalogError('CATALOG_COVERAGE')
    by_name = {e['name']:e for e in entries}
    visiting, done = set(), set()
    def visit(name):
        if name in visiting:
            raise CatalogError('CATALOG_CYCLE')
        if name in done:
            return
        visiting.add(name)
        entry = by_name[name]
        sql = (root/entry['path']).read_text()
        actual = set(re.findall(r"ref\('([a-z0-9_]+)'\)", sql))
        actual.update('source:'+x for x in re.findall(r"source\('commerceguard', '([a-z0-9_]+)'\)", sql))
        if set(entry['lineage']) != actual:
            raise CatalogError('CATALOG_LINEAGE')
        for parent in entry['lineage']:
            if not parent.startswith('source:'):
                if parent not in by_name:
                    raise CatalogError('CATALOG_PARENT')
                visit(parent)
        visiting.remove(name); done.add(name)
    for name in names:
        visit(name)
    return document

def load_catalog() -> dict:
    return validate(json.loads(Path(__file__).with_name('catalog.json').read_text()))

def main():
    p=argparse.ArgumentParser(description='Я читаю проверяемый каталог аналитики без подключения к БД')
    p.add_argument('action',choices=['check','list','show']); p.add_argument('name',nargs='?')
    a=p.parse_args()
    try:
        d=load_catalog()
        if a.action=='check': result={'valid':True,'views':len(d['entries'])}
        elif a.action=='list': result=[{'name':e['name'],'grain':e['grain']} for e in d['entries']]
        else:
            result=next((e for e in d['entries'] if e['name']==a.name),None)
            if result is None: raise CatalogError('CATALOG_NOT_FOUND')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except CatalogError as e: p.exit(2,str(e)+'\n')

if __name__=='__main__': main()
