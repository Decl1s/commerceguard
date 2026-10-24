# CG-101: схема и миграции

0.1.0.dev1, 24.10.2026, написано без исполнения. Я пока не открывал соединение, не применял SQL
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
| ingest_batch | batch_id; UNIQUE merchant/source/hash | Источник, версия, ожидаемые строки/байты, состояние и время |
| ingest_raw_record | batch_id/row_number | Исходный текст логической записи и hash |
| ingest_quarantine | batch_id/row_number/error_code | Код причины и колонка, без payload в ошибке |
| core_oms_snapshot | snapshot_id, UNIQUE batch_id | Полный OMS-снимок, effective/observed времена |
| core_order_expectation | snapshot/merchant/order | Ожидаемые capture/refund и raw-ссылка |
| core_payment_event | merchant/source_event_id | Факт, semantic hash, времена и raw-ссылка |

UUID формирует будущий application layer: расширение uuid-ossp не нужно.
Деньги bigint, не более 10^12 на запись; агрегаты потребуют отдельной оценки диапазона.
Составные FK связывают строку с batch того же магазина/типа. FK платежа на заказ
намеренно нет: orphan должен сохраниться. is_complete=true не доказывает полноту
пакета; counts и атомарное опубликование обеспечивает будущий CG-103.

Триггеры отклоняют UPDATE/DELETE нормализованных строк и снимка. Они защищают
от случайного DML, не от владельца: он может изменить триггер или TRUNCATE.
Роли приложения — S4. Primary key сам не различает равный повтор и конфликт;
это работа будущего ingest. Точный semantic_sha256 будет закреплён CG-102.

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

CG-102 определит manifest и ограниченный parser CSV/JSONL, не вставляющий core
построчно до завершения партии. COPY и публикация остаются CG-103. Таблицы CG-101
лишь подготавливают будущий поток; работающий ingest не заявляется.
