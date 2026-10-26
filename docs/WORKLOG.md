# Фактический журнал разработки

## 24.10.2026 — S0

Я начал отдельный флагманский проект по дата-инженерии: реалистичный бизнес-сценарий,
Scrum/Kanban, важная документация и работа частями. Для текущего этапа выбрал
написание без исполнения и тестирования. Ежедневный sqlite-event-queue за ту же дату уже завершён;
CommerceGuard — отдельная длительная инициатива, не дубликат ежедневного проекта.

Я выбрал контур сверки OMS/PSP/settlement с будущим рабочим местом финансового специалиста.
Я прочитал применимые локальные инструкции и официальные материалы Scrum, Kanban,
Python 3.12 и PostgreSQL 16. Я сформулировал допущения, требования, дорожная карта,
истории и правила переходов. Я написал начальный kernel и синтетический CLI.

CG-001/002 переданы в Review как материалы, без утверждения о принятии или запуске.
Результаты исполнения отсутствуют; наблюдавшихся ошибок приложения нет, потому
что оно не запускалось. Я создал отдельный workspace IDE без автоматических задач.
Публикация GitHub, конкретные коммиты и Draft PR фиксируются в локальном журнале
передачи отдельно: удалённое сохранение не означает эксплуатационную готовность.

Я создал публичный Decl1s/commerceguard и опубликовал 35 разрешённых файлов в ветке
codex/sprint-0-foundation. Открыт Draft PR #1 к main; в main опубликована стартовая
страница с навигацией в текущую ветку. Созданы истории CG-001/002 и CG-101…105
и эпик дальнейших этапов; их ссылки собраны в KANBAN. Ни один бизнес-сценарий
пока не прошёл приёмку; я не сливал PR и не создавал stable release.

Я оставил ежедневные мини-проекты отдельной серией. Их расписание не менял;
CommerceGuard веду как самостоятельную инициативу без отдельного расписания.

Следующая история: CG-101. Не реализовывать остальные спринты в этом же заходе.
Не добавлять CI и не заимствовать обязательный прогон тестов из ежедневной серии.

## 24.10.2026 — S1, CG-101

Я продолжил S1 и добавил простую таблицу этапов docs/PROGRESS.md со ссылкой из README. Начат S1; выбран только первый срез,
не весь спринт. CG-001/002 остаются в Review без придуманной бизнес-приёмки.

Я написал SQL bootstrap и миграция 0001, восемь таблиц, ограничения/FK, три append-only
триггера и индексы под описанные фильтры. Физическая схема одна, commerceguard;
ingest/core — префиксы логических слоёв. Написан runner: отдельная БД PostgreSQL 16,
identity/owner, непрерывная checksum-история, transaction advisory lock, один COMMIT
для bootstrap/pending/ledger, отказ вместо downgrade/reset. CLI db status/migrate,
DSN только из внешней переменной, текст драйвера скрывается. Версия 0.1.0.dev1.

Я опционально закрепил Psycopg 3.3.6, psycopg-binary 3.3.6, typing_extensions 4.15.0,
tzdata 2026.2 (Windows), по официальным метаданным PyPI. Установка и resolver
не выполнялись. Demo по-прежнему не требует этого набора. ADR-13/14 объясняют
физическую схему и небольшой собственный migration runner.

Ни программа, ни импорт, SQL, миграции, тесты, линтер, сборка, контейнеры или CI
не исполнялись. В таблицах/исходниках нет пользовательских данных. CG-101 в Review,
unverified. Следующий pull — CG-102; в этом заходе он не реализуется.

Материалы CG-101 опубликованы в codex/s1-cg101-database-foundation, Draft PR #10
поверх ветки S0. Публичный manifest теперь содержит 42 текстовых исходника.
Таблица PROGRESS связана с PR; ни #5, ни S0 истории не закрываются автоматически.

## 24.10.2026 — S1, CG-102

Я продолжил приложение одним следующим срезом:
файловый контракт и parser, без COPY/публикации. Версия исходников 0.1.0.dev2.

Я написал file_contracts.py и file_inputs.py: один source/merchant на пакет,
строгий manifest, OMS CSV с точным header, PSP JSONL с точными ключами и int-суммами,
RFC3339 subset, ограничения 64000/100000000/1000000 байт и 10^6 записей.
Определены file/record/semantic SHA и canonical UTC microseconds. Дубликаты ключей
JSON, NaN/float, OMS key repeat и PSP semantic conflict должны отклоняться.
Равный повтор PSP остаётся raw record, но отдельно учитывается в duplicate_rows.

