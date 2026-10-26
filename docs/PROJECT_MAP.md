# Моя карта CommerceGuard: где, что и зачем

27.10.2026: я завершил функциональный объём30историй. Текущий release gate — RELEASE_CHECKLIST; актуальная карта изменений и эксплуатации — HANDBOOK. Исторические разделы ранних срезов ниже сохраняю.
Это навигация по исходникам, а не подтверждение их корректности.

## Как я связываю бизнес-вопрос и код

Я хочу объяснить недостачу по заказу, а затем сохранить историю её разбора.
Для этого мне нужны три разные идентичности: **пакет** отвечает за принятый вход,
**run** — за точный отчёт, **case** — за проблему, которая живёт дольше отчёта.
Повтор доставки не должен создавать второй business fact; повтор расчёта не должен
перезаписывать старый result; новая сумма не должна создавать несвязанную карточку.
Я провожу эти правила через отдельные модули, а не через один большой CLI handler.

| Вопрос | Куда я иду первым | Подробное объяснение |
| --- | --- | --- |
| Зачем магазину этот продукт? | PRD.md и README | Бизнес-сценарий, роли, ограничения |
| Почему не вычесть refund из capture? | domain.py → reconcile.py | DATA_CONTRACTS, NOTES |
| Почему CSV отклонён? | file_contracts.py → file_inputs.py | INPUTS |
| Где исходный файл и его SHA? | raw_store.py | INGESTION, RECOVERY |
| Почему повтор не дублирует event? | ingestion.py → 0002 SQL | INGESTION |
| Какие данные вошли в отчёт? | run_plans.py | RUN_MANIFEST |
| Откуда взялась сумма? | run_execution.py | RESULTS, run evidence |
| Что изменилось после поздней оплаты? | run_changes.py | LATE_DATA |
| Почему оплата просрочена, а возврат pending? | domain/reconcile | DEADLINES |
| Почему это тот же case? | case_projection.py → case_store.py | CASES |
| На каком этапе разработка? | PROGRESS → KANBAN → WORKLOG | S2.md, BACKLOG |

## Какие модули я написал

| Файл в commerceguard/ | Его ответственность | Почему держу отдельно |
| --- | --- | --- |
| `__init__.py` | Версия черновика | Импорт пакета не должен открывать соединение |
| `__main__.py` | Параметры команд и JSON представление | Формулы и транзакции оставляю за пределами CLI |
| `domain.py` | Неизменяемые входы/результаты, Rule, money/currency/time constraints | Доменные типы использую без драйвера и HTTP |
| `reconcile.py` | Видимость, дедупликация, balances и findings | Чистая функция не читает часы/файлы/БД |
| `demo.py` | Один фиксированный пример в памяти | Бизнес-смысл могу прочитать без инфраструктуры |
| `file_contracts.py` | OMS v1/v2, PSP v1, временной и semantic контракт | Один смысл поля для parser и приёма |
| `file_inputs.py` | Frozen input, hashes, один проход, ordinal/physical rows и полный EOF | Изменение исходного файла во время чтения не должно дать смесь версий |
| `raw_store.py` | Собственное immutable raw-хранилище и discovery | File/object identity отделяю от DB COMMIT |
| `postgres.py` | Ленивое подключение, параметры и безопасные ошибки | DSN и server DETAIL не отправляю в CLI |
| `migrations.py` | Ledger/checksums, lock схемы и применение pending SQL | Не использую auto-create как скрытый побочный эффект чтения |
| `ingestion.py` | Raw → stage COPY → contract/core/receipt → atomic publish | В одном месте определяю границу whole-package COMMIT |
| `ingest_journal.py` | Started/success/rejection и schema guard | Отказ записываю отдельно от откатываемых фактов |
| `recovery.py` | Сопоставление raw и metadata, повтор приёма | Recovery использует тот же publish, а не второй алгоритм загрузки |
| `ingest_status.py` | Read-only просмотр batch/attempt/manifest metadata | Диагностика не должна незаметно запускать recovery |
| `sample_data.py` | Воспроизводимые синтетические файлы и варианты отказа | Реальные выгрузки и персональные данные мне не нужны |
| `run_plans.py` | Выбор input IDs, два времени, fingerprint, request identity | Выбор latest делаю до вычисления и сохраняю |
| `run_execution.py` | Attempt, bounded snapshot, вызов kernel, immutable result/evidence | Транзакция результата отделена от времени вычисления Python |
| `run_changes.py` | Read-only сравнение correction с baseline | Сравнение сохранённых выводов не запускает kernel |
| `case_projection.py` | Snapshot finding, SHA и transition | Смысл detected/changed/absent/reappeared не зависит от SQL |
| `case_store.py` | Case stream, application ledger, heads/history и read API | Явная единая транзакция продвижения |

