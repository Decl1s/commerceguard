> Я храню полный проверенный исходник в [теге v1.0.0](https://github.com/Decl1s/commerceguard/tree/v1.0.0). Main служит навигацией; исторические PR автоматически не сливаю.
>
> Моя квитанция выпуска: commit `b699899529449ec53f45ee6e2dc3106e09076bc5`,184разрешённых файла. [Финальный CI](https://github.com/Decl1s/commerceguard/actions/runs/40409886361), [релиз](https://github.com/Decl1s/commerceguard/releases/tag/v1.0.0), [архив](https://github.com/Decl1s/commerceguard/releases/download/v1.0.0/commerceguard-1.0.0-sources.tar.gz), [SHA256](https://github.com/Decl1s/commerceguard/releases/download/v1.0.0/commerceguard-1.0.0-sources.tar.gz.sha256).
>
> SHA256 архива: `913320b00ebc150d6d5daf6e3a975957e24f6de20290f075ed1dacd5148ce321`. Я подтвердил запуск из этого архива отдельным Compose/Chrome прогоном с реальными импортом/повтором,CSV,409и сохранением sessions/volumes.

# CommerceGuard

Я разработал информационную систему сверки заказов, оплат и возвратов: от файла OMS/PSP до объяснения суммы, решения финансового специалиста и истории изменений. Это мой самостоятельный портфельный проект с синтетическими примерами и рабочей поставкой. Реального клиента и коммерческий опыт проекту не приписываю.

**Первая версия1.0.0 · 27.10.2026.** Я завершил30 историй и подтвердил полный [CI кандидата](https://github.com/Decl1s/commerceguard/actions/runs/40408987370). Для окончательного commit CI повторяет все обязательные gates; tag и архив публикуются только после их успеха. [Релиз и архив](https://github.com/Decl1s/commerceguard/releases/tag/v1.0.0), [история CI](https://github.com/Decl1s/commerceguard/actions), [матрица](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/RELEASE_CHECKLIST.md), [этапы](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/PROGRESS.md).

## Что я реализовал

| Контур | Результат |
| --- | --- |
| Приём | OMS CSV v1/v2, PSP JSONL, manifest/EOF/SHA, immutable raw, атомарный COPY/publish, журнал и восстановление; повтор без двойных фактов |
| Сверка | Capture/refund отдельно, RUB/USD/EUR без смешения, deadlines, два времени, immutable run/result/evidence, поздние корректировки |
| Settlement | Версии выписки, membership, независимый тариф, gross/refund/fee/net, объяснимое unknown |
| Аналитика | 9dbt views, предварительная агрегация,19data tests, каталог grain/key/time/currency/lineage |
| Оркестрация | Prefect run/resume, preflight, ограниченный retry; backfill1…31 день по сохранённым identities |
| Рабочее место | Русская очередь, фильтры, страницы, карточка с источниками, назначение/комментарий, закрытие/повторное открытие с причиной |
| Доступ | Viewer/analyst/manager, merchant scopes, server sessions, CSRF/Origin/Host, optimistic concurrency, immutable human audit |
| Экспорт | Согласованный CSV одной валюты, canonical context, защита формул, лимит10000 строк |
| Эксплуатация | PostgreSQL15 миграций/31 таблица, DB+raw backup/проверка/restore receipt, health/metrics, ограниченные JSON logs |
| Поставка | Docker Compose, Waitress, Caddy, отдельный runtime SQL role, секреты вне Git, pinned dependencies/base digests |

```mermaid
flowchart LR
  F[OMS CSV / PSP JSONL] --> I[Проверка manifest и raw]
  I --> P[(PostgreSQL canonical facts)]
  P --> R[Immutable run и evidence]
  R --> C[Очередь и история решений]
  R --> D[dbt views и каталог]
  O[Prefect / backfill] --> I
  O --> R
  C --> E[Согласованный CSV]
```

Я отделил финансовое наблюдение от человеческого решения: исчезнувшее расхождение не закрывает разбор автоматически. Историческая корректировка остаётся отдельным report и не подменяет текущий canonical baseline. Прежние результаты сохраняю.

## Как я запускаю рабочий экземпляр

Мой проверенный профиль: **Linux x86_64, Docker Engine/Compose, одна организация, локальный доступ**. Я выделяю минимум4GiB свободной памяти и место для image/БД/raw/backup; это ориентир запуска, не доказанная ёмкость бизнеса. Первый build скачивает закреплённые образы и Python пакеты. Для внешнего домена отдельно настраиваю TLS.

```bash
git clone --branch v1.0.0 --single-branch https://github.com/Decl1s/commerceguard.git
cd commerceguard
python3 deploy/configure.py
docker compose --env-file workspace/deployment/.env -f deploy/compose.yml up -d --build --wait
```

Я открываю http://127.0.0.1:8765/login под `manager`. Случайный пароль читаю локально из `workspace/deployment/operator_password`. Configure создаёт три независимых секрета в закрытом каталоге, существующие настройки не перезаписывает. Реальных бизнес-данных в новой установке нет. Я могу явно загрузить пример:

```bash
docker compose --env-file workspace/deployment/.env -f deploy/compose.yml run --rm --build tools demo
```

Для своих файлов использую `deploy/import_input.py` и отдельные prepare/execute/case apply. Команды и порядок — [HANDBOOK](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/HANDBOOK.md). Аккаунты создаю owner tools; пароли ввожу getpass. Обычная остановка `docker compose ... down` сохраняет volumes. `down --volumes` удаляет данные, для рабочей остановки его не использую. Полный порядок установки, резервирования и внешнего доступа — [DEPLOYMENT](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/DEPLOYMENT.md).

## Как я проверяю исходники

```bash
python3.12 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-analytics.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_postgres.py --pg-bin /usr/lib/postgresql/16/bin
python3.12 -m venv .venv-orchestration
.venv-orchestration/bin/pip install --require-hashes -r requirements-orchestration.lock
.venv-orchestration/bin/python scripts/check_pipeline.py --pg-bin /usr/lib/postgresql/16/bin
python3.12 -m venv .venv-validation
.venv-validation/bin/pip install --require-hashes -r requirements-validation.lock
.venv-validation/bin/python scripts/check_browser.py
```

Integration runners требуют обычную учётную запись с доступными PostgreSQL16 бинарниками, Docker и Chrome. Они создают отдельные временные экземпляры, генерируют данные и удаляют только собственные ресурсы. Я проверяю денежные сценарии, реальные транзакции/конкуренцию, HTTP/Chrome, restore в другой кластер,15 миграций,9dbt views/19tests, Prefect retries/resume, перезапуск web и сохранность volumes. Полный отчёт — [VALIDATION](https://github.com/Decl1s/commerceguard/blob/v1.0.0/VALIDATION.md). Workflow выполняет unit в трёх runtime профилях и проверяет известные уязвимости всех трёх locks; release job зависит от всех gates.

## Где я объясняю устройство

- [START_HERE](https://github.com/Decl1s/commerceguard/blob/v1.0.0/START_HERE.md) — маршрут чтения и работы в IDE.
- [PROJECT_MAP](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/PROJECT_MAP.md), [HANDBOOK](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/HANDBOOK.md) — какой модуль менять и почему.
- [NOTES](https://github.com/Decl1s/commerceguard/blob/v1.0.0/NOTES.md), [EXERCISES](https://github.com/Decl1s/commerceguard/blob/v1.0.0/EXERCISES.md), [DEMO](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/DEMO.md) — конспекты, задания и10 минутный показ.
- [DECISIONS](https://github.com/Decl1s/commerceguard/blob/v1.0.0/DECISIONS.md), [TECHNOLOGIES](https://github.com/Decl1s/commerceguard/blob/v1.0.0/TECHNOLOGIES.md) — аргументы и фактические зависимости с версиями.
- [BACKUP](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/BACKUP.md), [OPERATIONS](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/OPERATIONS.md), [PERFORMANCE](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/PERFORMANCE.md) — сопровождение и измерения.
- [PROGRESS](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/PROGRESS.md), [KANBAN](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/KANBAN.md), [WORKLOG](https://github.com/Decl1s/commerceguard/blob/v1.0.0/docs/WORKLOG.md) — этапы и фактические результаты.

## Какие границы я сохраняю

Я не выполняю платежи, проводки, конвертацию валют и автоматическое списание денег. Входы файловые; расписание/PSP API/SSO/HA/SaaS не входят в1.0. Сырьё и audit требуют планирования диска; автоматической retention нет. Я проверил синтетические сценарии, не подтверждал100 тысяч заказов в сутки или произвольный SLA. Windows/macOS, реальный публичный домен и внешнюю приёмку не заявляю. Владелец БД/хоста остаётся доверенным администратором. Ранние документы со статусом unverified сохраняю как историю; актуальный объём проверок определяется RELEASE_CHECKLIST и VALIDATION.


## Как я готовлю будущий деплой

27.10.2026: сейчас я использую localhost и отдельно подготовил1.1.0.dev1для будущего домена/HTTPS. Stable1.0.0не меняю.

| Срез | Что я подтвердил |
| --- | --- |
| CG-604 | Я сохранил local default и добавил отдельный доменный HTTPS профиль, persistent certificates, manage и инструкцию переноса |
| Проверки | Я прошёл104unit в3профилях, прежний полный integration/Chrome и отдельный HTTPS smoke; [CI успешен](https://github.com/Decl1s/commerceguard/actions/runs/40464921599) |
| Внешняя установка | Я её ещё не выполнял: сервера и домена пока нет; публичный сертификат не выпускал |

[Исходники подготовки](https://github.com/Decl1s/commerceguard/tree/codex/https-deployment), [PR53](https://github.com/Decl1s/commerceguard/pull/53), [localhost/будущий сервер](https://github.com/Decl1s/commerceguard/blob/codex/https-deployment/docs/INTERNET_DEPLOYMENT.md). Для нового сервера я беру эту ветку, поскольку immutable tag1.0.0новых файлов ещё не содержит:

```bash
git clone --branch codex/https-deployment --single-branch https://github.com/Decl1s/commerceguard.git
```