Временный фиксированный снимок связывает hash и parse с одним содержимым;
однопроходный open_input требует EOF до summary/нормального выхода. InputRecord
несёт logical ordinal, physical range, raw_text, два hash и объект domain.
Добавлена input inspect с метаданными вместо payload, без БД и постоянного raw.
Новых сторонних зависимостей нет. Подробные поля, семантика, ограничения и
официальные источники — INPUTS, ADR-15/16, SOURCES и TECHNOLOGIES.

Ни parser, ни inspect, demo, SQL, импорт, тесты, линтер, сборка или CI не выполнялись.
Временные файлы приложения не создавались, потому что приложение не запускалось.
Числа/примеры — спецификация, не наблюдавшийся результат. Ошибки исполнения неизвестны.
CG-102 в Review/unverified, CG-103 Ready. Таблица PROGRESS обновлена.
Глобальные повторы, temporal dedup и неизменяемый ранее опубликованный факт,
постоянный raw, staging и одна публикация остаются следующим CG-103.

CG-102 сохранён в codex/s1-cg102-file-contracts и Draft PR #11 поверх CG-101 #10.
Manifest публикации содержит 45 текстовых исходников; сами входы и временные файлы
туда не входят. В таблице PROGRESS сохранена ссылка на PR; приёмка не выдумывается.

## 24.10.2026 — S1, CG-103

Я написал следующий срез, версия 0.1.0.dev3. Постоянный raw
с маркером, content-addressed keys, эксклюзивным hard link и сверкой существующих
объектов; canonical manifest отдельно от исходных байтов. Identity batch включает
весь envelope, что допускает одинаковый OMS CSV в новом effective snapshot.
0002 сохраняет 0001, отказывает на непустом legacy ingest_batch, добавляет metadata,
счётчики и append-only receipts. Всего девять постоянных таблиц.

Я написал сервис публикации: shared migration lock, merchant try-lock, TEMP/COPY
write_row до EOF, полный replay, semantic/temporal conflict и одна транзакция
batch/raw/snapshot/events/receipts/published. Earlier observed_at старого события
отклоняется без UPDATE; равное/позднее поступление сохраняет provenance.
Подключение и safe SQLSTATE вынесены в postgres.py; CLI ingest publish — минимальная
граница среза, status/генератор остаются CG-105. Новых внешних зависимостей нет.

Обращение к официальным Python/Psycopg/PostgreSQL материалам не сопровождалось
исполнением. Приложение, SQL, импорт, COPY, тесты, сборка, линтер и CI не запускались.
Сбоев приложения не наблюдалось; rollback/fsync/concurrency не подтверждены.
Raw может остаться orphan; неизвестный исход COMMIT требует точного replay.
Карантин/recovery пока не написан, следующий CG-104. CG-103 Review/unverified;
предыдущие PR не слиты, истории не приняты автоматически.

CG-103 опубликован в codex/s1-cg103-atomic-ingestion, Draft PR #12 поверх CG-102 #11.
Публикация включает 51 текстовый файл PUBLIC_FILES; ни данные, ни raw, ни DSN
не входят в дерево. Навигация и карточки обновляются без закрытия/слияния историй.

## 24.10.2026 — авторский стиль материалов

Я перевёл описания, комментарии и журнал решений на первое лицо. Сохранил
технические факты, даты, ссылки и статус unverified. Приложение, SQL и проверки
на этом этапе не запускал; функциональный этап не менял.

## 24.10.2026 — S1, CG-104

Я написал миграцию 0003 и независимый ingest_attempt: started до COPY, success
с core, rejection отдельным best-effort COMMIT. Терминальную историю защищаю
trigger; ошибки классифицирую без payload, source IDs, DSN и абсолютных путей.
Whole-package quarantine не публикует валидный prefix. Raw scan ограничен и не
читает полный data hash; recover по manifest SHA проверяет все байты и вызывает
тот же publish, создавая новую попытку без новых фактов при replay.

Я добавил CLI scan-raw/recover и возврат безопасного attempt_id/journal status.
Недоступный журнал и preflight без identity описал как ограничения. Версия dev4,
новых библиотек нет. Приложение, импорт, SQL, COPY, проверки и CI не запускал.
Следующий последовательный срез — CG-105: status и синтетический генератор.

