# Схема и миграции: CG-101…103

0.1.0.dev3, 24.10.2026, написано без исполнения. Я пока не открывал соединение, не применял SQL
и не импортировал драйвер. Описываю намерение исходников.

## Карта файлов

| Файл | Ответственность |
| --- | --- |
| commerceguard/sql/bootstrap.sql | Схема, маркер, идентичность и журнал версий |
| commerceguard/sql/migrations/0001_storage_foundation.sql | Шесть таблиц ingest/core, связи, ограничения, триггеры и индексы |
| commerceguard/migrations.py | Доверенные SQL, проверки цели/истории, одна транзакция |
| commerceguard/__main__.py | CLI db status/migrate |
| requirements-postgres.lock | Exact pins опционального драйвера и Python-зависимостей |

ingest/core — логические слои, представленные префиксами одной схемы commerceguard
(ADR-13). Нужна отдельная уже созданная PostgreSQL 16 БД commerceguard. Код не
создаёт базу, роли, системные службы или extensions и не использует схему public.

## Таблицы

| Объект | Ключ | Содержание |
| --- | --- | --- |
| app_identity | singleton=true | commerceguard:storage:v1, storage format=1 |
| schema_migration | version | Имя SQL, SHA-256 точных байтов, дата применения |
| ingest_batch | batch_id; UNIQUE canonical manifest hash (0002) | Источник, версия, ожидаемые строки/байты, состояние и время |
| ingest_raw_record | batch_id/row_number | Исходный текст логической записи и hash |
| ingest_quarantine | batch_id/row_number/error_code | Код причины и колонка, без payload в ошибке |
| core_oms_snapshot | snapshot_id, UNIQUE batch_id | Полный OMS-снимок, effective/observed времена |
| core_order_expectation | snapshot/merchant/order | Ожидаемые capture/refund и raw-ссылка |
| core_payment_event | merchant/source_event_id | Факт, semantic hash, времена и raw-ссылка |
| core_payment_receipt | batch_id/raw_row_number | Каждое поступление PSP, в том числе повтор, FK на canonical fact |

UUID формирует application layer CG-103: расширение uuid-ossp не нужно.
Деньги bigint, не более 10^12 на запись; агрегаты потребуют отдельной оценки диапазона.
Составные FK связывают строку с batch того же магазина/типа. FK платежа на заказ
намеренно нет: orphan должен сохраниться. is_complete=true не доказывает полноту
пакета; counts и атомарное опубликование написаны в CG-103; не исполнены.

Триггеры отклоняют UPDATE/DELETE нормализованных строк и снимка. Они защищают
от случайного DML, не от владельца: он может изменить триггер или TRUNCATE.
Роли приложения — S4. Primary key сам не различает равный повтор и конфликт;
это работа ingest CG-103. semantic_sha256 закреплён CG-102 в [INPUTS](INPUTS.md).

## Путь db migrate

1. Прочитать DSN из внешней переменной, не печатая его.
2. Прочитать пакетные UTF-8 SQL. Имена 0001..N непрерывны, checksum от точных байтов.
   Пользовательского --sql path нет.
3. Лениво импортировать Psycopg 3.3.6. До команды db он не требуется.
4. Соединение autocommit=True и один conn.transaction(): нет неявной внешней
   транзакции, из-за которой transaction() стал бы только SAVEPOINT.
5. Потребовать PostgreSQL 16 и БД commerceguard, для migrate — записываемый primary.
   Session-only search_path=pg_catalog, timeouts и UTC не меняют настройки кластера.
6. pg_try_advisory_xact_lock: при занятом ключе отказать, не ждать бесконечно.
7. У существующей схемы проверить владельца, маркер, собственные metadata-таблицы
   и identity. Несовпадение — отказ, не присвоение или исправление чужой схемы.
8. История должна быть точным префиксом локальных миграций. Новая база относительно
   старого checkout, пропуск версии или другая checksum — отказ без downgrade.
9. Новая схема получает bootstrap; все pending SQL и журнал пишутся в одной
   транзакции. SQL не режется по ';', поскольку PL/pgSQL содержит их внутри тела.
