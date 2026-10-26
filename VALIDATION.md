# Фактические проверки CommerceGuard

## 26.10.2026 — CG-304: я проверил source health

Я использовал CPython3.12.15/PostgreSQL16.15/Psycopg3.3.6, прежние dbt/Prefect версии.
Analytics lock теперь62distributions с tzdata2026.5/IANA2026e; orchestration107версий
сохранил. Все hashes проверены, uv pip check в обеих средах завершился успешно.

| Проверка | Фактический результат |
| --- | --- |
| Unit analytics | 53 tests, OK, без skip;15 новых health tests |
| Unit orchestration | Те же53tests, OK, без skip |
| compileall | commerceguard/scripts/tests без ошибок, включая metadata dev14 |
| Exact age boundary | threshold60seconds fresh, +1microsecond stale |
| Completeness | no_data отличается от OMS complete_zero, PSP empty_unproven, incomplete advice/missing membership |
| Last success/attempt | Последующая failure не убрала прежний success; duplicate не продвинул observed watermark |
| Backfill | Последний delivered OMS стал новым, observed максимум остался прежним, late_delivery=true |
| Historical diagnosis | Started до cutoff/finished после: state started_at_boundary, error_code/finished_at скрыты |
| Timezone | Wheel tzdata2026.5/IANA2026e, Moscow next date, New_York fallback fold0/1 |
| Guards | Invalid timezone/version/threshold/history limit и future cutoff отвергнуты |
| Read-only | Counts пяти ingest/core/ops таблиц до/после health не изменились; REPEATABLE READ READ ONLY |
| Incomplete OMS | Parser отказал до attempt registration; journal_status not_registered, фиктивной записи health не создал |
| Settlement journal | Last attempt NULL, supported=false; не приписал выписке PSP attempt |
| CLI health |3источника, pinned timezone metadata, database_actions=read_only, JSON round-trip успешен |
| Core integration | Exit0: migrations1…9/schema8→9,4order results,11settlement reports/9advice revisions до health fixtures,oldSHA unchanged |
| dbt |9models/19data tests PASS28/WARN0/ERROR0/SKIP0; старый fanout10500/100/NULL/prepared exclusion прошёл |
| Prefect integration | Exit0: normal/exact replay/partial failure/preflight/injected retry2/3/marts failure/CLI resume, прежний resultSHA |
| Cleanup | Оба runner остановили/удалили собственные temporary PG; Prefect backend остановлен после команд |

В health helper я создавал/менял только собственные synthetic fixtures и отдельную
контролируемую journal attempt. DATABASE_UNCONFIRMED там — записанный тестовый диагноз,
не реальный обрыв COMMIT. Заявление read-only относится к source_health, а не к
подготовке тестовых данных. Business формулы/опубликованные migrations не менял.
После успешных integration менял документы и metadata версии, функциональный код
не менял. Минимальный прежний postgres-only lock в этом срезе не устанавливал.

Реальная ошибка разработки: первый unit ожидал UTC строку без .000000, но текущий
canonical_time стабильно пишет шесть знаков. Я исправил ожидание fixture, контракт
не ослаблял. До integration явно нормализовал typed datetimes в UTC, чтобы fold
локальной зоны не определял сортировку/арифметику. Это решение по контракту,
не выдуманный найденный production incident. Оба первых integration прогона прошли.

Не проверял CI/Windows/нагрузку/EXPLAIN/real concurrency/power loss/backup restore
и полный legacy Case-policy upgrade. Marker cutoff не реконструирует исторический
MVCC snapshot; freshness MAX не доказывает покрытие внешнего источника. Нет health
history journal, source-specific SLA справочника, notifier или автоматического gate
в Prefect. У settlement нет attempt journal, pre-registration failures в ingest
журнале отсутствуют. Общие пороги/эти ограничения я явно описал в FRESHNESS.

## 26.10.2026 — CG-303: я проверил Prefect flow и продолжение после отказа

Я использовал CPython3.12.15 и два отдельных lock: analytics61 distributions,
orchestration107 distributions. Prefect3.8.8/FastAPI0.154.0/Psycopg3.3.6; PostgreSQL16.15.

