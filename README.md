# CommerceGuard

**Я разрабатываю учебную информационную систему сверки заказов, оплат и возвратов
интернет-магазина с рабочим местом финансового аналитика.**

Я приближаю задачу к бизнес-запросу: объясняю недоплату, возврат, неверную валюту
и settlement discrepancy, показываю происхождение каждой суммы и сохраняю разбор.
Все примеры синтетические. Реального клиента, коммерческий опыт и банковские
операции этому проекту не приписываю.

**26.10.2026: CG-405, `0.1.0.dev20`. Я добавил согласованный CSV выбранной очереди с одной валютой, версиями и моментом среза.**

Я написал 22/30 историй исходного backlog. Я прошёл84unit и PostgreSQL/HTTP/dbt integration: export filters, scope, canonical run, SHA и запрет смешения валют;dbtPASS28.
Проверки относятся к Linux; полной приёмки, CI и стабильного релиза пока нет.
Карта текущего среза, команды, решения и упражнения — [EXPORT](docs/EXPORT.md).
Таблицу этапов веду в [PROGRESS](docs/PROGRESS.md).

## Что я уже написал

| Контур | Что работает | Существенная граница |
| --- | --- | --- |
| Приём | OMS v1/v2 CSV, PSP JSONL, manifest/hash, frozen input, raw/COPY, атомарная публикация и журнал | Реальный PSP API и персональные данные не использую |
| Сверка | Capture/refund отдельно, два времени, deadlines, immutable run/result/evidence и late corrections | Валюты не конвертирую; historical correction report-only для Case |
| Settlement | Advice revisions/membership, независимый tariff, gross/refund/fee/net, unknown | Не распределяю fee по заказам и не выполняю перечисление |
| Аналитика | 9 dbt views, pre-aggregation перед JOIN, каталог с grain/key/time/currency/lineage | Latest run не выбираю автоматически, revisions не суммирую |
| Оркестрация | Prefect run/resume, preflight, frozen inputs, bounded retry | Локальный временный backend, без Cloud/schedule/daemon |
| Источники | Freshness/completeness/volume, last publication/attempt/success и явный timezone | MAX observations не гарантия внешнего покрытия |
| Рабочее место | Очередь, фильтры/страницы, карточка, суммы, история и OMS/PSP refs | Локальный HTTP adapter, export ещё впереди |
| Разбор | Аккаунты/роли/merchant scopes, server sessions/CSRF, assignee/comments, close/reopen/reason/audit | Прямой владелец БД вне web-ролевой границы |
| Хранение | PostgreSQL schema12,28persistent tables и9аналитических views | Published migrations не переписываю; backup/restore ещё впереди |

## Где я объясняю решения

- [START_HERE](START_HERE.md): маршрут чтения и запуска.
- [WORKPLACE](docs/WORKPLACE.md): интерфейс, роли, версии, audit, ошибки и задания.
- [CATALOG](docs/CATALOG.md): смысл показателей и проверяемый lineage.
- [PROJECT_MAP](docs/PROJECT_MAP.md): карта кода и места изменения.
- [PROGRESS](docs/PROGRESS.md), [KANBAN](docs/KANBAN.md), [BACKLOG](docs/BACKLOG.md): этапы и критерии.
- [MARTS](docs/MARTS.md), [SETTLEMENT](docs/SETTLEMENT.md), [FRESHNESS](docs/FRESHNESS.md),
  [ORCHESTRATION](docs/ORCHESTRATION.md): остальные контуры с упражнениями.
- [DECISIONS](DECISIONS.md), [TECHNOLOGIES](TECHNOLOGIES.md): аргументы и закреплённый стек.

## Как я запускаю проверки

```bash
git clone --branch codex/s4-cg404-case-decisions --single-branch https://github.com/Decl1s/commerceguard.git
cd commerceguard
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-analytics.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m commerceguard.catalog check
.venv/bin/python scripts/check_postgres.py --pg-bin /usr/lib/postgresql/16/bin
```

Я использовал CPython3.12.15 и доступные PostgreSQL16.15 binaries под обычной
учётной записью Linux. Runner создаёт собственный кластер без TCP и временный HTTP
на127.0.0.1, генерирует данные и останавливает/удаляет всё в finally. Чужие БД,
системные службы и реальные выгрузки не трогает. Он проверяет UI по HTTP, но не
оставляет долговечную demo БД. Для проверки Prefect у меня отдельное окружение:

```bash
python3.12 -m venv .venv-orchestration
.venv-orchestration/bin/python -m pip install --require-hashes -r requirements-orchestration.lock
.venv-orchestration/bin/python scripts/check_pipeline.py --pg-bin /usr/lib/postgresql/16/bin
```

Оба lock содержат hash pins транзитивных зависимостей. Prefect временно использует
loopback backend и останавливает его; внешние Cloud credentials не наследую.

## Как я открываю рабочее место

Для своей уже подготовленной БД commerceguard я задаю DSN во внешней переменной
COMMERCEGUARD_DATABASE_URL, без пароля в командной строке/репозитории. Подготовку
синтетического ingest/run/case описал в [WORKBENCH](docs/WORKBENCH.md),
[RESULTS](docs/RESULTS.md) и [CASES](docs/CASES.md). Затем:

```bash
.venv/bin/python -m commerceguard db migrate
.venv/bin/python -m commerceguard.access create analyst_demo --role analyst --merchant M01
.venv/bin/python -m commerceguard.access create manager_demo --role manager --merchant M01
.venv/bin/python -m commerceguard.workbench serve --port 8765
```

Я ввожу собственные пароли скрыто; готовых credentials нет. Открываю
`http://127.0.0.1:8765/login`, вхожу, выбираю M01. Проверяю очередь → evidence →
назначение → комментарий → вход manager → close с причиной → reopen. Две вкладки
одной карточки показывают конфликт устаревшей версии409. Ctrl+C выключает сервер.
Аккаунт отключаю `python -m commerceguard.access disable NAME` тем же окружением.

Этот stdlib HTTP adapter предназначен для локального обучения. Внешний bind/TLS,
production web server, backup/restore и нагрузочные гарантии ещё не реализовал.
Браузер не получает raw payload, DSN и файловые download routes.

## Как я веду этапы

Я написал **21/30 историй исходного backlog — 70% по количеству**. Это не процент
готовности к эксплуатации и не оценка часов. S0/S1/S2/S3 написаны, в S4 готово4/5.
Осталось **9историй**: CG-405 export, S5×5(эксплуатация), S6×3(демонстрация/передача).
Рабочее место уже выполняет основные сценарии; финальная поставка ещё впереди.

Я веду Scrum+Kanban, WIP1 и отдельные последовательные Draft PR. Пять новых срезов
публикую до перехода к следующему; PR сам по себе не означает Accepted/merge.
Точные ссылки и факты сохраняю в WORKLOG. Main пока содержит навигацию, текущий
полный код — в source branch выше. Автоматический merge и stable release не делаю.
Ежедневные мини-проекты веду отдельно. В [PUBLIC_FILES](PUBLIC_FILES.txt) перечислены
только разрешённые исходники, без raw, БД, окружений, токенов и личных файлов.


## Мои пять последовательных срезов 26.10.2026

| История | Что я поставил | Review |
| --- | --- | --- |
| CG-305 | Каталог9SQL views, grain/key/currency/time/lineage | [DraftPR#34](https://github.com/Decl1s/commerceguard/pull/34) |
| CG-401 | Очередь/карточка/evidence, filters/keyset/empty state | [DraftPR#36](https://github.com/Decl1s/commerceguard/pull/36) |
| CG-402 | Accounts/roles/scope/sessions/CSRF | [DraftPR#38](https://github.com/Decl1s/commerceguard/pull/38) |
| CG-403 | Assignment/comments/request/version/atomic audit | [DraftPR#40](https://github.com/Decl1s/commerceguard/pull/40) |
| CG-404 | Close/reopen/reason/history/сигнал пересмотра | [DraftPR#42](https://github.com/Decl1s/commerceguard/pull/42) |

Я опубликовал137разрешённых исходников в отдельной source ветке
codex/s4-cg404-case-decisions. Следующий Ready — [CG-405#43](https://github.com/Decl1s/commerceguard/issues/43).
Merge/Accepted/stable release не выполняю; CI отдельно от локальных проверок.