## Как я читаю SQL

Я начинаю с STORAGE, затем читаю миграции в порядке имени. Bootstrap проверяет
собственное приложение/схему. `stage_input.sql` относится к временной staging
таблице COPY, а не к ещё одной persistent витрине.

| Миграция | Что я добавил |
| --- | --- |
| 0001 | Identity/ledger, batch/raw/quarantine, OMS snapshot/expectation, PSP canonical event |
| 0002 | Canonical manifest identity, counts и все PSP receipts; legacy data не угадываю |
| 0003 | Ingest attempt history и защита terminal transitions |
| 0004 | Immutable run manifest и ordered input membership |
| 0005 | Run attempts, result JSON и relational evidence refs |
| 0006 | Case application/stream/head/revision/event |
| 0007 | Два времени, reason/baseline и новый result version; старые строки не переписываю |
| 0008 | OMS v2, version membership, manifest/result v3 и явный переход Case policy |

Я не редактирую опубликованную миграцию для исправления уже существующей БД.
Новое изменение оформляю следующим номером; ledger хранит SHA SQL. История
миграций — отдельный контракт от JSON input manifest и ruleset. Полный replay
исторического движка при любой новой схеме пока не обеспечен автоматически.

## Где я меняю проект под свою задачу

| Изменение | Какие границы я затрону | Что сначала объясню |
| --- | --- | --- |
| Другой источник CSV | INPUTS → file_contracts/inputs → staging/ingestion → новая миграция при нужде | Version, grain, EOF, ключ и смысл повторной строки |
| Новое денежное правило | DATA_CONTRACTS/ADR → Rule/reconcile → manifest/result compatibility | Отдельное плечо, null, deadline, stable rule code |
| Иная политика актуальных кейсов | CASES/ADR → case_store и additive SQL | Порядок run, область merchant, old retry, ручные решения |
| Назначение/комментарий/закрытие | Новый workflow contract S4 → event/permissions/UI | Actor, аудит, конкуренция и запрет стирать историю |
| Новый аналитический отчёт | Будущий S3 mart, не core UPDATE | Grain, currency, freshness и связь с immutable run |
| Больший объём | Лимиты Python + SQL + ADR | Где материализую данные и чем подтвержу скорость после разрешения запуска |

Я начинаю с одного сценария и явно меняю контракт. Не добавляю вычисления в
парсер CLI и не исправляю недостачу обновлением core_payment_event. Новый
интерфейс должен вызывать тот же application service; очередь/оркестратор
не должны становиться новым источником финансовой истины.

## Как я разбираю сбой по идентичности

Если не принят файл, я сохраняю manifest SHA/attempt ID и читаю RECOVERY.
Если не выполнен расчёт, смотрю run_id/attempt_id и RESULTS. Если результат
сохранён, но карточка не продвинулась, различаю run execute и case apply:
результат расчёта ещё не application в canonical stream. При unknown COMMIT
повторяю ту же identity. Я не лечу неопределённость удалением истории и новым UUID.