| Проверка | Наблюдённый результат |
| --- | --- |
| Установка orchestration lock | 107 distributions, hashes проверены uv0.13.1; отдельная .venv-orchestration |
| uv pip check | Все107 установленных пакетов совместимы по metadata |
| Unit tests в analytics .venv | 38 tests, OK, без skip |
| Unit tests в orchestration .venv | 38 tests, OK, без skip |
| compileall | commerceguard/tests/scripts завершились без ошибок |
| Full pipeline | 7stages Completed,5balances/5findings,9dbt models/19tests,6canonical PSP facts |
| Exact timestamp replay | Те же run_id/SHA, duplicate batches/result,1business result в БД |
| Partial failure | Новый OMS сохранился (2snapshots), PSP conflict дал Failed/attempt1; cutoff/prepare/execute/marts не выполнялись |
| Preflight rejection | Повреждённые bytes отвергнуты до обоих publish;1attempt,0completed stages |
| Transient injection | Я инъецировал один MERCHANT_BUSY: OMS выполнился со второй попытки |
| Retry limit injection | Постоянный busy остановился после3attempts; следующий этап не начат |
| Marts failure injection | Настоящий Prefect flow получил Failed; сохранённый result SHA не изменился; marts не ретраился |
| CLI resume | Я продолжил прежний run_id без ingest/prepare, получил Completed/duplicate_result и прежний SHA; mart содержит1published run |
| Cleanup | Worker сообщил backend_stopped=true на normal/replay/failure/resume; test fault backend также stop в finally; runner остановил/удалил свой PG |
| Прежний core integration | Снова прошёл: migrations1…9/schema8→9,4published order runs,11settlement reports/9advice revisions,oldSHA unchanged |
| Прежний dbt build | PASS28/WARN0/ERROR0/SKIP0:9views+19data tests; fanout10500/100,currency/NULL,prepared exclusion |

Команды воспроизведения — README/ORCHESTRATION. Новый runner выполняю orchestration
Python, старый — analytics Python. Оба используют только свою temporary PG безTCP;
Prefect открывает временный127.0.0.1 backend, Cloud не требуется. Сетевой аудит всех
зависимостей, SIGKILL/power loss, конкурентных writers и Windows не выполнял.
Инъекция retry — управляемая ошибка адаптера в тесте, не реальная конкурентная
сессия SQL lock. Последний программный срез прошёл обе проверки; после этого
менял только документы/metadata. Опубликованные migrations1…9 не менял.

### Мои реальные ошибки разработки CG-303

Первый lock разрешил FastAPI0.162.0. Импорт API Prefect упал с TypeError на
Body(min_items); я сверил release notes0.155 и закрепил FastAPI0.154.0. Первый
build adapter использовал неверный --no-anonymous-usage-stats: dbtRunner отказал,
flow стал Failed после сохранённого result. Исправил на --no-send-anonymous-usage-stats.
В новом тестовом runner исправил название таблицы core_order_snapshot на реальное
core_oms_snapshot; ошибка была в assert запроса, нормальный flow уже завершился.
При вставке CLI исправил синтаксическую опечатку elf→elif, найденную compileall.
Прямой ранний импорт Prefect также показал недоступный default home; production
worker задаёт private home/profiles ДО импорта. Vendor source не патчил.

Sandbox заблокировал локальные sockets при первом запуске PostgreSQL; я повторил
разрешённый собственный runner вне этого ограничения. Это не ошибка DDL/финансов.
После исправлений весь check_pipeline завершился exit0, затем старый check_postgres
завершился exit0. Не выдаю ранние неуспешные прогоны за успешные.

### Что я оставил непроверенным или не реализовал

CI/Windows, нагрузки, concurrency/fault/power loss, backup/restore и полный legacy
Case policy upgrade остаются прежними пробелами. Нет durable pipeline journal,
schedule/worker deployment, бизнес-HTTP/RBAC, atomic swap всех views и автоматического
retry произвольного COMMIT unknown. Resume требует существующий run_id и совместимый
engine; checksum/временные границы не обходятся. Сложные DSN service/multi-host/options
пока отвергаю до ingest. Полноту внешнего PSP источника Prefect сам не доказывает.

## 26.10.2026 — CG-302: я проверил перечисление и обновление схемы

