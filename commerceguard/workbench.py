"""Я даю локальное рабочее место без внешних assets, JavaScript и доступа к raw файлам."""
import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import secrets
import time
from uuid import uuid4
from .case_workflow import mutate,read_workflow,REASONS
import hmac
from http.cookies import SimpleCookie

from .access import session, login, logout
from urllib.parse import parse_qsl, urlencode, urlsplit

from .catalog import load_catalog
from .case_store import show_case
from .postgres import DatabaseError
from .run_execution import read_evidence
from .source_health_store import source_health
from .workbench_store import WorkbenchError, queue
from .queue_export import export_queue
from .observability import HttpStats,event,readiness,metrics

CSS='body{font:16px system-ui;max-width:1150px;margin:2rem auto;padding:0 1rem;background:#f7f8fc;color:#17243d}nav,a{color:#2453ab}table{border-collapse:collapse;width:100%;background:white}td,th{padding:.7rem;border-bottom:1px solid #d9dfec;text-align:left}input,select,button,textarea{font:inherit;padding:.45rem;margin:.3rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:1rem}label{display:inline-block}small{color:#52617b}.badge{padding:.4rem;background:#e4edff}section{margin:1.5rem 0}'
def e(value): return escape(str(value),quote=True)
def pretty(value): return '<pre>'+e(json.dumps(value,ensure_ascii=False,indent=2))+'</pre>'
def page(title, body):
    return ('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>'+e(title)+' · CommerceGuard</title><style>'+CSS+'</style><nav><a href="/">Очередь</a> · '
            '<a href="/catalog">Каталог показателей</a></nav><h1>'+e(title)+'</h1>'+body+
            '<footer><small>Учебное локальное рабочее место. Финансовые операции здесь не выполняются.</small></footer></html>').encode()

def params(query,maximum=4000):
    if len(query)>maximum: raise WorkbenchError('QUERY_TOO_LARGE',413)
    pairs=parse_qsl(query,keep_blank_values=True,max_num_fields=20,errors='strict')
    if len(dict(pairs))!=len(pairs): raise WorkbenchError('QUERY_DUPLICATE')
    return dict(pairs)

def queue_html(data,p):
    fields=[('merchant','Магазин'),('currency','Валюта: RUB/USD/EUR'),('rule','Правило'),
            ('assignee','Исполнитель'),('status','Статус: open/closed/all'),('presence','Наличие: present/absent/all'),
            ('age_min_days','Возраст от дней'),('age_max_days','Возраст до дней')]
    form='<form method="get" action="/">'+''.join('<label>'+label+'<input name="'+key+'" value="'+e(p.get(key,{'status':'open','presence':'present','age_min_days':'0','age_max_days':'36500'}.get(key,'')))+'"></label>' for key,label in fields)+'<button>Отобрать</button></form>'
    if data.get('closed_needs_review'):
        form+='<p class="badge">Закрытых карточек с новым расхождением во всём магазине: '+str(data['closed_needs_review'])+'. <a href="/?'+e(urlencode({'merchant':data['merchant'],'status':'closed'}))+'">Я пересматриваю закрытые решения</a></p>'
    context=data['context']
    if context:
        form+='<p class="badge">Canonical run '+e(context['run_id'])+' · as_of '+e(context['as_of'])+' · возраст расчёта '+e(context['age_seconds'])+' секунд</p>'
    else: form+='<p>Canonical run пока отсутствует. Я сначала публикую результат и применяю Case.</p>'
    form+='<p>Момент чтения: '+e(data['evaluated_at'])+'. Количество карточек по валюте: '+e(', '.join(str(x['case_count'])+' '+x['currency'] for x in data['counts_by_currency']) or '0')+'. Денежный итог между валютами не вычисляю.</p>'
    form+='<table><tr><th>Заказ</th><th>Валюта</th><th>Правило</th><th>Наличие / разбор</th><th>Впервые обнаружен</th><th>Исполнитель</th></tr>'
    for x in data['items']:
        form+='<tr><td><a href="/case/'+x['case_key']+'">'+e(x['order_id'])+'</a></td>'+''.join('<td>'+e(v)+'</td>' for v in [x['currency'],x['rule'],x['presence']+' / '+x['status'],x['first_detected_at'],x.get('assignee') or 'Не назначен'])+'</tr>'
    form+='</table>'
    if not data['items']: form+='<p>По выбранным фильтрам карточек нет.</p>'
    if data['next_after']:
        form+='<p><a href="/?'+e(urlencode({**p,'after':data['next_after'],'run_id':context['run_id']}))+'">Следующая страница</a></p>'
    export_params={k:v for k,v in p.items() if k not in {'after','limit'}}
    if context:export_params['run_id']=context['run_id']
    form+='<p><a href="/export?'+e(urlencode(export_params))+'">Скачать CSV (одна выбранная валюта)</a> · Срез фиксируется в момент выгрузки; очередь могла измениться.</p>'
    return form+'<p><a href="/health?'+e(urlencode({'merchant':data['merchant']}))+'">Свежесть и полнота источников</a></p>'