Важные границы: временная регрессия case не является сетевым retry; старый
engine mismatch не является повреждением raw; report-only correction не
означает, что исторический результат не сохранился. Фиксированные error codes
помогают разделить причины без вывода исходных строк/DSN.

## Как я изучаю проект руками, пока без исполнения

1. Я выбираю один заказ и отмечаю expected capture/refund, его deadline, occurred
   и observed событий. По reconcile вывожу ожидаемое finding. Суммы обеих валют
   никогда не складываю в один total.
2. Я выписываю цепочку raw SHA → batch/row → canonical event/receipt → run input →
   result evidence → case revision. Объясняю каждый ключ и где он хранится.
3. Я прохожу сценарий R1 shortfall → R2 changed → R3 absent → R4 reappeared.
   По CASES отличаю last_seen, evaluated и revision run; старый retry остаётся noop.
4. Я прохожу T0/T1 из LATE_DATA и объясняю, почему поздний receipt не требует
   подмены observed_at. Отдельно ищу возможное изменение engine.
5. Я планирую свою небольшую правку по таблице выше: контракт, файл, новая версия,
   ограничения и документация. До отдельного решения о запуске не называю её проверенной.

Ожидаемые ответы на десять предметных задач есть в CASES/LATE_DATA. Команды для
будущего знакомства перечислены в WORKBENCH/RESULTS/CASES/LATE_DATA; я их не
выполнял. VS Code workspace открывает только этот репозиторий, без auto-run tasks.
Фактическое наличие редактора и открытие окна не следуют из наличия workspace.

## Как я веду разработку дальше

Я беру одну Ready историю, записываю контракт/решение, пишу ограниченный срез,
обновляю PROGRESS/WORKLOG и публикую Draft PR с конкретным base. Затем беру
следующую зависимую историю, сохраняя unverified статус. Accepted и производственную
готовность не вывожу из числа файлов или коммитов. CG-305 — следующий pull;
мини-проекты и их ежедневная автоматизация остаются отдельной серией.

## Расширение карты CG-205

Я сохраняю исходный путь raw/core/run/case. Новые поля проходят через
file_contracts → file_inputs → stage_input → ingestion → 0008/core → run_execution.
Смысл отдельных deadlines определяю в domain/reconcile; версии входов закрепляю
в run_plans. Для старого v1 я адаптирую общий срок в памяти, не переписываю raw.
Case policy upgrade меняю в case_store и 0008, а не в case_projection: ключ
проблемы и шесть кодов rules остались прежними. DEADLINES объясняет эту границу.

## Новый слой CG-301

Я добавил analytics/dbt_project.yml и profiles.yml (только env vars), models/staging
для completed runs/balances/events/findings, intermediate для двух pre-aggregates,
marts для order и currency. Зерно каждого узла объяснил в MARTS.
В analytics/tests живут SQL data tests, в tests/test_contracts.py — unit-регрессии,
в scripts/check_postgres.py — собственный lifecycle временного PostgreSQL и полный
synthetic сценарий. requirements-analytics.in/lock закрепляют 61 dependency с hashes.
Я не добавляю оркестратор и формулы в CLI. Миграций по-прежнему восемь.

## CG-302: мой маршрут по перечислению

Я читаю SETTLEMENT рядом с settlement_contract.py (15 полей/identity), settlement.py
(completeness/формула), settlement_store.py (advice/run/result/evidence), 0009_settlement.sql
(4 новые таблицы) и mart_settlement_reconciliation.sql (зерно report_id).
Для нового тарифа меняю явную version policy и request identity, не CLI-арифметику.
Для другого формата провайдера добавляю adapter к advice, не угадываю event_ids.
Для исправления опубликованной выписки создаю revision, не UPDATE. В tests/test_settlement.py
держу чистые регрессии, в scripts/settlement_scenarios.py — DB сценарии main runner.
На этапе CG-302 я сохранил schema9/24tables/9views; Prefect тогда ещё не написал. Подробные задания — SETTLEMENT.