Я использовал прежнюю .venv Python3.12.15 и analytics lock с61 distributions.
Денежный код проверил на synthetic примерах в собственном PostgreSQL16.15 без TCP.

| Проверка | Фактический результат |
| --- | --- |
| Python unit tests | 27 tests, OK, без skip; 12 новых settlement tests и15 прежних; повтор после metadata версии также OK |
| compileall commerceguard/tests/scripts | Завершился без ошибок в финальном checkout |
| Strict advice | Float/bool/повтор ID/JSON key/лишнее поле отвергнуты; canonical повтор равен |
| Денежный контракт | Gross36000/refund1000/fee720/net34280; independent tariff201→fee724; half-up/negative net допустимы |
| Migration8→9 | Я сначала создал заполненную schema8, сохранил четыре result SHA, затем применил только0009; повтор noop, теперь24 persistent tables |
| Старые результаты | После upgrade и settlement сценариев SHA прежних run неизменны |
| Settlement публикация | 9 advice revisions; replay noop; conflict revision/assignment/семейства не добавил частичную выписку |
| Settlement отчёты | 11 reports; matched, fee overcharge80, incomplete/member missing/currency/period unknown, complete zero, negative net |
| Late PSP | Старый unknown/NULL сохранён, exact retry его вернул; новый cutoff получил matched36100/1000/722/34378 |
| Append-only | UPDATE advice/result отвергнут PostgreSQL SQLSTATE55000 |
| CLI/viewer | Result round-trip matched; limit1 обрезал evidence с явным флагом |
| dbt Core/PostgreSQL | 9 view models +19 data tests, PASS28/WARN0/ERROR0/SKIP0 |
| SQL старого контура | O1001 capture10500/refund100; USD/blocked=NULL; prepared run исключён,4published run вошли |
| Новый mart | Число строк равно11 reports; unknown expected gross/net остались NULL |
| Очистка | Runner завершился exit0, в finally остановил свой сервер и удалил временный cluster |

Команды: `.venv/bin/python -m unittest discover -s tests -v` и
`.venv/bin/python scripts/check_postgres.py --pg-bin /usr/lib/postgresql/16/bin`.
Runner использует временный mock загрузчика только для подготовки старой schema8,
затем настоящий полный набор migrations для upgrade. К чужой БД не подключался.
Это проверка реального перехода8→9 на данных текущего runner, не доказательство
совместимости всех исторических Case policy/произвольных пользовательских баз.

В разработке я заметил, что aggregate10^16 не помещается в прежний integer token16.
Я добавил явный parser предел18 для settlement, сохранил default16 OMS/PSP и
проверил оба контракта регрессией. Не выдаю это за наблюдённый production сбой.
Новых зависимостей не устанавливал. После успешного integration менял только
документацию и metadata версии dev12; денежный код/SQL не менял.

Пробелы: я не запускал CI/Windows/concurrent writers/power loss/backup restore,
не реализовал reassign/void advice, тарифный справочник, отдельный settlement
attempt journal или автоматическое обнаружение standalone raw advice при recovery.
Отсутствие receipt — unknown, но согласованно заниженное внешним провайдером
expected_event_count само по себе независимая проверка не обнаружит. Bank ledger,
FX/chargeback/минимальная fee/T+N вне текущей модели. Review не означает приёмку.

## 25.10.2026 — CG-301, я включил исполнение

Я сменил прежний режим отдельным решением. Ниже — факты текущего checkout;
старый журнал в конце сохраняю как историю, а не действующий запрет.