Я опубликовал CG-104 в codex/s1-cg104-quarantine-recovery, Draft PR #13 поверх #12.
В manifest 55 исходников, ни приложение, ни SQL не исполнял.

## 24.10.2026 — S1, CG-105

Я написал синтетический генератор и status по batch/attempt/manifest. Fixture
даёт 5 OMS, 7 основных PSP строк и 1 late PSP отдельно; добавил три варианта отказа.
Генератор не заменяет существующий каталог. Status читает явные metadata без
payload одним read-only snapshot, ограничивает историю и различает not_found.
Я описал маршрут в WORKBENCH, решения ADR-21, задания и обзор написанного S1.
Версия dev5, новых библиотек/миграций нет. Приложение, генерацию, SQL и проверки
не запускал. S1 в Review/unverified; следующим последовательно беру S2/CG-201.

Я опубликовал CG-105 в codex/s1-cg105-input-workbench, Draft PR #14 поверх #13.
В manifest 58 исходников. S1 написан без исполнения; следующим беру CG-201.

## 24.10.2026 — S2, CG-201

Я начал S2 с immutable run manifest и входов: миграция 0004, run_plans.py,
prepare/show, selector published OMS/PSP, cutoff и balance-v1/source fingerprint.
Детерминированный ключ и полный canonical текст дают replay. Missing/ambiguous OMS,
отсутствующий PSP, будущий cutoff и превышение input limit приводят к отказу.
Я отделил manifest от lifecycle расчёта (следующий CG-202), сохранил только as-was v1
и явно описал границу published_at marker. Версия dev6, всего 12 постоянных таблиц,
новых сторонних зависимостей нет. Ни код, ни SQL, ни проверки не запускал.

Я опубликовал CG-201 в codex/s2-cg201-run-manifest, Draft PR #16 поверх #14.
В manifest 62 исходника. Расчёт ещё не выполняется; следующим беру CG-202.

## 24.10.2026 — S2, CG-202

Я написал 0005 и run_execution.py: проверяю immutable manifest/engine/input counts,
читаю receipt-bound PSP и выбранный OMS, вызываю kernel вне idle transaction,
публикую canonical JSON result и все raw evidence refs одним COMMIT. Независимые
попытки сохраняют started/success/duplicate/failed/unknown; потеря ответа не затирает
успех. Добавил read-only result/evidence CLI, bounded limits и ADR-23/RESULTS.
Версия dev7, 15 таблиц, новых библиотек нет. Код, SQL, CLI и проверки не запускал.
Следующий CG-203 — кейсы/ревизии и явный порядок применения канонических runs.

Я опубликовал CG-202 в codex/s2-cg202-results-evidence, Draft PR #18 поверх #16.
В manifest 65 исходников. Исходники и числа unverified; следующий CG-203.

## 25.10.2026 — S2, CG-203

Я написал пять таблиц проекции, strict finding snapshot, явный case apply и bounded
list/show. Выбрал монотонный канонический поток и noop повторного применения.
Карточку отделил от immutable revisions/events; presence не закрывает workflow.
Дополнил CASES картой файлов, аргументами, обоснованием, примерами и упражнениями.
При написании убрал лишнее промежуточное создание snapshot; исполнения это не заменяет.
Версия dev8, новых зависимостей нет. Приложение, SQL и проверки не запускал.
Следующий CG-204 — поздние факты и два режима времени.

Я опубликовал CG-203 в Draft PR #20 поверх #18: 69 разрешённых файлов.
Карточку #19 перевёл в Review, CG-204 #21 подготовил в Ready. Исполнение не проводил.

## 25.10.2026 — S2, CG-204

Я написал manifest/result v2 с раздельными временами, reason/baseline lineage,
новый selection OMS/PSP, kernel visibility и read-only run changes. Evidence
показывает occurred/observed/visible. Разницу engine/visibility выделяю отдельно.
Выбрал report-only для исторических corrections, текущие Case не продвигаю ими.
Добавил 0007, не изменял опубликованные миграции/строки. Версия dev9, новых библиотек
нет. LATE_DATA содержит подробное обоснование, параметры и пять упражнений.
Приложение, SQL и проверки не запускал. Следующий CG-205.

Я опубликовал CG-204 в codex/s2-cg204-late-data, Draft PR #22 поверх #20:
72 разрешённых файла. Карточка #21 — Review, следующий CG-205 #23 — Ready.
Приложение, SQL и проверки не исполнял.

