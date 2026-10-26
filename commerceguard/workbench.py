"""Я даю локальное рабочее место без внешних assets, JavaScript и доступа к raw файлам."""
import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

from .catalog import load_catalog
from .case_store import show_case
from .postgres import DatabaseError
from .run_execution import read_evidence
from .source_health_store import source_health
from .workbench_store import WorkbenchError, queue

CSS='body{font:16px system-ui;max-width:1150px;margin:2rem auto;padding:0 1rem;background:#f7f8fc;color:#17243d}nav,a{color:#2453ab}table{border-collapse:collapse;width:100%;background:white}td,th{padding:.7rem;border-bottom:1px solid #d9dfec;text-align:left}input,select,button,textarea{font:inherit;padding:.45rem;margin:.3rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:1rem}label{display:inline-block}small{color:#52617b}.badge{padding:.4rem;background:#e4edff}section{margin:1.5rem 0}'
def e(value): return escape(str(value),quote=True)
def pretty(value): return '<pre>'+e(json.dumps(value,ensure_ascii=False,indent=2))+'</pre>'
def page(title, body):
    return ('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>'+e(title)+' · CommerceGuard</title><style>'+CSS+'</style><nav><a href="/">Очередь</a> · '
            '<a href="/catalog">Каталог показателей</a></nav><h1>'+e(title)+'</h1>'+body+
            '<footer><small>Учебное локальное рабочее место. Финансовые операции здесь не выполняются.</small></footer></html>').encode()

def params(query):
    if len(query)>4000: raise WorkbenchError('QUERY_TOO_LARGE',413)
    pairs=parse_qsl(query,keep_blank_values=True,max_num_fields=20,errors='strict')
    if len(dict(pairs))!=len(pairs): raise WorkbenchError('QUERY_DUPLICATE')
    return dict(pairs)

def queue_html(data,p):
    fields=[('merchant','Магазин'),('currency','Валюта: RUB/USD/EUR'),('rule','Правило'),
            ('status','Статус: open/closed/all'),('presence','Наличие: present/absent/all'),
            ('age_min_days','Возраст от дней'),('age_max_days','Возраст до дней')]
    form='<form method="get" action="/">'+''.join('<label>'+label+'<input name="'+key+'" value="'+e(p.get(key,{'status':'open','presence':'present','age_min_days':'0','age_max_days':'36500'}.get(key,'')))+'"></label>' for key,label in fields)+'<button>Отобрать</button></form>'
    context=data['context']
    if context:
        form+='<p class="badge">Canonical run '+e(context['run_id'])+' · as_of '+e(context['as_of'])+' · возраст расчёта '+e(context['age_seconds'])+' секунд</p>'
    else: form+='<p>Canonical run пока отсутствует. Я сначала публикую результат и применяю Case.</p>'
    form+='<p>Момент чтения: '+e(data['evaluated_at'])+'. Количество карточек по валюте: '+e(data['counts_by_currency'])+'. Денежный итог между валютами не вычисляю.</p>'
    form+='<table><tr><th>Заказ</th><th>Валюта</th><th>Правило</th><th>Наличие / разбор</th><th>Впервые обнаружен</th></tr>'
    for x in data['items']:
        form+='<tr><td><a href="/case/'+x['case_key']+'">'+e(x['order_id'])+'</a></td>'+''.join('<td>'+e(v)+'</td>' for v in [x['currency'],x['rule'],x['presence']+' / '+x['status'],x['first_detected_at']])+'</tr>'
    form+='</table>'
    if not data['items']: form+='<p>По выбранным фильтрам карточек нет.</p>'
    if data['next_after']:
        form+='<p><a href="/?'+e(urlencode({**p,'after':data['next_after'],'run_id':context['run_id']}))+'">Следующая страница</a></p>'
    return form+'<p><a href="/health?'+e(urlencode({'merchant':data['merchant']}))+'">Свежесть и полнота источников</a></p>'

class Server(HTTPServer):
    def __init__(self,port,dsn_env):
        if type(port) is not int or not 0<=port<=65535: raise WorkbenchError('PORT_INVALID')
        self.dsn_env=dsn_env
        super().__init__(('127.0.0.1',port),Handler)
        self.origin='http://127.0.0.1:'+str(self.server_port)
    def get_request(self):
        sock,addr=super().get_request();sock.settimeout(10);return sock,addr