| Проверка | Наблюдённый результат |
| --- | --- |
| Python 3.12.15, `unittest discover -s tests -v` | 15 tests, OK, без skip на Linux |
| compileall commerceguard/tests/scripts | Завершился без ошибок |
| CLI demo | 5 balances, 4 findings, дедупликация 1, невидимое событие 1; JSON сроков сериализуется |
| Установка analytics lock | uv 0.13.1: 61 пакет с проверкой hashes в собственной .venv; dbt-core-experimental-parser 2.0.8 собрался из sdist |
| Миграции PostgreSQL 16.15 | 0001…0008 применены к пустой одноразовой БД; повтор migrate — noop; 20 persistent tables |
| Полный приём | 5 OMS / 7 PSP records; повтор пакета возвращает duplicate_batch |
| Run | prepare/execute replay без второго result, result/evidence читаются |
| Поздние данные | corrective run убирает одну недоплату; один newly visible event; SHA исходного отчёта неизменен |
| Case | apply repeat noop; corrective apply отклонён report-only; old retry не откатывает head; show/history читаются |
| Whole-package ошибки | conflict, earlier-observed и invalid-json отвергнуты; количество canonical payment facts не изменилось |
| OMS v2 | Новый snapshot выбран, expectation_version=2, capture discrepancy отдельно от refund deadline |
| dbt Core 1.12.6 / dbt-postgres 1.11.0 | 8 view models + 13 data tests: PASS=21, WARN=0, ERROR=0, SKIP=0 |
| Финансовый JOIN | O1001: 3 capture events → 10500; 2 refunds → 100; повторная доставка не добавляет event |
| Валюты/неизвестность | USD finding сохранён при order_count=0; actual=NULL, blocked balance также NULL |
| Завершённость | 4 опубликованных run вошли в mart, отдельный prepared run исключён |
| Очистка | Каждый integration runner останавливает свой кластер в finally и удаляет временный каталог; исходный подготовительный кластер также остановлен |

Команды воспроизведения — README. Временный сервер я запускал только через Unix
socket внутри приватного каталога без TCP. Реальных данных/существующей БД нет.
В dbt отключил анонимную телеметрию. В target/logs остаются локальные артефакты,
в публикацию они не входят. CI не создавал и не выдаю локальный запуск за CI.

### Что я действительно исправил

При втором raw persist обнаружил TypeError: regular_file имеет keyword-only
artifact, а RawStore передавал его позиционно. Исправил оба вызова — в _verify
и resolve_manifest — и добавил регрессию raw repeat/resolve/corruption.
Первый unit-набор также выявил две ошибки самих тестов: tuple dataclass вместо
сохранённой JSON list и необработанный EOF guard контекстного менеджера. Я уточнил
fixtures/ожидание исключения; production проверки для прохождения тестов не ослаблял.
В integration runner исправил имя psp-late, прежде чем получить успешный прогон.

### Что пока не подтверждено

Я не выполнял Windows, нагрузку, конкурентных writers, аварийный COMMIT/power loss,
backup/restore, полный legacy-data upgrade, реальный v1→v2 Case stream upgrade,
выполнение исторического kernel, сетевые роли/CSRF, веб-интерфейс и CI.
Текущий integration покрывает v1/v2 INPUT в balance-v2, а не архив старых executors.
Fallback чтения result v1/v2 написан, но fixtures этого integration — result v3.
Проверки не означают production readiness или внешнюю приёмку Sprint 1/2.

## Исторический журнал до включения проверок

# Исполнение и ограничения

24.10.2026. Я веду текущий этап без запуска приложения и проверок.

| Действие | Факт |
| --- | --- |
| Написание исходников и документов | S0, S1/CG-101 (схема) CG-102 (manifest/parser) и CG-103 (raw/COPY/publish) написаны |
| input inspect / CSV / JSONL parser | Не запускались; примеры входов не прогонялись |
| Запуск python -m commerceguard | Не выполнялся |
| Импорт/compileall/py_compile | Не выполнялись |
| Unit, integration, end-to-end, нагрузочные проверки | Не выполнялись; тестовые файлы не создавались |
| Линтер, formatter check, type checker | Не запускались |
| Установка зависимостей, pip install, сборка | Не выполнялись |
| SQL и migration runner | Написаны; сервер не подключался, схема не создавалась, SQL не применялся |
| Контейнеры, веб-сервер | Ещё не реализованы и не запускались |
| CI | Workflow не создавался; автоматический запуск проверок отключён отсутствием workflow |
| Windows/Linux работоспособность программы | Не подтверждена ни на одной ОС |
| Результаты demo в документах | Расчёт по контракту вручную, не наблюдавшийся stdout |
| Производственная готовность | Не заявляется |

Операции создания/чтения файлов, Git и публикации документов не исполняют предметный
код. Публичный состав контролируется отдельным явным списком; это защита от случайной
публикации домашней папки, а не свидетельство качества приложения.