10. PUBLIC-доступ отзывается только у собственных объектов. Success возвращается
    после выхода из transaction(), то есть после COMMIT.

При ошибке в pending-наборе контекст должен откатить DDL и запись версии, включая
первый CREATE SCHEMA. Это заявленное намерение кода, не наблюдавшийся rollback.
Advisory lock защищает только между миграторами с тем же ключом, не от DBA.
READ COMMITTED выбран, чтобы команда после lock видела завершённого предшественника.
Официальная база — SOURCES; наше применение ещё не проверено.

db status использует тот же lock и READ ONLY transaction. Если схемы нет,
показывает version=0 и pending, не создавая её. Это не healthcheck всех таблиц,
прав и данных. Повтор migrate на актуальной схеме не исполняет SQL заново;
PUBLIC ACL вновь ограничивается. Расхождение фактического DDL при неизменённой
истории этим срезом не обнаруживается: полного catalog diff здесь нет.

## Подготовленные мной команды, которые я пока не выполнял

Из корня checkout в Linux; Windows Python — .venv/Scripts/python.exe:

```bash
.venv/bin/python -m pip install -r requirements-postgres.lock
.venv/bin/python -m commerceguard db status
.venv/bin/python -m commerceguard db migrate
```

До команд пользователь самостоятельно готовит отдельную PostgreSQL 16 БД
commerceguard и роль для владения своей схемой. Подключение — внешняя переменная
COMMERCEGUARD_DATABASE_URL. Пароль не добавлять в команду или Git; допустим внешний
libpq passfile. Другое имя переменной: `db --dsn-env MY_DATABASE_URL status`.
--dsn-env стоит перед status/migrate; сам DSN как аргумент CLI не принимается.

Wheel-сборка приложения не добавлена; pip install . не является инструкцией запуска.
requirements устанавливает только драйвер. Python-транзитивные зависимости вручную
закреплены по метаданным PyPI, не по выполненному resolver/install. binary wheel
содержит нативные библиотеки; их состав определяется платформенным артефактом,
runtime-версии не наблюдались. Применение этой инструкции не подтверждено.

## Ошибки и следующий шаг

MigrationError выводит составленную приложением причину, без DSN. Ошибки драйвера
показывают только SQLSTATE: текст сети/сервера может содержать параметры подключения.
Нет driver — сообщение об отдельном requirements. Нет команд reset/drop и обхода hash.

CG-102 добавил manifest и ограниченный parser CSV/JSONL без вставки core.
CG-103 добавил 0002, persistent raw, staging/COPY и публикацию;
подробности в [INGESTION](INGESTION.md). Работающий ingest не заявляется.

## Изменения CG-103

0002 требует пустую legacy ingest_batch, добавляет manifest_sha256/JSONB,
относительные raw/manifest keys, parsed/new/known/duplicate counts и таблицу
core_payment_receipt. 0001 сохранён неизменным. Пустая новая БД получает bootstrap,
0001 и 0002 одной транзакцией; версия 1 без batches получает только 0002.
Если batches уже вставлены вручную, мигратор отказывает без DELETE и подстановки
неизвестных времён. Это ограничение обновления, а не реализованный backfill.

Общее соединение вынесено в postgres.py. require_current_storage требует всю
текущую историю до COPY. Ingest берёт shared lock мигратора и merchant lock.
9 физических таблиц вместе с metadata; TEMP stage не входит в постоянную схему.
Receipts защищены тем же append-only trigger. Прямой DML владельца схемы и drift
каталога вне гарантий этого среза. Ни одна миграция не применена.

## CG-104: журнал попыток

Я добавил ingest_attempt в 0003: это десятая постоянная таблица. Candidate batch_id
не имеет FK, потому что started регистрирую до core; published_batch_id имеет FK
и появляется лишь у published/duplicate attempt. Guard разрешает единственный
переход started → terminal и сохраняет identity. Старые миграции не менял.
Обзор требует текущую схему с write=False; публикация — writable primary.
Описал границы карантина и недоступного журнала в [RECOVERY](RECOVERY.md).

## S2/CG-201: immutable run inputs