Я переработал START_HERE/ARCHITECTURE и добавил PROJECT_MAP, чтобы текущие точки
входа не оставались на описании S0/CG-103. Обновил таблицу README и собрал актуальные
инструкции продолжения в AGENTS. Исторические ADR/WORKLOG сохранил.
Путь от raw до Case и выбор места для правки описал в единой карте.

## 25.10.2026 — S2, CG-205

Я написал OMS v2, два срока и per-leg states, сохранил explicit legacy v1 semantic
payload. Пронёс version/deadlines через parser/COPY/core/membership в manifest/result
v3 и balance-v2. Run changes отмечает смену правил. Переход существующего Case
stream требует точного head и записывает policy/upgrade source в application ledger.
Добавил 0008 без изменения 0001…0007, split-deadlines с двумя полными snapshots,
DEADLINES/ADR-26 с картой файлов, обоснованиями и пятью упражнениями. Dev10, schema8,
20 таблиц, новых зависимостей нет. Генератор, приложение, SQL и проверки не запускал.
CG-205 остаётся Review/unverified; весь S2 написан, но не принят. Следующий CG-301.

Я опубликовал CG-205 в [Draft PR #24](https://github.com/Decl1s/commerceguard/pull/24)
поверх #22: 75 разрешённых исходников. Карточка #23 — Review/unverified,
CG-301 #25 — Ready. Код, SQL и проверки не запускал; релиз/архив не создавал.

## 25.10.2026 — S3, CG-301, я включил проверки

Я снял запрет исполнения и обновил PROCESS/AGENTS/VALIDATION. Установил analytics
набор (61 pinned dependency/hashes) в локальную .venv: Python3.12.15, dbt Core1.12.6,
dbt-postgres1.11.0, Psycopg3.3.6. PostgreSQL16.15 запускал временно без TCP.
Написал 8 views, ref DAG, 13 SQL data tests, 15 unit tests и integration runner.
Обнаружил raw regular_file positional/keyword-only TypeError, исправил оба вызова.
Уточнил две собственные unit fixtures и путь psp-late в runner, не ослаблял contract.

Unit15 OK; dbt PASS21 (8models+13tests); migration0001…0008/replay, ingest whole-package,
четыре reports, late correction, Case noop/history, fanout10500/100, USD/NULL и prepared
exclusion подтверждены. Runner останавливает/удаляет кластер; подготовительный также
остановил. Миграции не менял, schema8/20 tables. Версия dev11. CI/Windows/нагрузка/
legacy-data upgrade/аварийные COMMIT не проверены. Stable release/приёмку не объявляю.

Я обновил таблицу: 13из30 историй написаны (43% счёта задач), остаются17, до рабочего
места аналитика по плану9 историй S3/S4. Это не процент времени/качества. Следующий
CG-302, settlement/fee на уровне PSP batch. Мини-проекты и sources не менял.

Я опубликовал срез в Draft PR #26 поверх #24, ветка codex/s3-cg301-verified-marts.
В явном manifest 97 файлов; issue #25 — Review, CG-302 #27 — Ready.
Публикую только исходники, CI/релиз/слияние не выполняю.

## 26.10.2026 — S3, CG-302: я реализовал settlement и независимую комиссию

Я взял одну историю WIP1, отделил business settlement от ingest file. Написал
advice15fields/revision/canonical identity, exact membership и assignment против
двойного включения. Добавил независимый fee_bps/gross half-up, signed net,
unknown/NULL и completezero. Published receipt evidence/result immutable;
новый cutoff видит late fact, старый report не меняется. Case не применяю.

Я добавил migration0009 и4append-only таблицы без изменения0001…0008. Теперь
schema9/24tables. Новый mart на report_id расширил dbt до9views/19tests. Зависимости
сохранил (61 distribution в analytics lock), версияdev12. Прочитал PostgreSQL16
LATERAL/ON CONFLICT. Тариф gross-bps-half-up-v1 — моё явное учебное допущение.

Я выполнил27unit tests и полный одноразовый integration на PostgreSQL16.15:
schema8 с данными→9,4oldresultSHA unchanged,9advice/11reports, mismatch80,late/NULL,
zero/negative net,period/currency/revision/assignment,отказUPDATE55000. dbtPASS28,
WARN0/ERROR0/SKIP0. Сервер без TCP runner остановил и удалил. Денежный код/SQL после
успешного integration не менял; дополнил документы и metadata версии.
При разработке обнаружил несоответствие integer16 и агрегата10^16, ввёл отдельный
предел18 только для settlement и регрессию старого default. Это не production bug.

В SETTLEMENT написал подробный конспект, карту, формулы, аргументы, сбои/ограничения
и5упражнений с ответами. Обновил PROGRESS:14/30написано,16остаётся,8до рабочего места.
Следующий CG-303 Prefect; сейчас flow не написан. CI/Windows/fault/concurrency
не проверял, отдельного settlement attempt/reassign/GC нет. Публичный manifest106
файлов; publication фиксирую следующим фактом. Sources/daily проекты не менял.

Я опубликовал CG-302 в Draft PR#28 поверх #26, source branch codex/s3-cg302-settlement.
Issue#27 перевёл в Review, CG-303#29 создал Ready с критериями local flow/retry/failure.
В PUBLIC_FILES106 исходников, никаких raw/БД/окружений/контактов. Main обновляю только
как навигацию, исходники автоматически не сливаю. После публикации добавил ссылки
и metadata статуса отдельным docs commit, исполняемый код/SQL не менял.

## 26.10.2026 — S3, CG-303: я реализовал локальную оркестрацию

Я взял #29 WIP1 поверх CG-302#28. Написал pipeline run/resume, preflight frozen
input, последовательные Prefect tasks, cutoff после обоих ingest, expected-batch
membership guard и bounded retry только известных locks. Failed stage не запускает
следующие; partial OMS success сохраняю. Resume работает по immutable run_id.
БД — source of truth, Prefect cache/persist_result отключены. Case/settlement
автоматически не применяю, schema9/24tables/9views/миграции не менял.

Я закрепил Prefect3.8.8/FastAPI0.154.0/Psycopg3.3.6 и107distributions/hashes в
отдельной .venv-orchestration. Analytics61pins сохранил, dbtRunner вызываю другим
Python по тому же явному DSN. Private home/profiles/cwd до импорта Prefect,
Cloud URL/key не наследую, telemetry выключаю, loopback backend stop в finally.
Нет постоянной службы и durable flow journal. Dependencies/ADR-31…32/ORCHESTRATION
описывают решения, цену, ограничения и5заданий с ответами (конспект около1700слов).

Я прошёл38unit в обоих окружениях, compileall, uv pip check107. Новый PG16.15+Prefect
runner завершился exit0: полный pipeline/dbt9models19tests, точный replay,
partial OMS success/PSP conflict без downstream, preflight reject, injected lock
2attempts и предел3attempts, marts failure и CLI resume с прежним resultSHA.
В новой проверочной БД1result,6PSPfacts,2OMSsnapshots. Backend остановил/удалил.
Старый integration тоже exit0: schema8→9,4order results,11settlement reports,
9views/19testsPASS28,oldSHAunchanged. CI/Windows/realconcurrency/powerloss нет.

Реальные ошибки: Body(min_items) incompatibility FastAPI0.162→pin0.154, неверное
имя dbt flag исправил по CLI help, имя таблицы в test runner и elf→elif в CLI.
Вне sandbox проверил разрешённые локальные sockets. Детали сохраняю в VALIDATION.
После green проверки менял только документы и metadata версииdev13.
PROGRESS теперь15/30историй,15осталось/7до первого рабочего места; это не доля
времени/готовности. Следующий CG-304freshness. Manifest115исходников, публикацию
фиксирую после фактического создания PR. Sources/daily мини-проекты не менял.

Я исключил AGENTS.md из публичного дерева и списка, оставил его только локально:
автоматическая проверка отклонила публикацию рабочих инструкций. Исходники,
документацию и результаты проверок сохранил, приватные настройки не публикую.

Я опубликовал CG-303 в Draft PR#30 поверх #28, issue#29 перевёл в Review,
CG-304#31 создал Ready. В итоговом public tree только115allowlisted исходников,
AGENTS храню локально и не наследую в новое дерево. После проверки состава
зафиксирую точные remote/local/main heads в локальном FLAGSHIP.md.
Документы со ссылками сохраняю отдельным commit, исполняемый код/SQL не менял.

## 26.10.2026 — S3, CG-304: я реализовал свежесть и полноту источников

Я взял #31 WIP1 поверх CG-303#30. Написал source health для OMS/PSP/settlement:
observed/business/event watermarks, last publication/attempt/success, freshness,
completeness и volume отдельно. Полнота last_published_package не доказывает
покрытие всего источника. Backfill/duplicate не обновляют observed максимум;
future terminal diagnosis маскирую. Complete_zero OMS/settlement и unknown empty
PSP различаю. Source reader использует REPEATABLE READ READ ONLY и bounds, не
меняет финансовую baseline/Case/schema9/24tables/9views. Новых migrations нет.

Я добавил tzdata2026.5/IANA2026e в analytics lock (62distributions), в orchestration
объявил direct dependency без смены107версий. Использую ZoneInfo.from_file изwheel,
не системный TZPATH. Пороги целые microseconds, timezone влияет на local date/offset/fold.
Прочитал официальные zoneinfo/tzdata/PostgreSQL isolation/datetime материалы,
обосновал ADR-33/34. FRESHNESS около1600слов, карта кода/CLI/ограничения/5заданий.

Я прошёл53unit в обеих средах,compileall,uv pip check62/107. Core runner exit0:
health readonly counts,late backfill,failed-after-success,duplicate-still-stale,
future terminal hidden,zero/unknown/incomplete,CLI. До health fixtures старый
контур прошёл schema8→9,4order results/11settlement reports и dbtPASS28(9models19tests).
Prefect runner тоже exit0: normal/exact replay/partial failure/retry2/3/marts
failure/CLI resume,oldSHA unchanged. Временные backend остановил/удалил.

В первом unit исправил неверное ожидание canonical UTC без6микросекундных знаков;
runtime контракт не менял. Нормализацию datetimes/fold принял до integration,
не выдаю за production bug. CI/Windows/нагрузку/realconcurrency/powerloss не проверял.
Нет health journal/notifier/source-specific SLA, marker не исторический MVCC replay.
Журналы отсутствующих pre-registration failures/settlement attempts не выдумываю.
PROGRESS16/30написано,14осталось/6до рабочего места (это не доля времени).
Следующий CG-305catalog. Public manifest120исходников,AGENTS остаётся только локально.
Публикацию фиксирую после фактического PR; sources/daily не менял.

Я опубликовал CG-304 в Draft PR#32 поверх #30, issue#31 перевёл в Review,
CG-305#33 создал Ready. Public manifest120исходников; внутренние инструкции
AGENTS остаются локально. Main обновляю только как навигацию, исходники не сливаю.
Точные remote/local/main heads и проверку blob SHA сохраняю в локальном FLAGSHIP.md.
После успешных проверок менял только документы/metadata; runtime код не менял.


## 26.10.2026 · CG-305

Я завершил каталог девяти dbt views с зерном, ключами, валютой, временем, lineage и владельцем смысла.

Я прошёл59unit tests; catalog check подтвердил9моделей. Новых зависимостей, SQL-миграций и runtime подключений нет.
Материалы: [CATALOG](CATALOG.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-401.

Я опубликовал CG-305 в [Draft PR#34](https://github.com/Decl1s/commerceguard/pull/34), затем взял CG-401 issue#35.


## 26.10.2026 · CG-401

Я добавил локальную read-only очередь, фильтры, keyset pagination, карточку с историей и evidence.

Я прошёл65unit и core/HTTP integration наPG16.15: filters, empty state, head409, Host/cross-site guards, финансовые SHA неизменны;dbtPASS28.
Материалы: [WORKPLACE](WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-402.

Я опубликовал CG-401 в [Draft PR#36](https://github.com/Decl1s/commerceguard/pull/36), затем взял CG-402 issue#37.


## 26.10.2026 · CG-402

Я добавил локальные аккаунты, роли и merchant scopes, серверные сессии, CSRF и отзыв доступа.

Я прошёл70unit и PostgreSQL/HTTP integration: schema8→10 на данных, login/logout/disable, role/scope denial, Origin/CSRF, challenge replay, account throttle;dbtPASS28.
Материалы: [WORKPLACE](WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-403.

Я опубликовал CG-402 в [Draft PR#38](https://github.com/Decl1s/commerceguard/pull/38), затем взял CG-403 issue#39.


## 26.10.2026 · CG-403

Я добавил назначения, комментарии, workflow version и атомарный append-only аудит человеческих действий.

Я прошёл75unit и PG/HTTP integration: schema8→11, exact replay, changed-request409, настоящий конфликт двух соединений, rollback между UPDATE/audit, deferred guard и stored-XSS escape;dbtPASS28.
Материалы: [WORKPLACE](WORKPLACE.md).
Я сохраняю учебный статус, исходники без локальных данных и WIP1; следующий CG-404.