Реальные ошибки исполнения неизвестны, потому что исполнения не было. Не придумываю
успешные прогоны, замеры, покрытие, найденные баги или сравнения производительности.
Продолжаю поэтапное написание в этом режиме до отдельного решения о запуске.
Невыполненные проверки остаются в журнале риска; они не считаются «пройденными по умолчанию».

Сохранение в GitHub отражается в локальном журнале проекта отдельно от готовности
продукта. Эта итерация — публикация разработки, не стабильный релиз.

CG-101: constraints/FK/append-only, checksum/lock/rollback, отказ при чужой схеме
и сокрытие DSN предусмотрены исходниками. Исполнением не подтверждались.
Pins requirements-postgres.lock выбраны по метаданным официального реестра;
resolver, установка и импорт драйвера не выполнялись.

CG-102: написаны ограничения manifest/байтов/строк, временный снимок, raw/semantic
SHA, строгий JSON/CSV, номера записей, внутрипакетные повторы и полный EOF.
Ни один сценарий не выполнялся: hash mismatch, malformed UTF-8, malformed CSV/JSON,
NaN/повтор ключей, конфликт ID и ранний выход описаны как намерение кода.
Новых Python-зависимостей нет. Производительность и память не измерялись.

CG-103: постоянный raw, canonical manifest identity, temp staging/COPY, одна
транзакция публикации, PSP receipts и temporal conflict написаны, не исполнялись.
0002 не применялась. Отказ на legacy batches, hard link/fsync на Linux/Windows,
параллельные загрузки, replay и обрыв COMMIT не проверялись. Драйвер не установлен.
Административная публикация исходников/Git не является проверкой этих сценариев.

CG-104: я написал миграцию 0003, журнал попыток, классификацию ошибок, scan-raw и
recover. Ни schema SQL, COPY, запись журнала, повреждённый raw, неизвестный COMMIT,
терминальный trigger, Ctrl+C, конкуренцию, обзор или replay не исполнял. Новых
успешных проверок не заявляю. Административная сверка GitHub не проверяет приложение.

CG-105: я написал генератор baseline/invalid-json/conflict/earlier-observed,
отдельный late PSP и read-only status. Не генерировал входные файлы, не выполнял
CLI, не подключал БД, не прогонял ожидаемые количества или ошибки. Команды в
WORKBENCH и примеры чисел — инструкция и ручная спецификация, не результаты запуска.

CG-201: я написал 0004, selector опубликованных входов, canonical run manifest,
engine fingerprint и CLI prepare/show. Не выполнял SQL, read/write, timestamps,
ambiguous/missing OMS, отсутствующий PSP, предел входов, locks и replay. Fingerprint
приложения не вычислял вызовом его кода. Это планирование/исходники, не результат сверки.

CG-202: я написал 0005 и run execution/result/evidence. Не исполнял kernel через
БД, JSON round-trip, FK, counts, memory caps, lost COMMIT, concurrency, repeat или
просмотр evidence. Результаты в RESULTS — ручной ориентир, не наблюдённый stdout.
ОС, скорость и память не измерял. Исходники остаются unverified.

CG-203: я написал 0006, case projection/store и apply/list/show. Не выполнял
SQL, FK/триггеры, strict finding parse, canonical ordering, replay, concurrency,
lost COMMIT, размерные границы, пагинацию или CLI. Рассуждения в CASES — спецификация,
не наблюдённый результат. Административная публикация не проверяет приложение.

CG-204: я написал 0007, temporal contract v2, baseline/reason, раздельные границы
kernel и read-only changes/evidence visibility. Не выполнял миграцию, имена checks,
baseline FK, выбор позднего OMS/PSP, kernel, SHA migration, сравнение историй,
receipt visibility, размерные/временные границы или CLI. Числа и переходы LATE_DATA —
ожидаемая спецификация. Административные Git/публикация не доказывают корректность.

CG-205: я написал 0008, OMS v2, совместимое чтение v1, per-leg deadlines/states,
manifest/result v3, версию membership, flags сравнения и явный Case policy upgrade.
Я не выполнял parser/generator/demo, импорт, SQL/constraints/FK, сериализацию,
semantic hashes вызовом приложения, migration/replay, concurrency, CLI, проверки
или CI. Реальных ошибок исполнения и подтверждённых ОС нет. Числа и переходы
DEADLINES — спецификация вручную. Административная сверка разрешённых GitHub
файлов и их SHA относится только к факту публикации, не корректности кода.
S2 остаётся Review/unverified; stable release и приёмку не объявляю.