class Handler(BaseHTTPRequestHandler):
    server_version='CommerceGuard';sys_version=''
    def log_message(self,*args): pass  # Я не записываю URL, cookie или тело формы в access log.
    def guard(self):
        if self.headers.get_all('Host')!=[self.server.origin.removeprefix('http://')]: raise WorkbenchError('HOST_REJECTED',403)
        if self.headers.get('Sec-Fetch-Site') not in (None,'none','same-origin'): raise WorkbenchError('CROSS_SITE_REJECTED',403)
    def send(self,status,title,body,headers=None):
        raw=page(title,body);self.send_response(status)
        for k,v in {'Content-Type':'text/html; charset=utf-8','Content-Length':str(len(raw)),
                    'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
                    'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
                    'Connection':'close',**(headers or {})}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(raw);self.close_connection=True
    def do_GET(self):
        try:
            self.guard();u=urlsplit(self.path)
            if u.scheme or u.netloc or u.fragment: raise WorkbenchError('PATH_INVALID')
            p=params(u.query);env={'dsn_env':self.server.dsn_env}
            if u.path=='/':
                if not p: return self.send(200,'Очередь расхождений','<p>Я выбираю магазин для начала разбора.</p><form><input name="merchant" placeholder="merchant_demo" required><button>Открыть</button></form>')
                return self.send(200,'Очередь расхождений',queue_html(queue(p,**env),p))
            if u.path=='/catalog':
                if p: raise WorkbenchError('QUERY_UNKNOWN')
                d=load_catalog();return self.send(200,'Каталог показателей',''.join('<section><h2>'+e(x['name'])+'</h2>'+pretty(x)+'</section>' for x in d['entries']))
            if u.path=='/health':
                if set(p)!={'merchant'}:raise WorkbenchError('QUERY_UNKNOWN')
                d=source_health(p['merchant'],as_of='now',business_timezone='Europe/Moscow',max_age_seconds=86400,late_after_seconds=3600,**env)
                return self.send(200,'Свежесть источников',pretty(d))
            match=re.fullmatch('/case/([a-f0-9]{64})(/evidence)?',u.path)
            if match:
                if set(p)-{'before_revision'}:raise WorkbenchError('QUERY_UNKNOWN')
                d=show_case(match[1],before_revision=int(p['before_revision']) if p.get('before_revision') else None,**env)
                if not d['found']:raise WorkbenchError('CASE_NOT_FOUND',404)
                if match[2]: return self.send(200,'Происхождение фактов',pretty(read_evidence(d['head']['last_seen_run_id'],case_key=match[1],limit=100,**env)))
                body=pretty(d['head'])+'<p><a href="/case/'+match[1]+'/evidence">OMS / PSP batch, raw row, SHA</a></p>'+pretty(d['application'])+'<h2>История наблюдений</h2>'+pretty(d['history'])
                if d['next_before_revision']:body+='<a href="?before_revision='+str(d['next_before_revision'])+'">Предыдущие ревизии</a>'
                return self.send(200,'Карточка '+d['head']['order_id'],body)
            raise WorkbenchError('NOT_FOUND',404)
        except WorkbenchError as ex:self.send(ex.status,'Запрос отклонён',e(ex.code))
        except DatabaseError:self.send(503,'База недоступна','Я не подтвердил чтение. Проверяю подключение и версию схемы локально.')
        except ValueError:self.send(400,'Некорректный запрос','Я проверяю фильтры и идентификаторы.')
        except Exception:self.send(500,'Ошибка приложения','Я не подтвердил выполнение запроса; детали данных не вывожу.')
    def do_POST(self): self.send(405,'Только чтение','Изменения HTTP пока не включены.',{'Allow':'GET'})

def main():
    p=argparse.ArgumentParser(description='Локальное рабочее место CommerceGuard')
    p.add_argument('action',choices=['serve']);p.add_argument('--port',type=int,default=8765);p.add_argument('--dsn-env',default='COMMERCEGUARD_DATABASE_URL')
    a=p.parse_args()
    try:
        with Server(a.port,a.dsn_env) as server:
            print('Я открыл CommerceGuard: '+server.origin,flush=True)
            try: server.serve_forever()
            except KeyboardInterrupt: pass
    except (OSError,WorkbenchError):p.exit(2,'Я не смог открыть loopback порт. Проверяю --port.\n')
if __name__=='__main__':main()
