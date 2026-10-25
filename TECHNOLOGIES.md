# Технологии и зависимости

## Текущий проверенный набор · CG-301, 25.10.2026

Я использую CPython 3.12.15, PostgreSQL 16.15, Psycopg/binary 3.3.6,
dbt Core 1.12.6 и dbt-postgres 1.11.0. Resolver/install выполнены uv 0.13.1
в отдельной .venv, hashes проверены. Я установил 61 distribution, включая
транзитивные; полный воспроизводимый набор — requirements-analytics.in/lock.
Это проверенный Linux/Python3.12 analytics набор. Core-only requirements-postgres.lock
с его прежними typing_extensions/tzdata pins отдельно здесь не устанавливал.

Я выбрал SQL-first dbt v1 Core/adapter; доступную новую v2 distribution не добавляю
в это окружение. Прочитал актуальные официальные материалы, совместимость
закреплённых v1 версий подтвердил build 8views/13tests. PostgreSQL binaries уже
доступны в среде: я не устанавливал системные компоненты и постоянные сервисы.
Временные кластеры без TCP остановил. Нагрузочные гарантии/Windows не подтверждал.

Базовый domain/demo/parser использует только Python stdlib. Для проверок добавил
stdlib unittest, subprocess, tempfile, importlib.metadata; SQL data tests — часть dbt.
Использую YAML 1.2-совместимые конфигурации dbt, Jinja ref/source и PostgreSQL views,
JSONB/lateral/window functions/FILTER/FULL JOIN. Новых core migrations нет.
Git/Markdown/Mermaid и необязательный VS Code workspace сохраняю. Wheel приложения,
Prefect, HTTP/UI и CI не добавлял.

### Все фактически установленные Python distributions

Я фиксирую даже транзитивные пакеты: их назначение в окружении определяется
dependency graph lock, прямое использование в коде не приписываю каждому из них.
dbt-core-experimental-parser 2.0.8 установлен сборкой из проверенного sdist;
остальные установленные артефакты выбрал resolver. Это не обещание наличия wheel
для любой ОС. Официальная страница конкретной версии — в каждой строке.