## Публикация CG-302

Я сохранил проверенные исходники в Draft PR#28 поверх CG-301#26. Это source
публикация, не выполненный CI, merge или stable release. Issue#27 — Review,
CG-303#29 — Ready. Фактический удалённый состав проверяю по106allowlisted blob SHA;
remote/local история различается, force push не использую.

## Публикация CG-303

Я сохранил исходники в [Draft PR#30](https://github.com/Decl1s/commerceguard/pull/30)
поверх CG-302#28, issue#29 — Review, CG-304#31 — Ready. Публикую115allowlisted
файлов без внутренних рабочих инструкций. Main обновляю только как навигацию.
Локальные проверки отделяю от CI; workflow не добавлял, stable release/merge нет.

## Публикация CG-304

Я опубликовал [Draft PR#32](https://github.com/Decl1s/commerceguard/pull/32) поверх
CG-303#30. Issue#31 — Review, CG-305#33 — Ready. В явном составе120исходников,
рабочие инструкции/БД/raw/окружения/контакты исключены. Main — навигация, merge/
stable release не выполняю. Workflow не добавлял, локальные проверки не называю CI.


## 26.10.2026 · CG-305

Я завершил каталог девяти dbt views с зерном, ключами, валютой, временем, lineage и владельцем смысла.

Я прошёл59unit tests; catalog check подтвердил9моделей. Новых зависимостей, SQL-миграций и runtime подключений нет.
Материалы: [CATALOG](docs/CATALOG.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-401.


## 26.10.2026 · CG-401

Я добавил локальную read-only очередь, фильтры, keyset pagination, карточку с историей и evidence.

Я прошёл65unit и core/HTTP integration наPG16.15: filters, empty state, head409, Host/cross-site guards, финансовые SHA неизменны;dbtPASS28.
Материалы: [WORKPLACE](docs/WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-402.


## 26.10.2026 · CG-402

Я добавил локальные аккаунты, роли и merchant scopes, серверные сессии, CSRF и отзыв доступа.

Я прошёл70unit и PostgreSQL/HTTP integration: schema8→10 на данных, login/logout/disable, role/scope denial, Origin/CSRF, challenge replay, account throttle;dbtPASS28.
Материалы: [WORKPLACE](docs/WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-403.


## 26.10.2026 · CG-403

Я добавил назначения, комментарии, workflow version и атомарный append-only аудит человеческих действий.

Я прошёл75unit и PG/HTTP integration: schema8→11, exact replay, changed-request409, настоящий конфликт двух соединений, rollback между UPDATE/audit, deferred guard и stored-XSS escape;dbtPASS28.
Материалы: [WORKPLACE](docs/WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-404.


## 26.10.2026 · CG-404

Я завершил close/reopen с обязательной причиной, сохранением истории и сигналом пересмотра нового расхождения по закрытой карточке.

Я прошёл79unit; core/HTTP integration подтвердил schema8→12 с данными, два concurrent соединения, atomic audit rollback, replay/CSRF/scope/roles, настоящие disappearance/reappearance и прежниеSHA;dbt9models/19testsPASS28. Prefect normal/replay/retry/failure/resume прошёл отдельно.
Материалы: [WORKPLACE](docs/WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-405.


## Итог пяти срезов · фактическая область проверки

Я прошёл 79 unit tests в analytics и orchestration окружениях, compileall для
commerceguard/scripts/tests, uv pip check (62/107 distributions) и catalog check
для девяти моделей. Финальный core runner завершился с exit0: PostgreSQL 16.15,
upgrade заполненной схемы8→12, 28 persistent tables, 9 dbt views и 19 data tests
(PASS28). Четыре прежних order results и 11 settlement reports относятся к checkpoint
до workflow fixtures. Затем я добавил ещё два настоящих order runs для проверки
исчезновения и повторного появления расхождения. Старые SHA сохранились.

HTTP я проверил через http.client на loopback. Полноценную визуальную и браузерную
матрицу не выполнял. Отдельный Prefect runner завершился с exit0 на schema12:
normal, exact replay, partial OMS success/PSP failure, preflight rejection, retry2/3,
marts failure, CLI resume и прежний SHA. Временные PostgreSQL, HTTP и Prefect backend
остановил; каталоги временных данных удалены runner в finally.

Я подтвердил настоящую гонку двух соединений Case, отказ устаревшей версии,
exact request replay, отказ изменённого тела под прежним request_id, откат после
внедрённого сбоя INSERT audit и запрет прямого изменения version без аудита.
Проверил login/logout/disable, role/scope/CSRF/Origin, повтор login challenge,
блокировку после неверных паролей и экранирование сохранённого HTML. Close/reopen
с обязательной причиной проверил через service и HTTP. Новые OMS snapshots,
run execution и Case projection сохранили закрытое решение и историю после
исчезновения/возвращения finding; в очереди появился сигнал пересмотра.

Я не заявляю CI, Windows, нагрузочные гарантии, полную concurrency/power-loss/
backup-restore матрицу, внешний TLS deployment, production HTTP server,
автоматическую приёмку или stable release. Первый CG-404 runner отказал из-за
константы10500 в fixture после добавленных settlement PSP events. Я исправил
синтетический сценарий и повторил полный runner успешно. Ошибки quoting SQL и
скобки HTML поймал compileall и исправил до публикации. Байты kernel/projector
и опубликованные миграции0001…0011 не менял. Публикую только137 разрешённых UTF-8
исходников: без AGENTS, raw, БД, DSN, env, контактов и локальных окружений.


## 26.10.2026 · CG-405

Я добавил согласованный CSV выбранной очереди с одной валютой, версиями и моментом среза.

Я прошёл84unit и PostgreSQL/HTTP/dbt integration: export filters, scope, canonical run, SHA и запрет смешения валют;dbtPASS28.
Материалы: [EXPORT](docs/EXPORT.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-501.


## CG-501 · завершение первой версии

Я реализовал календарный план, закрепление run IDs и bounded resume с отдельным состоянием job.

Я прошёл89unit и PG/dbt/HTTP integration; остановка backfill и повтор сохранили run identity, completed retry не создал новый результат.
Материал: [BACKFILL](docs/BACKFILL.md). Следующий CG-502.


## CG-502 · завершение первой версии

Я добавил согласованный DB+raw backup, проверку повреждений и восстановление в пустую БД с server receipt и finish-restore.

Я прошёл89unit и полный PG/HTTP/dbt runner: реальный restore в другой кластер/owner, old SHA/Case/audit comparison, session revocation, tampering/nonempty denial и остановка после DB COMMIT.
Материал: [BACKUP](docs/BACKUP.md). Следующий CG-503.


## CG-503 · завершение первой версии

Я добавил live/readiness, scoped метрики, безопасные JSON события и X-Request-ID.

Я прошёл92unit и PG/HTTP/dbt/restore integration; health/metrics authorization и плохой Host POST проверены фактически.
Материал: [OPERATIONS](docs/OPERATIONS.md). Следующий CG-504.


## CG-504 · завершение первой версии

Я добавил проверенную Compose поставку с Waitress/Caddy, private backend, runtime SQL правами, независимыми tools venv и управлением аккаунтами.

Я прошёл96unit в трёх средах и реальный Compose scenario: fresh install, full Prefect/dbt, pg_dump/verify, UI decisions/export, SQL denial,40requests/concurrency4 за0.393с, restart/session/volume persistence. Я ограничиваю подтверждение Linuxx86_64.
Материал: [DEPLOYMENT](docs/DEPLOYMENT.md). Следующий CG-505.


## CG-505 · завершение первой версии

Я измерил реальный план очереди на2000Case и заменил полную загрузку health history на bounded SQL summaries.

Я прошёл97unit и полный PG15migrations/core/HTTP/dbt/restore runner. EXPLAIN дал50строк,planning0.211мс/execution0.056мс; старые health semantics/SHA сохранены, искусственно планировщик не ограничивал.
Материал: [PERFORMANCE](docs/PERFORMANCE.md). Следующий CG-601.
