# Схема и миграции: CG-101…103

0.1.0.dev3, 24.10.2026, написано без исполнения. Ни соединение, ни SQL,
ни driver import разработчиком не выполнялись. Описано намерение исходников.

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

## Команды для пользователя, не выполненные разработчиком

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