def money(value,currency):
    if value is None:return 'Неизвестно'
    sign='−' if value<0 else ''
    whole,fraction=divmod(abs(value),100)
    return sign+str(whole)+','+str(fraction).zfill(2)+' '+currency

def case_summary(head,workflow):
    labels={'payment_shortfall':'Недоплата','payment_excess':'Избыточная оплата','refund_missing':'Недостающий возврат','refund_excess':'Избыточный возврат','currency_mismatch':'Несовпадение валют','orphan_payment':'Платёж без заказа'}
    body='<section><p class="badge">'+e(labels.get(head['rule_code'],head['rule_code']))+' · '+e(head['currency'])+'</p><p>Наличие: '+e(head['finding_state'])+' · Разбор: '+e(workflow['status'])+' · Исполнитель: '+e(workflow['assignee'] or 'Не назначен')+'</p>'
    finding=workflow['finding']
    if finding:
        body+='<table><tr><th>Ожидается</th><th>Известный факт</th><th>Разница: факт − ожидание</th></tr><tr>'+''.join('<td>'+e(money(finding[k],head['currency']))+'</td>' for k in ['expected_minor','actual_minor','delta_minor'])+'</tr></table>'
    else:body+='<p>В текущем расчёте этого расхождения нет. Ранее принятое решение и прежнее доказательство я сохраняю.</p>'
    return body+'<p><small>Версия наблюдения '+str(head['revision_number'])+' · Версия разбора '+str(workflow['version'])+' · Run '+e(workflow['run_id'])+'</small></p></section>'

def human_history(workflow):
    labels={'assign':'Назначение','comment':'Комментарий','close':'Закрытие','reopen':'Повторное открытие'}
    body='<h2>История разбора</h2>'
    if not workflow['history']:return body+'<p>Человеческих действий пока нет.</p>'
    for x in workflow['history']:
        body+='<section><strong>'+e(labels[x['action']])+'</strong> · '+e(x['actor'])+' · '+e(x['recorded_at'])+'<p>'+e(x['command'].get('reason_code',''))+'</p><pre>'+e(x['command']['value'])+'</pre><small>Версия '+str(x['version'])+' · Request '+e(x['request_id'])+'</small></section>'
    return body

def workflow_forms(key,workflow,identity):
    if identity['role'] not in ('analyst','manager'):return ''
    hidden='<input type="hidden" name="csrf" value="'+e(identity['csrf'])+'"><input type="hidden" name="expected_version" value="'+str(workflow['version'])+'"><input type="hidden" name="expected_revision" value="'+str(workflow['revision'])+'"><input type="hidden" name="expected_run_id" value="'+e(workflow['run_id'])+'">'
    def form(action,label,field):
        return '<form method="post" action="/case/'+key+'/'+action+'">'+hidden+'<input type="hidden" name="request_id" value="'+str(uuid4())+'">'+field+'<button>'+label+'</button></form>'
    assignment='<label>Исполнитель (пусто — снять)<input name="value" value="'+e(identity['username'] if identity['role']=='analyst' else workflow['assignee'] or '')+'"></label>'
    forms='<h2>Разбор · версия '+str(workflow['version'])+'</h2>'
    if workflow['status']=='open':forms+=form('assign','Назначить',assignment)
    forms+=form('comment','Сохранить комментарий','<label>Комментарий<textarea name="value" maxlength="2000" required></textarea></label>')
    if identity['role']=='manager':
        action='close' if workflow['status']=='open' else 'reopen'
        choices={'source_corrected':'Источник исправлен','confirmed_external':'Проверено вне системы','accepted_difference':'Разница принята','duplicate_investigation':'Дублирующий разбор','new_evidence':'Новые доказательства','decision_revised':'Решение пересмотрено'}
        fields='<label>Причина<select name="reason_code">'+''.join('<option value="'+r+'">'+choices[r]+'</option>' for r in sorted(REASONS[action]))+'</select></label><label>Обоснование<textarea name="value" maxlength="2000" required></textarea></label>'
        forms+=form(action,'Закрыть разбор' if action=='close' else 'Открыть заново',fields)
    if workflow['decision_needs_review']:forms+='<p class="badge">После закрытия наблюдение изменилось. Я пересматриваю решение явно; история закрытия сохранена.</p>'
    return forms