| Distribution | Версия | Роль |
| --- | --- | --- |
| [agate](https://pypi.org/project/agate/1.9.1/) | 1.9.1 | Транзитивная зависимость analytics набора |
| [annotated-types](https://pypi.org/project/annotated-types/0.8.0/) | 0.8.0 | Транзитивная зависимость analytics набора |
| [attrs](https://pypi.org/project/attrs/26.1.0/) | 26.1.0 | Транзитивная зависимость analytics набора |
| [babel](https://pypi.org/project/babel/2.18.0/) | 2.18.0 | Транзитивная зависимость analytics набора |
| [certifi](https://pypi.org/project/certifi/2026.10.23/) | 2026.10.23 | Транзитивная зависимость analytics набора |
| [charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.2/) | 3.5.2 | Транзитивная зависимость analytics набора |
| [click](https://pypi.org/project/click/8.5.0/) | 8.5.0 | Транзитивная зависимость analytics набора |
| [colorama](https://pypi.org/project/colorama/0.4.6/) | 0.4.6 | Транзитивная зависимость analytics набора |
| [daff](https://pypi.org/project/daff/1.4.2/) | 1.4.2 | Транзитивная зависимость analytics набора |
| [dbt-adapters](https://pypi.org/project/dbt-adapters/1.24.5/) | 1.24.5 | Транзитивная зависимость analytics набора |
| [dbt-common](https://pypi.org/project/dbt-common/1.39.0/) | 1.39.0 | Транзитивная зависимость analytics набора |
| [dbt-core](https://pypi.org/project/dbt-core/1.12.6/) | 1.12.6 | Я выполняю SQL DAG и data tests |
| [dbt-core-experimental-parser](https://pypi.org/project/dbt-core-experimental-parser/2.0.8/) | 2.0.8 | Транзитивная зависимость analytics набора |
| [dbt-extractor](https://pypi.org/project/dbt-extractor/0.6.0/) | 0.6.0 | Транзитивная зависимость analytics набора |
| [dbt-postgres](https://pypi.org/project/dbt-postgres/1.11.0/) | 1.11.0 | Я подключаю dbt к PostgreSQL |
| [dbt-protos](https://pypi.org/project/dbt-protos/1.0.615/) | 1.0.615 | Транзитивная зависимость analytics набора |
| [deepdiff](https://pypi.org/project/deepdiff/8.6.2/) | 8.6.2 | Транзитивная зависимость analytics набора |
| [idna](https://pypi.org/project/idna/3.20/) | 3.20 | Транзитивная зависимость analytics набора |
| [importlib_metadata](https://pypi.org/project/importlib_metadata/10.1.0/) | 10.1.0 | Транзитивная зависимость analytics набора |
| [isodate](https://pypi.org/project/isodate/0.7.2/) | 0.7.2 | Транзитивная зависимость analytics набора |
| [Jinja2](https://pypi.org/project/Jinja2/3.1.6/) | 3.1.6 | Транзитивная зависимость analytics набора |
| [jsonschema](https://pypi.org/project/jsonschema/4.26.0/) | 4.26.0 | Транзитивная зависимость analytics набора |
| [jsonschema-specifications](https://pypi.org/project/jsonschema-specifications/2025.9.1/) | 2025.9.1 | Транзитивная зависимость analytics набора |
| [leather](https://pypi.org/project/leather/0.4.1/) | 0.4.1 | Транзитивная зависимость analytics набора |
| [MarkupSafe](https://pypi.org/project/MarkupSafe/3.0.4/) | 3.0.4 | Транзитивная зависимость analytics набора |
| [mashumaro](https://pypi.org/project/mashumaro/3.17/) | 3.17 | Транзитивная зависимость analytics набора |
| [metricflow](https://pypi.org/project/metricflow/0.213.0/) | 0.213.0 | Транзитивная зависимость analytics набора |
| [more-itertools](https://pypi.org/project/more-itertools/10.8.0/) | 10.8.0 | Транзитивная зависимость analytics набора |
| [msgpack](https://pypi.org/project/msgpack/1.2.3/) | 1.2.3 | Транзитивная зависимость analytics набора |
| [networkx](https://pypi.org/project/networkx/3.7/) | 3.7 | Транзитивная зависимость analytics набора |
| [opentelemetry-api](https://pypi.org/project/opentelemetry-api/1.45.1/) | 1.45.1 | Транзитивная зависимость analytics набора |
| [orderly-set](https://pypi.org/project/orderly-set/5.5.0/) | 5.5.0 | Транзитивная зависимость analytics набора |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | Транзитивная зависимость analytics набора |
| [parsedatetime](https://pypi.org/project/parsedatetime/2.6/) | 2.6 | Транзитивная зависимость analytics набора |
| [pathspec](https://pypi.org/project/pathspec/1.0.4/) | 1.0.4 | Транзитивная зависимость analytics набора |
| [protobuf](https://pypi.org/project/protobuf/6.33.6/) | 6.33.6 | Транзитивная зависимость analytics набора |
| [psycopg](https://pypi.org/project/psycopg/3.3.6/) | 3.3.6 | Я выполняю миграции/COPY/run/case |
| [psycopg-binary](https://pypi.org/project/psycopg-binary/3.3.6/) | 3.3.6 | Нативный driver runtime Psycopg |
| [psycopg2-binary](https://pypi.org/project/psycopg2-binary/2.9.13/) | 2.9.13 | Транзитивный PostgreSQL driver dbt adapter |
| [pydantic](https://pypi.org/project/pydantic/2.14.1/) | 2.14.1 | Транзитивная зависимость analytics набора |
| [pydantic_core](https://pypi.org/project/pydantic_core/2.50.1/) | 2.50.1 | Транзитивная зависимость analytics набора |
| [python-dateutil](https://pypi.org/project/python-dateutil/2.9.0.post0/) | 2.9.0.post0 | Транзитивная зависимость analytics набора |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.4/) | 1.2.4 | Транзитивная зависимость analytics набора |
| [python-slugify](https://pypi.org/project/python-slugify/9.1.3/) | 9.1.3 | Транзитивная зависимость analytics набора |
| [pytimeparse](https://pypi.org/project/pytimeparse/1.1.10/) | 1.1.10 | Транзитивная зависимость analytics набора |
| [pytz](https://pypi.org/project/pytz/2026.5/) | 2026.5 | Транзитивная зависимость analytics набора |
| [PyYAML](https://pypi.org/project/PyYAML/6.0.3/) | 6.0.3 | Транзитивная зависимость analytics набора |
| [RapidFuzz](https://pypi.org/project/RapidFuzz/3.14.6/) | 3.14.6 | Транзитивная зависимость analytics набора |
| [referencing](https://pypi.org/project/referencing/0.37.0/) | 0.37.0 | Транзитивная зависимость analytics набора |
| [requests](https://pypi.org/project/requests/2.34.2/) | 2.34.2 | Транзитивная зависимость analytics набора |
| [rpds-py](https://pypi.org/project/rpds-py/2026.9.1/) | 2026.9.1 | Транзитивная зависимость analytics набора |
| [six](https://pypi.org/project/six/1.17.0/) | 1.17.0 | Транзитивная зависимость analytics набора |
| [snowplow-tracker](https://pypi.org/project/snowplow-tracker/1.1.0/) | 1.1.0 | Транзитивная зависимость analytics набора |
| [sqlglot](https://pypi.org/project/sqlglot/30.24.0/) | 30.24.0 | Транзитивная зависимость analytics набора |
| [sqlparse](https://pypi.org/project/sqlparse/0.6.0/) | 0.6.0 | Транзитивная зависимость analytics набора |
| [tabulate](https://pypi.org/project/tabulate/0.10.0/) | 0.10.0 | Транзитивная зависимость analytics набора |
| [text-unidecode](https://pypi.org/project/text-unidecode/1.3/) | 1.3 | Транзитивная зависимость analytics набора |
| [typing-inspection](https://pypi.org/project/typing-inspection/0.4.4/) | 0.4.4 | Транзитивная зависимость analytics набора |
| [typing_extensions](https://pypi.org/project/typing_extensions/4.16.0/) | 4.16.0 | Транзитивная зависимость analytics набора |
| [urllib3](https://pypi.org/project/urllib3/2.8.0/) | 2.8.0 | Транзитивная зависимость analytics набора |
| [zipp](https://pypi.org/project/zipp/4.1.2/) | 4.1.2 | Транзитивная зависимость analytics набора |

Я использую официальные [Postgres adapter setup](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup),
[ref](https://docs.getdbt.com/reference/dbt-jinja-functions/ref),
[data tests](https://docs.getdbt.com/docs/build/data-tests),
[Python unittest](https://docs.python.org/3.12/library/unittest.html) и
[PostgreSQL 16](https://www.postgresql.org/docs/16/). Конкретные результаты — VALIDATION,
проектные причины — ADR-27/28 и MARTS. Locks/metadata не доказывают отсутствие всех
уязвимостей; отдельного security audit я не выполнял.

## История выбора до CG-301

Ниже я сохраняю первоначальный набор и состояние на дату написания. Отметки
«не устанавливал/не запускал» в этом разделе исторические; актуальный факт выше.

Дата выбора: 24.10.2026. Раздел «написано» означает наличие использования в исходниках,
а не установку, выполненный запуск или подтверждённую совместимость.

## Текущий срез

| Компонент | Целевая версия | Назначение и причина |
| --- | --- | --- |
| CPython | 3.12.15; поддерживаемая ветка >=3.12,<3.13 | Один язык предметного слоя и будущей загрузки; .python-version фиксирует patch |
| dataclasses | stdlib Python 3.12 | frozen/slots структуры и явные инварианты входа; без ORM в бизнес-правилах |
| datetime/timezone | stdlib Python 3.12 | UTC, aware timestamps, граница исторического знания |
| enum.StrEnum | stdlib Python 3.12 | Ограниченные состояния и коды, сериализуемые как строки |
| collections.defaultdict | stdlib Python 3.12 | Группировка событий по заказу |
| hashlib.sha256 | stdlib Python 3.12 | Case key, file/record/semantic/manifest hashes, merchant lock key; не подпись |
| uuid.UUID/uuid5/NAMESPACE_URL | stdlib Python 3.12 | Детерминированные batch/snapshot IDs без MAC-адреса |
| json | stdlib Python 3.12 | Однозначное составление ключа и JSON-отчёт |
| argparse/sys/re/typing | stdlib Python 3.12 | CLI, UTF-8 stdout, ограничения ID, аннотации интерфейса |
| pathlib/os | stdlib Python 3.12 | Пакетные SQL, raw hard links/fsync, внешнее подключение без печати DSN |
| csv/io | stdlib Python 3.12 | Строгий CSV и UTF-8 поток с сохранением окончаний строк |
| tempfile/contextlib | stdlib Python 3.12 | Ограниченный временный снимок входа и управление закрытием ресурсов |
| stat | stdlib Python 3.12 | Отказ от нерегулярных файлов при разборе входа |
| Psycopg + psycopg-binary | 3.3.6 / 3.3.6, опционально | Миграции, COPY write_row, Jsonb, параметры и транзакция; не устанавливались |
| typing_extensions | 4.15.0, транзитивная для Python 3.12 | Требуется драйвером; закреплена, не установлена |
| tzdata | 2026.2, транзитивная только Windows | Требуется драйвером на win32; закреплена, не установлена |
| PostgreSQL SQL/PLpgSQL | Ветка сервера 16 | DDL, ограничения, триггеры и advisory lock; сервер не запускался/не подключался |
| Git | Формат обычного самостоятельного репозитория | История этапов на ветках codex/; версия Git не влияет на расчёт |
| Markdown, Mermaid | Текст и диаграммы в GitHub | Документация, решения, бэклог и доска рядом с кодом |
| TOML/JSON | Конфигурационные форматы | Метаданные и локальное окно IDE, не отдельные runtime-библиотеки |
| VS Code | Необязательный редактор, версия не закрепляется | Просмотр, навигация; workspace не требует расширений |

Базовое ядро/demo/input inspect: **0 сторонних зависимостей** (pyproject dependencies=[]).
Опциональный postgres extra использует psycopg[binary]==3.3.6; полный набор exact
pins, включая все Python-транзитивные зависимости, — requirements-postgres.lock.
Это ручная фиксация по метаданным PyPI, не результат resolver/install и не hash-lock.
Модули stdlib версионируются вместе с CPython; отдельно dataclasses/enum/hashlib
не устанавливаются. Сборка wheel приложения и тестовые библиотеки не вводились.
psycopg-binary содержит нативные компоненты (включая libpq); конкретный wheel
зависит от ОС/архитектуры. Их runtime-версии не наблюдались и не выдаются за измеренные.

## Следующие компоненты и границы текущего подключения

| Компонент | Где появится | Зачем нужен |
| --- | --- | --- |
| PostgreSQL, ветка 16 | S1, CG-101…103 написаны без применения | DDL/миграции, TEMP staging, manifest/receipts, публикация |
| Psycopg 3.3.6 | S1, адаптер написан, не установлен | Транзакции миграций и ingestion, COPY FROM STDIN/write_row, JSONB |
| dbt Core + dbt-postgres | S3 | SQL-витрины с ref/DAG и lineage моделей |
| Prefect | S3 | Граф пакетного потока, retries, расписание и параметры backfill |
| FastAPI + Jinja2 | S4 | Небольшое рабочее место, API и серверное HTML без отдельного SPA |
| Контейнерная композиция | S5 | Воспроизводимое окружение по запросу, без постоянных сервисов по умолчанию |

Patch-версии будущих компонентов не угадываются. Перед фактическим добавлением
нужно прочитать официальную документацию, закрепить прямые и транзитивные зависимости,
обновить этот файл и описать ограничение отсутствия исполнения. Пакеты dbt/Prefect/
FastAPI/Jinja2 не подключены. Psycopg импортируется только при явной команде db/ingest
и не нужен demo. Я не запускал ни одну команду приложения. Kafka, Spark, Airflow, Kubernetes,
облака и Redis в архитектуру не включены: требование пока не оправдывает их цену.

Официальные ссылки на каждую фактическую stdlib-группу и будущие компоненты:
[SOURCES.md](docs/SOURCES.md). Прочтение документации не заменяет запуск проекта.

CG-104: я использую прежние Python 3.12/Psycopg 3.3.6/PostgreSQL 16 и pins;
новых сторонних зависимостей не добавил. uuid.uuid4 даёт ID попытки, os.scandir —
ограниченный обзор собственных manifest shard. Написал READ ONLY/REPEATABLE READ
обзор и отдельные короткие транзакции журнала. Всё без исполнения.

CG-105: я использую прежние stdlib csv/io/json/hashlib/pathlib/os/datetime и
uuid.UUID для генерации и выбора metadata. Psycopg/PostgreSQL нужны только status/
publish, генератор без сторонних пакетов. Pins не менял, новых транзитивных зависимостей
и миграций нет. Статус исполнения и ОС не подтверждал.

CG-201: я использую прежние Python/Psycopg/PostgreSQL/pins. Добавил fingerprint
собственных source bytes через hashlib, canonical manifest через JSON, UUIDv5
и две SQL-таблицы с FK/partial unique/immutable trigger. Динамических SQL-имён,
новых Python-зависимостей, сервиса и оркестратора не добавлял. Всё без исполнения.

CG-202: я сохранил прежний стек и pins. Использую JSONB для bounded immutable
snapshot, relational FK для evidence и history, Counter для per-batch counts,
Psycopg executemany с параметрами, отдельный run advisory lock. Новых библиотек
и сервисов нет. Применение PostgreSQL/Psycopg пока не проверял исполнением.

CG-203: я использую прежние Python 3.12/Psycopg 3.3.6/PostgreSQL 16 и pins.
Добавил dataclasses для snapshot, stdlib SHA/JSON для revision identity, advisory
xact lock и deferred composite FK для атомарной проекции. Новых прямых/транзитивных
библиотек, сборки и сервиса нет. Официальные основы: [locks](https://www.postgresql.org/docs/16/explicit-locking.html),
[constraints](https://www.postgresql.org/docs/16/ddl-constraints.html). Всё без исполнения.

CG-204: я сохранил Python 3.12/Psycopg 3.3.6/PostgreSQL 16 и прежние pins без
новых прямых/транзитивных пакетов. Использую aware UTC datetime для двух границ,
JSON/SHA/UUID для manifest v2, SQL FK для baseline и READ ONLY/REPEATABLE READ
для сравнения, NOT EXISTS для видимости baseline event. Основы:
[datetime](https://docs.python.org/3.12/library/datetime.html#aware-and-naive-objects),
[isolation](https://www.postgresql.org/docs/16/transaction-iso.html). Исполнения нет.

CG-205: я сохранил Python 3.12/Psycopg 3.3.6/PostgreSQL 16 и все pins, включая
транзитивные зависимости requirements-postgres.lock. Новых пакетов/сервисов нет.
Использую прежние dataclasses, datetime, JSON/SHA, CSV, UUID, SQL CHECK/composite FK
и advisory lock. В schema 8 добавляю constant default и nullable legacy columns.
Основа: [PostgreSQL 16 ALTER TABLE](https://www.postgresql.org/docs/16/ddl-alter.html).
Manifest/result v3 и deadline version — мои контракты, не версии библиотек.
Инструменты и SQL не запускал; dbt/Prefect по-прежнему только планы S3.
