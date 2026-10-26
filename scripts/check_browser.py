"""Я проверяю настоящий Chromium/Chrome и снимаю только синтетический экземпляр приложения."""
import argparse
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from check_delivery import verify


def browser_check(origin,password,output):
    output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            context=browser.new_context(viewport={'width':1440,'height':1000},locale='ru-RU',accept_downloads=True)
            external=[];errors=[];post_origins=[]
            def route(request):
                if request.request.url.startswith(origin+'/'):request.continue_()
                else:external.append(request.request.url);request.abort()
            context.route('**/*',route)
            context.on('request',lambda r:post_origins.append(r.headers.get('origin')) if r.method=='POST' else None)
            page=context.new_page();page.on('pageerror',lambda ex:errors.append(str(ex)))
            page.goto(origin+'/login')
            page.get_by_label('Имя',exact=True).fill('manager');page.get_by_label('Пароль',exact=True).fill(password)
            page.get_by_role('button',name='Войти',exact=True).click()
            if page.url!=origin+'/':
                message=page.locator('body').inner_text()[:500]
                raise AssertionError('Browser login refused: '+message.replace(password,'[fixture secret]'))
            page.get_by_role('link',name='M01',exact=True).click()
            page.locator('select[name="currency"]').select_option('RUB');page.get_by_role('button',name='Показать очередь').click()
            page.screenshot(path=str(output/'queue.png'),full_page=True)
            with page.expect_download() as downloaded:page.get_by_role('link',name='Скачать CSV выбранной очереди').click()
            artifact=downloaded.value;artifact.save_as(output/'queue.csv')
            assert 'canonical_run_id' in (output/'queue.csv').read_text(encoding='utf-8-sig')
            page.locator('a[href^="/case/"]').first.click();key=re.search('/case/([a-f0-9]{64})',page.url).group(1)
            assignment=page.locator('form[action="/case/'+key+'/assign"]')
            assignment.locator('select[name="value"]').select_option('manager');assignment.get_by_role('button').click()
            old=context.new_page();old.goto(page.url)
            comment=page.locator('form[action="/case/'+key+'/comment"]');comment.locator('textarea').fill('Я сверил синтетическую сумму с исходными событиями.');comment.get_by_role('button').click()
            stale=old.locator('form[action="/case/'+key+'/comment"]');stale.locator('textarea').fill('Я проверяю конфликт двух вкладок.')
            with old.expect_navigation() as navigation:stale.get_by_role('button').click()
            assert navigation.value.status==409
            old.close();page.reload();page.screenshot(path=str(output/'case.png'),full_page=True)
            assert page.get_by_text('Я сверил синтетическую сумму с исходными событиями.',exact=True).count()==1
            assert not external and not errors
            assert post_origins and all(value==origin for value in post_origins)
            return {'engine':browser.version,'stale_form_409':True,'csv_download':True,'external_page_requests':len(external),'screenshots':['queue.png','case.png']}
        finally:browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('artifacts/demo'));parser.add_argument('--no-build',action='store_true');a=parser.parse_args()
    print(json.dumps(verify(build=not a.no_build,browser_check=lambda origin,password:browser_check(origin,password,a.output)),ensure_ascii=False))