## CG-303: мой маршрут по оркестрации

Я читаю ORCHESTRATION → pipeline.py (snapshots/process/adapters) → pipeline_flow.py
(tasks/order/retry) → pipeline_worker.py (settings/backend lifetime) → pipeline_dbt.py
(отдельный analytics процесс). Новое business правило меняю в kernel, не в flow.
Новый transient добавляю только с доказанной идемпотентностью и проверкой retry.
Возобновление делаю по immutable run_id, не выбираю заново latest. В scripts/check_pipeline.py
и pipeline_faults.py вижу реальные DB/Prefect сценарии. Prefect уже написан;
следующий слой — freshness, HTTP ещё впереди. Schema9/24tables/9views сохранена.

## CG-304: мой маршрут по свежести

Я читаю FRESHNESS → source_health.py (typed metadata/пороги/timezone/чистые правила)
→ source_health_store.py (единый read-only snapshot) → freshness_scenarios.py.
Новый источник требует явного контракта полноты и timestamp semantics; я не копирую
значение is_complete OMS на PSP. Для другого SLA меняю явный параметр, не часы run.
Timezone читаю из pinned tzdata wheel. Новых таблиц/миграций/dbt views нет; live
операционный view не подменяет сохранённый financial report. Следующий — catalog.


## 26.10.2026 · моя карта рабочего места, актуальный dev19

| Где я меняю поведение | Файл | Что я сохраняю |
| --- | --- | --- |
| Смысл показателя | catalog.json/catalog.py | Grain, key, currency/time policy, ref/source lineage |
| Фильтры и курсор очереди | workbench_store.py | Bind parameters, bounded pages, head409, snapshot |
| Экран и формы | workbench.py | Escape, CSRF/Origin/Host, local-only и отсутствие формул денег |
| Учётная запись/роль/scope | access.py | Server-side identity, пароль getpass, session revocation |
| Назначение/комментарий/решение | case_workflow.py | Request identity, три ожидания, atomic update+audit |
| Web identity schema | 0010_workbench_access.sql | Три таблицы, сессии без plaintext auth token |
| Human workflow schema | 0011_case_human_audit.sql | Version/assignee, append-only human event, deferred audit guard |
| Close/reopen policy | 0012_case_decisions.sql | Manager/reason, preservation system presence, индекс очереди |
| Реальные web/DB сценарии | scripts/workbench_scenarios.py | Два соединения, replay, fault rollback, stale decision, reappearance |

Schema12:28persistent tables+9dbt views. Я не менял опубликованные0001…0011 и
байты kernel/projector. Полные команды/решения/упражнения — WORKPLACE иCATALOG.


## Как я нахожу новые модули первой версии

| Модуль | Для чего я его добавил |
| --- | --- |
| queue_export | Я фиксирую один snapshot и безопасный CSV |
| backfill | Я планирую1…31день, сохраняю run IDs и продолжаю после сбоя |
| backup | Я сохраняю DB+raw, проверяю hashes и завершаю restore по receipt |
| observability | Я ограничиваю JSON события/HTTP counters и отдаю health без секретов |
| server/runtime_role | Я запускаю Waitress и отделяю SQL права web от owner |
| deploy | Я устанавливаю контейнеры, генерирую secrets и передаю выбранные файлы |
| scripts/check_browser | Я проверяю настоящий Chrome в собственном Compose project |
| scripts/source_archive | Я проверяю allowlist и bytes каждого элемента архива |
| .github/workflows/validate | Я связываю unit/integration/security с отдельным release gate |

Я использую миграции0009settlement,0010accounts,0011workflow,0012human audit,0013backfill,0014restore receipt и0015indexes. Всего15миграций/31таблица+9dbt views. Новое изменение схемы начинаю с0016, прежние файлы не переписываю.
