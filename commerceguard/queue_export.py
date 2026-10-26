"""Я выгружаю одну очередь в одном snapshot, без сырых payload и тихого усечения."""
import csv
import hashlib
import io
from .access import authorize
from .file_contracts import canonical_time
from .ingest_journal import schema_guard
from .postgres import postgres_session
from .workbench_store import WorkbenchError, filters

MAX_EXPORT = 10000
COLUMNS = ('exported_at','canonical_run_id','as_of','knowledge_at','case_key','order_id','currency',
           'rule','presence','status','assignee','finding_revision','workflow_version','evaluated_run_id')

def safe_cell(value):
    """Я оставляю текст текстом даже при открытии CSV в электронной таблице."""
    text = '' if value is None else str(value)
    if text.lstrip(' \ufeff').startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        return "'" + text
    return text

def export_queue(params, *, token, dsn_env='COMMERCEGUARD_DATABASE_URL'):
    if set(params) & {'after','limit'}:
        raise WorkbenchError('EXPORT_NOT_A_PAGE')
    p = filters(params)
    if not p.get('currency'):
        raise WorkbenchError('EXPORT_CURRENCY_REQUIRED')
    with postgres_session(dsn_env, application_name='commerceguard-export') as conn:
        with conn.transaction():
            with conn.cursor() as c:
                # Я беру SHARE locks для session, но бизнес-данные здесь не записываю.
                c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                schema_guard(c, write=False)
                authorize(c, token, merchant=p['merchant'])
                c.execute('SELECT clock_timestamp()')
                now = c.fetchone()[0]
                c.execute('SELECT s.current_run_id,m.as_of,m.knowledge_at FROM commerceguard.ops_case_stream s '
                          'JOIN commerceguard.ops_run_manifest m ON m.run_id=s.current_run_id WHERE s.merchant_id=%s', (p['merchant'],))
                context = c.fetchone()
                if p.get('run_id') and (not context or str(context[0]) != p['run_id']):
                    raise WorkbenchError('QUEUE_HEAD_CHANGED', 409)
                where = ['c.merchant_id=%s','c.currency=%s']
                args = [p['merchant'], p['currency']]
                for field, column in [('rule','rule_code'),('status','workflow_status'),('presence','finding_state'),('assignee','assignee')]:
                    if p.get(field) and p[field] != 'all':
                        where.append('c.' + column + '=%s'); args.append(p[field])
                where.extend(["a.applied_at<=%s-%s*interval '1 day'", "a.applied_at>=%s-%s*interval '1 day'"])
                args.extend([now,p['age_min_days'],now,p['age_max_days']])
                c.execute('SELECT c.case_key,c.order_id,c.currency,c.rule_code,c.finding_state,c.workflow_status,c.assignee,'
                          'c.revision_number,c.workflow_version,c.evaluated_run_id FROM commerceguard.ops_case c '
                          'JOIN commerceguard.ops_case_application a ON a.run_id=c.first_run_id WHERE ' +
                          ' AND '.join(where) + ' ORDER BY c.case_key LIMIT %s', (*args,MAX_EXPORT+1))
                rows = c.fetchall()
                if len(rows)>MAX_EXPORT:
                    raise WorkbenchError('EXPORT_LIMIT',413)
    context_fields = [canonical_time(now), str(context[0]) if context else '',
                      canonical_time(context[1]) if context else '', canonical_time(context[2]) if context else '']
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow([safe_cell(x) for x in (*context_fields,*row)])
    content = output.getvalue().encode('utf-8-sig')
    return {'content':content,'sha256':hashlib.sha256(content).hexdigest(),'rows':len(rows),
            'exported_at':context_fields[0],'canonical_run_id':context_fields[1] or None}
