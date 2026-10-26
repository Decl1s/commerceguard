# Как я устанавливаю рабочий экземпляр

Первую поставку я ориентирую на одну организацию и Linux x86_64 с Docker Engine/
Compose. На этой платформе я фактически проверяю контейнеры. Windows/macOS и
внешний доступ по реальному домену отдельно не подтверждаю. Историю разработки
проекта сохраняю как самостоятельную работу, реальных клиентов не выдумываю.

```bash
python3 deploy/configure.py
 docker compose --env-file workspace/deployment/.env -f deploy/compose.yml up -d --build --wait
```

В новом закрытом каталоге workspace/deployment я генерирую три независимых случайных
секрета: owner_password, web_password, operator_password. Ни один пароль не задан
в исходниках. Каталог0700 ограничивает доступ на хосте; secret files0444 нужны
non-root контейнерам, куда Compose монтирует конкретные файлы. .env0600 содержит
только путь/порт/origin/merchant, паролей в нём нет. Повторная configure не меняет
существующий каталог. Секреты и .env никогда не добавляю в PUBLIC_FILES/Git.

Я открываю http://127.0.0.1:8765/login. Первый аккаунт — manager, его случайный
пароль читаю локально из operator_password. Изначально бизнес-данных нет. Для
воспроизводимого знакомства могу явно добавить синтетический M01:

```bash
docker compose --env-file workspace/deployment/.env -f deploy/compose.yml run --rm --build tools demo
```

`demo` не является обязательным шагом рабочей установки. Он явно создаёт учебные
файлы, публикует и применяет сверку; чужие документы не ищет. Реальные OMS/PSP
загружаю инженерным file/manifest протоколом INPUTS/INGESTION/ORCHESTRATION, без
ручного редактирования canonical facts. Каталоги исходных файлов и raw задаю
явно. Самостоятельного облачного PSP API в первой версии нет.

## Почему я разделил контейнеры

| Компонент | Доступ и назначение |
| --- | --- |
| PostgreSQL16.15 | Только внутренняя backend сеть; порт БД на хост не публикую |
| init | Явные миграции, runtime grants и первый аккаунт; затем процесс завершается |
| web | Waitress3.0.2,4threads,64connections,32KiBbody,16KiBheaders; только web password |
| proxy | Caddy2.11.7 соединяет edge/backend; единственный порт опубликован на127.0.0.1 |
| tools | Owner secret и raw volume; отдельные analytics/Prefect venv, инженерные команды |

Web/proxy работают non-root, с read-only rootfs, cap_drop ALL и no-new-privileges.
Raw filesystem и owner secret в web вообще не смонтированы. Я удалил ненужную
file capability Caddy для privileged port: он слушает8081. Backend сеть internal,
proxy имеет отдельную edge сеть. Docker logging ограничен3файлами по10MiB.
Базы Python3.12.15/PostgreSQL16.15/Caddy2.11.7 закреплены digest, Python зависимости
закреплены hashes. Состав OS-пакетов сохраняю в image os-packages.txt.

Runtime commerceguard_web не владеет схемой, не мигрирует и не изменяет финансовые
core tables. Я выдал чтение, необходимые column-level updates workflow/login,
INSERT audit и session операции. PostgreSQL требует UPDATE хотя бы одной колонки
даже для FOR SHARE session row; я подтвердил это ошибкой прав первого прогона
первого прогона и добавил ровно csrf_token privilege. DELETE canonical PSP факт
под runtime я проверил: БД отказала. Это не модель против владельца БД/сервера.

## Как я управляю экземпляром

```bash
docker compose --env-file workspace/deployment/.env -f deploy/compose.yml ps
 docker compose --env-file workspace/deployment/.env -f deploy/compose.yml logs --tail 50 web
 docker compose --env-file workspace/deployment/.env -f deploy/compose.yml down
```

`down` останавливает контейнеры, volumes сохраняются. `up` поднимает прежние данные;
init не сбрасывает существующий пароль. `down --volumes` не использую для обычной
остановки. В автоматической проверке он удаляет только уникальный временный project.
Не публикую Docker socket внутрь приложения. Системные службы не устанавливаю.

Через `run --rm tools account create NAME --role analyst --merchant M01` создаю
аккаунты; disable/enable/reset управляют доступом. Reset вводит новый пароль getpass,
отзывает sessions и снимает login lock, но не включает отключённый аккаунт автоматически.
Для reset после restore использую owner tools, не пытаюсь угадывать старый пароль.

Tools image содержит /opt/analytics и /opt/orchestration с независимыми hash locks.
Для pipeline использую `tools cli pipeline ... --analytics-python /opt/analytics/bin/python`;
entrypoint выбирает orchestration Python. `tools pipeline-demo` проходит полный
синтетический Prefect/dbt путь и останавливает временный backend. Новые директории
scratch создаются в приватном raw volume, web доступа к ним не имеет.

Резервные копии создаю owner tools `backup create` в новом /var/lib/commerceguard/
backups/NAME. Проверяю `backup verify`, выношу копию на отдельное защищённое хранение.
Для копирования остановленного tools контейнера могу использовать compose create tools,
затем compose cp tools:/var/lib/commerceguard/backups/NAME workspace/offline/NAME;
не удаляю volume ради выгрузки. Restore выполняю в отдельной пустой БД до init/web,
сверяю bundle, отзываю sessions и заново выдаю runtime grants. Порядок и crash window
подробно описал в BACKUP; автоматического DROP/перезаписи базы нет.

## Как я ограничиваю сетевой доступ

Default опубликован только на127.0.0.1. Для команды в сети я сначала назначаю
свой DNS/origin с https, TLS certificate и reverse proxy, затем явно меняю bind/
конфигурацию Caddy. Прямой публичный HTTP origin сервер отвергает; cookies получают
Secure при HTTPS. Host/Origin не доверяют произвольным forwarded headers. Default
Caddyfile здесь локальный HTTP: наличие Caddy не означает уже настроенный TLS.
Реальный домен/сертификат в этой поставке самопроизвольно не создаю.

## Что я фактически проверяю

scripts/check_delivery.py создаёт уникальный project, проверяет fresh installation,
login/queue/comment/close/reopen/export, SQL denial runtime,40requests/concurrency4,
web restart и down/up с прежними volumes. Проверяю также tools Prefect/dbt и
контейнерные pg_dump/verify. Все тестовые ресурсы удаляю в finally, чужие контейнеры
не трогаю. Это ограниченная приёмочная матрица, не обещание произвольной нагрузки.
Ошибки tmpfs quoting, internal-only published port, file capability proxy и FOR SHARE
privilege обнаружил и исправил до отметки готовности поставки.