Я добавил 0004, ops_run_manifest и ops_run_input: всего 12 постоянных таблиц.
Один run имеет один OMS input и от 1 до 10000 PSP inputs. FK сохраняют связи
merchant/run/batch/snapshot, append-only triggers защищают обычный UPDATE/DELETE.
Manifest и все input rows пишу одним COMMIT; lifecycle выполнения сюда не смешиваю.
Старые SQL-файлы не редактировал. Подробности — RUN_MANIFEST, ADR-22. SQL не применял.

## CG-202: результат и происхождение

Я добавил 0005: ops_run_attempt, ops_run_result, ops_run_evidence — всего 15 таблиц.
Manifest/input не меняю; additive UNIQUE(run_id,snapshot_id) связывает result с
выбранным OMS. Result JSON/Text и evidence публикую вместе, terminal attempts
защищаю trigger. Result/evidence immutable. Bound snapshot в v1 вместо второй
копии mutable денежных строк; SQL projections — следующий контур S3. См. RESULTS.

## CG-203: schema 6, кейсы

Я добавил 0006 без изменения 0001…0005: ops_case_application/stream/case/revision/event.
Всего 20 persistent tables. Ledger/revisions/events immutable; head содержит presence,
workflow=open, first/last/evaluated run и номер ревизии. FK head → revision/presence
DEFERRABLE INITIALLY DEFERRED. App stream сериализую отдельным merchant advisory lock.
Подробности CASES/ADR-24. SQL и БД не запускал.

## CG-204: schema 7, временные корректировки

Я добавил 0007 без обновления старых строк: расширил mode/time/result_version checks,
добавил nullable legacy reason_code/baseline_run_id и FK на опубликованный result
с merchant. Новый manifest v2 требует reason и baseline для as-known-now; прежний
v1 сохраняет NULL в этих новых колонках. Сопоставление baseline cutoff выполняю
в адаптере, не выдаю обычный CHECK за межстрочное ограничение. Новых таблиц нет:
по-прежнему 20. Имена снимаемых checks относятся к точной схеме 0004/0005 PG16;
проверенный migration ledger обязателен, произвольный legacy schema не принимаю.
SQL и существование constraints исполнением не проверял.

## CG-205: schema 8, без переписывания данных

Я добавил 0008_expectation_deadlines.sql, не меняя опубликованные 0001…0007.
Таблиц по-прежнему 20. В core_order_expectation добавляю expectation_version
с default=1 и nullable capture_due_at/refund_due_at. CHECK различает legacy v1
и полный v2, включая конечность сроков и settle_after=max. Старые строки остаются
legacy с NULL сроками, адаптация происходит при чтении. UPDATE core/raw нет.
В ops_run_input добавляю nullable contract_version: старое membership не backfill,
новое v3 явно записывает версию. Composite FK связывают batch/merchant/version
и защищают от записи v2 под v1. Расширяю checks manifest/ruleset/result; исторические
варианты сохраняю. В ops_case_application добавляю policy v2, nullable upgrade source
и ссылку на применение того же merchant; порядок и expected head проверяет service
под merchant lock. SQL/FK и имена снимаемых checks я не исполнял.
Обоснование constant default и ограничений — ADR-26/DEADLINES; это намерение DDL,
не подтверждённый результат миграции PostgreSQL.

## CG-302: schema9 и четыре append-only таблицы

Я добавил 0009_settlement.sql: core_settlement_advice, core_settlement_event_assignment,
core_settlement_member, ops_settlement_result. Теперь24 persistent tables. UPDATE/DELETE
запрещены; missing PSP fact допускаю для unknown, event assignment уникален на merchant.
Я проверил upgrade заполненной schema8, повтор migration noop и SHA прежних run.
9views строит dbt отдельно. Полная карта FK/identity/raw и ограничения — SETTLEMENT.

## CG-304: схема не меняется

Я читаю ingest_batch/ingest_attempt, PSP receipts/events и core_settlement_advice
в REPEATABLE READ READ ONLY. Никаких UPDATE/migrate в source health нет. В проверке
counts до/после чтения не изменились, saved reports сохранили SHA. Query bounds
не гарантируют быстрый план на большом объёме; индексы/EXPLAIN оставляю S5.
Сейчас schema9/24persistent tables/9views, прежние migrations неизменны.