class Server(HTTPServer):
    def __init__(self,port,dsn_env):
        if type(port) is not int or not 0<=port<=65535: raise WorkbenchError('PORT_INVALID')
        self.dsn_env=dsn_env
        self.challenges={}
        self.login_attempts=[]
        self.stats=HttpStats()
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
    def record(self,status):
        if getattr(self,'_recorded',False):return
        self._recorded=True
        self.request_id=str(uuid4())
        duration=max(0,int((time.monotonic()-getattr(self,'started_at',time.monotonic()))*1000000))
        self.server.stats.observe(status,duration)
        match=re.fullmatch('/case/([a-f0-9]{64})(?:/[a-z]+)?',self.path.split('?',1)[0])
        event('http_request',request_id=self.request_id,status=status,duration_us=duration,case_key=match[1] if match else None)
    def bytes_response(self,status,raw,content_type,headers=None):
        self.record(status);self.send_response(status)
        for k,v in {'Content-Type':content_type,'Content-Length':str(len(raw)),'Cache-Control':'no-store','X-Request-ID':self.request_id,'X-Content-Type-Options':'nosniff','X-Request-ID':self.request_id,'Referrer-Policy':'no-referrer','Connection':'close',**(headers or {})}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(raw);self.close_connection=True
    def send(self,status,title,body,headers=None):
        self.record(status)
        raw=page(title,body);self.send_response(status)
        for k,v in {'Content-Type':'text/html; charset=utf-8','Content-Length':str(len(raw)),
                    'Cache-Control':'no-store','X-Request-ID':self.request_id,'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
                    'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
                    'Connection':'close',**(headers or {})}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(raw);self.close_connection=True
    def cookie(self,name='cg_session'):
        raw=self.headers.get('Cookie','')
        if len(raw)>4096 or len(self.headers.get_all('Cookie',[]))>1:raise WorkbenchError('COOKIE_INVALID',400)
        jar=SimpleCookie()
        try:jar.load(raw)
        except Exception:raise WorkbenchError('COOKIE_INVALID',400) from None
        return jar[name].value if name in jar else ''
    def identity(self):
        return session(self.cookie(),dsn_env=self.server.dsn_env)
    def scope(self,identity,merchant):
        if merchant not in identity['merchants']:raise WorkbenchError('SCOPE_FORBIDDEN',403)
    def form(self):
        if self.headers.get_all('Origin')!=[self.server.origin]:raise WorkbenchError('ORIGIN_REJECTED',403)
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:raise WorkbenchError('BODY_INVALID')
        if self.headers.get('Content-Type')!='application/x-www-form-urlencoded':raise WorkbenchError('FORM_TYPE',415)
        length=self.headers.get('Content-Length','')
        if not length.isascii() or not length.isdigit() or not 0<int(length)<=32768:raise WorkbenchError('FORM_SIZE',413)
        raw=self.rfile.read(int(length))
        if len(raw)!=int(length):raise WorkbenchError('BODY_INCOMPLETE')
        return params(raw.decode('utf-8','strict'),32768)
    def login_page(self):
        now=time.monotonic();self.server.challenges={k:v for k,v in self.server.challenges.items() if now-v[1]<600}
        if len(self.server.challenges)>=256:raise WorkbenchError('LOGIN_LIMIT',429)
        token=secrets.token_hex(32);csrf=secrets.token_hex(32);self.server.challenges[token]=(csrf,now)
        body='<p>Я создаю учётную запись локальной командой access create; готового пароля нет.</p><form method="post" action="/login"><input type="hidden" name="csrf" value="'+csrf+'"><label>Имя<input name="username" autocomplete="username" required></label><label>Пароль<input type="password" name="password" autocomplete="current-password" maxlength="256" required></label><button>Войти</button></form>'
        return self.send(200,'Вход в CommerceGuard',body,{'Set-Cookie':'cg_login='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=600'})
    def navigation(self,identity):
        return '<p>Оператор '+e(identity['username'])+' · '+e(identity['role'])+'</p><form method="post" action="/logout"><input type="hidden" name="csrf" value="'+e(identity['csrf'])+'"><button>Выйти</button></form>'
    def download(self,result):
        self.record(200)
        raw=result['content'];self.send_response(200)
        for k,v in {'Content-Type':'text/csv; charset=utf-8','Content-Disposition':'attachment; filename="commerceguard-queue.csv"','Content-Length':str(len(raw)),'Cache-Control':'no-store','X-Request-ID':self.request_id,'X-Content-Type-Options':'nosniff','X-Content-SHA256':result['sha256'],'Connection':'close'}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(raw);self.close_connection=True
    def do_GET(self):
        self.started_at=time.monotonic()
        try:
            self.guard();u=urlsplit(self.path)
            if u.scheme or u.netloc or u.fragment: raise WorkbenchError('PATH_INVALID')
            p=params(u.query);env={'dsn_env':self.server.dsn_env}
            if u.path in ('/livez','/readyz'):
                if p:raise WorkbenchError('QUERY_UNKNOWN')
                ready=u.path=='/livez' or readiness(**env)
                return self.bytes_response(200 if ready else 503,b'{"status":"ok"}' if ready else b'{"status":"unavailable"}','application/json')
            if u.path=='/login':
                if p:raise WorkbenchError('QUERY_UNKNOWN')
                return self.login_page()
            identity=self.identity();nav=self.navigation(identity)
            if u.path=='/':
                if not p:return self.send(200,'Мои магазины',nav+''.join('<p><a href="/?merchant='+e(m)+'">'+e(m)+'</a></p>' for m in identity['merchants']))
                self.scope(identity,p.get('merchant'))
                return self.send(200,'Очередь расхождений',nav+queue_html(queue(p,**env),p))
            if u.path=='/metrics':
                if set(p)!={'merchant'}:raise WorkbenchError('QUERY_UNKNOWN')
                self.scope(identity,p['merchant'])
                return self.bytes_response(200,metrics(p['merchant'],token=self.cookie(),stats=self.server.stats,**env),'text/plain; version=0.0.4; charset=utf-8')
            if u.path=='/export':
                self.scope(identity,p.get('merchant'))
                return self.download(export_queue(p,token=self.cookie(),**env))
            if u.path=='/catalog':
                if p: raise WorkbenchError('QUERY_UNKNOWN')
                d=load_catalog();return self.send(200,'Каталог показателей',''.join('<section><h2>'+e(x['name'])+'</h2>'+pretty(x)+'</section>' for x in d['entries']))
            if u.path=='/health':
                if set(p)!={'merchant'}:raise WorkbenchError('QUERY_UNKNOWN')
                self.scope(identity,p['merchant'])
                d=source_health(p['merchant'],as_of='now',business_timezone='Europe/Moscow',max_age_seconds=86400,late_after_seconds=3600,**env)
                return self.send(200,'Свежесть источников',pretty(d))
            match=re.fullmatch('/case/([a-f0-9]{64})(/evidence)?',u.path)
            if match:
                if set(p)-{'before_revision','before_version'}:raise WorkbenchError('QUERY_UNKNOWN')
                d=show_case(match[1],before_revision=int(p['before_revision']) if p.get('before_revision') else None,**env)
                if not d['found']:raise WorkbenchError('CASE_NOT_FOUND',404)
                self.scope(identity,d['head']['merchant_id'])
                if match[2]: return self.send(200,'Происхождение фактов',pretty(read_evidence(d['head']['last_seen_run_id'],case_key=match[1],limit=100,**env)))
                workflow=read_workflow(match[1],token=self.cookie(),before_version=int(p['before_version']) if p.get('before_version') else None,**env)
                if workflow['revision']!=d['head']['revision_number'] or workflow['run_id']!=d['head']['evaluated_run_id']:raise WorkbenchError('CASE_VIEW_CHANGED',409)
                body=nav+case_summary(d['head'],workflow)+workflow_forms(match[1],workflow,identity)+human_history(workflow)
                body+='<p><a href="/case/'+match[1]+'/evidence">OMS / PSP batch, raw row, SHA</a></p>'+'<details><summary>Контекст и история наблюдений</summary>'+pretty(d['head'])+pretty(d['application'])+pretty(d['history'])+'</details>'
                if workflow['next_before_version']:body+='<p><a href="?before_version='+str(workflow['next_before_version'])+'">Предыдущие действия разбора</a></p>'
                if d['next_before_revision']:body+='<a href="?before_revision='+str(d['next_before_revision'])+'">Предыдущие ревизии</a>'
                return self.send(200,'Карточка '+d['head']['order_id'],body)
            raise WorkbenchError('NOT_FOUND',404)
        except WorkbenchError as ex:self.send(ex.status,'Запрос отклонён',e(ex.code)+'<p><a href="/login">Войти</a></p>')
        except DatabaseError:self.send(503,'База недоступна','Я не подтвердил чтение. Проверяю подключение и версию схемы локально.')
        except ValueError:self.send(400,'Некорректный запрос','Я проверяю фильтры и идентификаторы.')
        except Exception:self.send(500,'Ошибка приложения','Я не подтвердил выполнение запроса; детали данных не вывожу.')
    def do_POST(self):
        self.started_at=time.monotonic();u=urlsplit('/')
        try:
            self.guard();u=urlsplit(self.path)
            if u.scheme or u.netloc or u.query or u.fragment:raise WorkbenchError('PATH_INVALID')
            form=self.form();env={'dsn_env':self.server.dsn_env}
            if u.path=='/login':
                if set(form)!={'username','password','csrf'}:raise WorkbenchError('FORM_FIELDS')
                now=time.monotonic();challenge=self.server.challenges.pop(self.cookie('cg_login'),None)
                if not challenge or now-challenge[1]>=600 or re.fullmatch('[a-f0-9]{64}',form['csrf']) is None or not hmac.compare_digest(challenge[0],form['csrf']):raise WorkbenchError('CSRF_REJECTED',403)
                self.server.login_attempts=[t for t in self.server.login_attempts if now-t<60]
                if len(self.server.login_attempts)>=10:raise WorkbenchError('LOGIN_LIMIT',429)
                self.server.login_attempts.append(now)
                token=login(form['username'],form['password'],**env)
                return self.send(303,'Вход выполнен','<a href="/">Открыть очередь</a>',{'Location':'/','Set-Cookie':'cg_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
            if u.path=='/logout':
                if set(form)!={'csrf'}:raise WorkbenchError('FORM_FIELDS')
                logout(self.cookie(),form['csrf'],**env)
                return self.send(303,'Выход выполнен','<a href="/login">Войти</a>',{'Location':'/login','Set-Cookie':'cg_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
            match=re.fullmatch('/case/([a-f0-9]{64})/(assign|comment|close|reopen)',u.path)
            if match:
                if set(form)!=({'csrf','request_id','expected_version','expected_revision','expected_run_id','value'} | ({'reason_code'} if match[2] in REASONS else set())):raise WorkbenchError('FORM_FIELDS')
                result=mutate(match[1],action=match[2],request_id=form['request_id'],expected_version=int(form['expected_version']),expected_revision=int(form['expected_revision']),expected_run_id=form['expected_run_id'],value=form['value'],token=self.cookie(),csrf=form['csrf'],reason_code=form.get('reason_code'),**env)
                return self.send(303,'Разбор сохранён',pretty(result),{'Location':'/case/'+match[1]})
            raise WorkbenchError('NOT_FOUND',404)
        except WorkbenchError as ex:
            link=u.path.rsplit('/',1)[0] if re.fullmatch('/case/[a-f0-9]{64}/[a-z]+',u.path) else '/login'
            self.send(ex.status,'Действие отклонено',e(ex.code)+'<p>Я обновляю карточку перед новым решением. При повторе неподтверждённого запроса сохраняю прежний request_id.</p><p><a href="'+e(link)+'">Вернуться</a></p>')
        except DatabaseError:self.send(503,'Исход не подтверждён','Я повторяю тот же request_id для изменения, проверяю соединение локально.')
        except (ValueError,UnicodeError):self.send(400,'Некорректная форма','Я проверяю поля формы.')
        except Exception:self.send(500,'Ошибка приложения','Я не подтвердил действие; детали данных не вывожу.')

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
