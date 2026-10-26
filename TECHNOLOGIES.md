# Технологии и зависимости

## Analytics набор · CG-304, 26.10.2026

Я использую CPython 3.12.15, PostgreSQL 16.15, Psycopg/binary 3.3.6,
dbt Core 1.12.6 и dbt-postgres 1.11.0. Resolver/install выполнены uv 0.13.1
в отдельной .venv, hashes проверены. Я установил 62 distributions, включая
транзитивные; полный воспроизводимый набор — requirements-analytics.in/lock.
Это проверенный Linux/Python3.12 analytics набор. Core-only requirements-postgres.lock
с его прежними typing_extensions/tzdata pins отдельно здесь не устанавливал.

Я выбрал SQL-first dbt v1 Core/adapter; доступную новую v2 distribution не добавляю
в это окружение. Прочитал актуальные официальные материалы, совместимость
закреплённых v1 версий подтвердил build 9views/19tests. PostgreSQL binaries уже
доступны в среде: я не устанавливал системные компоненты и постоянные сервисы.
Временные кластеры без TCP остановил. Нагрузочные гарантии/Windows не подтверждал.

Базовый domain/demo/parser использует только Python stdlib. Для проверок добавил
stdlib unittest, subprocess, tempfile, importlib.metadata; SQL data tests — часть dbt.
Использую YAML 1.2-совместимые конфигурации dbt, Jinja ref/source и PostgreSQL views,
JSONB/lateral/window functions/FILTER/FULL JOIN. В CG-302 я добавил migration0009
и четыре append-only таблицы; прежние опубликованные миграции не менял.
Git/Markdown/Mermaid и необязательный VS Code workspace сохраняю. Wheel приложения,
HTTP/UI и CI не добавлял. Prefect теперь изолирую в отдельном orchestration
окружении со107distribution; полный набор описываю ниже в разделе CG-303.

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
| [tzdata](https://pypi.org/project/tzdata/2026.5/) | 2026.5 | Я читаю закреплённую IANA2026e базу для source health |
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

## CG-302: я сохранил зависимости и расширил SQL-контракт

26.10.2026. Прямые и все 61 транзитивные distributions/pins/hashes остались прежними.
Я добавил stdlib dataclass/JSON/SHA/UUID и integer half-up для advice/result,
Psycopg parameter binding, LEFT JOIN LATERAL для одного receipt на member,
ON CONFLICT после проверки assignment под merchant advisory lock. Официальные основы:
[PostgreSQL16 LATERAL](https://www.postgresql.org/docs/16/queries-table-expressions.html#QUERIES-LATERAL),
[INSERT/ON CONFLICT](https://www.postgresql.org/docs/16/sql-insert.html).
Gross-bps-half-up-v1 — моя учебная бизнес-политика, не стандарт SQL/PSP.
Версия приложения dev12, schema9/24tables/9views. 27unit и dbt19tests прошли на Linux;
CI/Windows/Prefect в этот срез не входят. Карта и аргументы — docs/SETTLEMENT.md.

## CG-303: мой отдельный набор оркестрации · 26.10.2026

Я сохранил analytics61distribution без изменений и установил отдельные107distribution
в .venv-orchestration: Prefect3.8.8/Psycopg3.3.6/FastAPI0.154.0. CPython3.12.15,
uv0.13.1; lock requirements-orchestration.in/lock содержит все pins/hashes. Я
выполнил uv pip check и реальный flow, совместимость не вывожу только из resolver.
FastAPI0.162.0 сначала сломала Body(min_items) Prefect; pin0.154.0 обосновал ADR-32.

Я использую flow/task, NO_CACHE, retry_condition_fn, synchronous task calls,
SubprocessASGIServer3.8.8, stdlib subprocess/tempfile/signal и временные JSON/YAML.
Prefect internal SQLite/HTTP/ASGI — backend одной команды. Docker/Redis/Apprise/
cryptography и другие пакеты ниже входят транзитивно; отдельные Docker/Redis службы,
провайдеры уведомлений и внешние API я не запускаю. Бизнес-HTTP/RBAC ещё впереди.
Dbт v1 вызывает отдельный analytics Python через dbtRunner. Schema9/24tables/9views
и прежние migrations/pins analytics не менял. Полный маршрут — ORCHESTRATION.

### Все фактически установленные distributions окружения оркестратора

Я фиксирую каждый пакет; роль «транзитивный» не означает прямое использование его
API в моём коде. Официальная версия PyPI связана с каждой строкой таблицы.

| Distribution | Версия | Назначение |
| --- | --- | --- |
| [Jinja2](https://pypi.org/project/Jinja2/3.1.6/) | 3.1.6 | Транзитивная зависимость окружения оркестратора |
| [Mako](https://pypi.org/project/Mako/1.4.3/) | 1.4.3 | Транзитивная зависимость окружения оркестратора |
| [Markdown](https://pypi.org/project/Markdown/3.11.2/) | 3.11.2 | Транзитивная зависимость окружения оркестратора |
| [MarkupSafe](https://pypi.org/project/MarkupSafe/3.0.4/) | 3.0.4 | Транзитивная зависимость окружения оркестратора |
| [PyYAML](https://pypi.org/project/PyYAML/6.0.3/) | 6.0.3 | Транзитивная зависимость окружения оркестратора |
| [Pygments](https://pypi.org/project/Pygments/2.21.0/) | 2.21.0 | Транзитивная зависимость окружения оркестратора |
| [SQLAlchemy](https://pypi.org/project/SQLAlchemy/2.1.6/) | 2.1.6 | Транзитивная зависимость окружения оркестратора |
| [aiosqlite](https://pypi.org/project/aiosqlite/0.22.1/) | 0.22.1 | Транзитивная зависимость окружения оркестратора |
| [alembic](https://pypi.org/project/alembic/1.20.1/) | 1.20.1 | Транзитивная зависимость окружения оркестратора |
| [amplitude-analytics](https://pypi.org/project/amplitude-analytics/1.3.0/) | 1.3.0 | Транзитивная зависимость окружения оркестратора |
| [annotated-doc](https://pypi.org/project/annotated-doc/0.0.5/) | 0.0.5 | Транзитивная зависимость окружения оркестратора |
| [annotated-types](https://pypi.org/project/annotated-types/0.8.0/) | 0.8.0 | Транзитивная зависимость окружения оркестратора |
| [anyio](https://pypi.org/project/anyio/4.15.1/) | 4.15.1 | Транзитивная зависимость окружения оркестратора |
| [apprise](https://pypi.org/project/apprise/1.13.1/) | 1.13.1 | Транзитивная зависимость окружения оркестратора |
| [asgi-lifespan](https://pypi.org/project/asgi-lifespan/2.1.0/) | 2.1.0 | Транзитивная зависимость окружения оркестратора |
| [asyncpg](https://pypi.org/project/asyncpg/0.32.0/) | 0.32.0 | Транзитивная зависимость окружения оркестратора |
| [attrs](https://pypi.org/project/attrs/26.1.0/) | 26.1.0 | Транзитивная зависимость окружения оркестратора |
| [beartype](https://pypi.org/project/beartype/0.23.1/) | 0.23.1 | Транзитивная зависимость окружения оркестратора |
| [burner-redis](https://pypi.org/project/burner-redis/0.1.7/) | 0.1.7 | Транзитивная зависимость окружения оркестратора |
| [cachetools](https://pypi.org/project/cachetools/7.2.5/) | 7.2.5 | Транзитивная зависимость окружения оркестратора |
| [certifi](https://pypi.org/project/certifi/2026.10.23/) | 2026.10.23 | Транзитивная зависимость окружения оркестратора |
| [cffi](https://pypi.org/project/cffi/2.1.1/) | 2.1.1 | Транзитивная зависимость окружения оркестратора |
| [charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.2/) | 3.5.2 | Транзитивная зависимость окружения оркестратора |
| [click](https://pypi.org/project/click/8.5.0/) | 8.5.0 | Транзитивная зависимость окружения оркестратора |
| [cloudpickle](https://pypi.org/project/cloudpickle/3.1.2/) | 3.1.2 | Транзитивная зависимость окружения оркестратора |
| [colorama](https://pypi.org/project/colorama/0.4.6/) | 0.4.6 | Транзитивная зависимость окружения оркестратора |
| [coolname](https://pypi.org/project/coolname/5.0.0/) | 5.0.0 | Транзитивная зависимость окружения оркестратора |
| [cronsim](https://pypi.org/project/cronsim/2.7/) | 2.7 | Транзитивная зависимость окружения оркестратора |
| [cryptography](https://pypi.org/project/cryptography/50.0.2/) | 50.0.2 | Транзитивная зависимость окружения оркестратора |
| [cyclopts](https://pypi.org/project/cyclopts/5.3.0/) | 5.3.0 | Транзитивная зависимость окружения оркестратора |
| [dateparser](https://pypi.org/project/dateparser/1.4.3/) | 1.4.3 | Транзитивная зависимость окружения оркестратора |
| [docker](https://pypi.org/project/docker/7.2.0/) | 7.2.0 | Транзитивная зависимость окружения оркестратора |
| [docstring_parser](https://pypi.org/project/docstring_parser/0.18.0/) | 0.18.0 | Транзитивная зависимость окружения оркестратора |
| [exceptiongroup](https://pypi.org/project/exceptiongroup/1.3.1/) | 1.3.1 | Транзитивная зависимость окружения оркестратора |
| [fastapi](https://pypi.org/project/fastapi/0.154.0/) | 0.154.0 | Я закрепляю совместимый внутренний API Prefect |
| [fsspec](https://pypi.org/project/fsspec/2026.9.0/) | 2026.9.0 | Транзитивная зависимость окружения оркестратора |
| [graphviz](https://pypi.org/project/graphviz/0.21/) | 0.21 | Транзитивная зависимость окружения оркестратора |
| [greenlet](https://pypi.org/project/greenlet/3.5.6/) | 3.5.6 | Транзитивная зависимость окружения оркестратора |
| [griffe](https://pypi.org/project/griffe/2.4.1/) | 2.4.1 | Транзитивная зависимость окружения оркестратора |
| [griffecli](https://pypi.org/project/griffecli/2.4.1/) | 2.4.1 | Транзитивная зависимость окружения оркестратора |
| [griffelib](https://pypi.org/project/griffelib/2.4.1/) | 2.4.1 | Транзитивная зависимость окружения оркестратора |
| [h11](https://pypi.org/project/h11/0.16.0/) | 0.16.0 | Транзитивная зависимость окружения оркестратора |
| [h2](https://pypi.org/project/h2/4.4.1/) | 4.4.1 | Транзитивная зависимость окружения оркестратора |
| [hpack](https://pypi.org/project/hpack/4.2.0/) | 4.2.0 | Транзитивная зависимость окружения оркестратора |
| [httpcore](https://pypi.org/project/httpcore/1.0.9/) | 1.0.9 | Транзитивная зависимость окружения оркестратора |
| [httpx](https://pypi.org/project/httpx/0.28.1/) | 0.28.1 | Транзитивная зависимость окружения оркестратора |
| [humanize](https://pypi.org/project/humanize/4.16.0/) | 4.16.0 | Транзитивная зависимость окружения оркестратора |
| [hyperframe](https://pypi.org/project/hyperframe/6.1.0/) | 6.1.0 | Транзитивная зависимость окружения оркестратора |
| [idna](https://pypi.org/project/idna/3.20/) | 3.20 | Транзитивная зависимость окружения оркестратора |
| [jinja2-humanize-extension](https://pypi.org/project/jinja2-humanize-extension/0.4.0/) | 0.4.0 | Транзитивная зависимость окружения оркестратора |
| [jsonpatch](https://pypi.org/project/jsonpatch/1.37/) | 1.37 | Транзитивная зависимость окружения оркестратора |
| [jsonpointer](https://pypi.org/project/jsonpointer/3.5/) | 3.5 | Транзитивная зависимость окружения оркестратора |
| [jsonschema](https://pypi.org/project/jsonschema/4.26.0/) | 4.26.0 | Транзитивная зависимость окружения оркестратора |
| [jsonschema-specifications](https://pypi.org/project/jsonschema-specifications/2025.9.1/) | 2025.9.1 | Транзитивная зависимость окружения оркестратора |
| [markdown-it-py](https://pypi.org/project/markdown-it-py/4.2.0/) | 4.2.0 | Транзитивная зависимость окружения оркестратора |
| [mdurl](https://pypi.org/project/mdurl/0.1.2/) | 0.1.2 | Транзитивная зависимость окружения оркестратора |
| [oauthlib](https://pypi.org/project/oauthlib/4.0.0/) | 4.0.0 | Транзитивная зависимость окружения оркестратора |
| [opentelemetry-api](https://pypi.org/project/opentelemetry-api/1.45.1/) | 1.45.1 | Транзитивная зависимость окружения оркестратора |
| [orjson](https://pypi.org/project/orjson/3.13.0/) | 3.13.0 | Транзитивная зависимость окружения оркестратора |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | Транзитивная зависимость окружения оркестратора |
| [pathspec](https://pypi.org/project/pathspec/1.1.1/) | 1.1.1 | Транзитивная зависимость окружения оркестратора |
| [pendulum](https://pypi.org/project/pendulum/3.3.0/) | 3.3.0 | Транзитивная зависимость окружения оркестратора |
| [pluggy](https://pypi.org/project/pluggy/1.7.0/) | 1.7.0 | Транзитивная зависимость окружения оркестратора |
| [prefect](https://pypi.org/project/prefect/3.8.8/) | 3.8.8 | Я выполняю локальный flow и задачи |
| [prometheus_client](https://pypi.org/project/prometheus_client/0.26.0/) | 0.26.0 | Транзитивная зависимость окружения оркестратора |
| [psycopg](https://pypi.org/project/psycopg/3.3.6/) | 3.3.6 | Я вызываю существующие сервисы PostgreSQL |
| [psycopg-binary](https://pypi.org/project/psycopg-binary/3.3.6/) | 3.3.6 | Я использую wheel драйвера libpq |
| [py-key-value-aio](https://pypi.org/project/py-key-value-aio/0.4.6/) | 0.4.6 | Транзитивная зависимость окружения оркестратора |
| [pycparser](https://pypi.org/project/pycparser/3.12/) | 3.12 | Транзитивная зависимость окружения оркестратора |
| [pydantic](https://pypi.org/project/pydantic/2.14.1/) | 2.14.1 | Транзитивная зависимость окружения оркестратора |
| [pydantic-extra-types](https://pypi.org/project/pydantic-extra-types/2.11.1/) | 2.11.1 | Транзитивная зависимость окружения оркестратора |
| [pydantic-settings](https://pypi.org/project/pydantic-settings/2.16.1/) | 2.16.1 | Транзитивная зависимость окружения оркестратора |
| [pydantic_core](https://pypi.org/project/pydantic_core/2.50.1/) | 2.50.1 | Транзитивная зависимость окружения оркестратора |
| [pydocket](https://pypi.org/project/pydocket/0.27.0/) | 0.27.0 | Транзитивная зависимость окружения оркестратора |
| [python-dateutil](https://pypi.org/project/python-dateutil/2.9.0.post0/) | 2.9.0.post0 | Транзитивная зависимость окружения оркестратора |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.4/) | 1.2.4 | Транзитивная зависимость окружения оркестратора |
| [python-json-logger](https://pypi.org/project/python-json-logger/4.2.0/) | 4.2.0 | Транзитивная зависимость окружения оркестратора |
| [python-slugify](https://pypi.org/project/python-slugify/9.0.0/) | 9.0.0 | Транзитивная зависимость окружения оркестратора |
| [pytz](https://pypi.org/project/pytz/2026.5/) | 2026.5 | Транзитивная зависимость окружения оркестратора |
| [readchar](https://pypi.org/project/readchar/4.2.2/) | 4.2.2 | Транзитивная зависимость окружения оркестратора |
| [redis](https://pypi.org/project/redis/8.1.0/) | 8.1.0 | Транзитивная зависимость окружения оркестратора |
| [referencing](https://pypi.org/project/referencing/0.37.0/) | 0.37.0 | Транзитивная зависимость окружения оркестратора |
| [regex](https://pypi.org/project/regex/2026.9.29/) | 2026.9.29 | Транзитивная зависимость окружения оркестратора |
| [requests](https://pypi.org/project/requests/2.34.2/) | 2.34.2 | Транзитивная зависимость окружения оркестратора |
| [requests-oauthlib](https://pypi.org/project/requests-oauthlib/2.0.0/) | 2.0.0 | Транзитивная зависимость окружения оркестратора |
| [rfc3339-validator](https://pypi.org/project/rfc3339-validator/0.1.4/) | 0.1.4 | Транзитивная зависимость окружения оркестратора |
| [rich](https://pypi.org/project/rich/15.0.0/) | 15.0.0 | Транзитивная зависимость окружения оркестратора |
| [rich-rst](https://pypi.org/project/rich-rst/2.2.0/) | 2.2.0 | Транзитивная зависимость окружения оркестратора |
| [rpds-py](https://pypi.org/project/rpds-py/2026.9.1/) | 2026.9.1 | Транзитивная зависимость окружения оркестратора |
| [ruamel.yaml](https://pypi.org/project/ruamel.yaml/0.19.1/) | 0.19.1 | Транзитивная зависимость окружения оркестратора |
| [ruamel.yaml.clib](https://pypi.org/project/ruamel.yaml.clib/0.2.15/) | 0.2.15 | Транзитивная зависимость окружения оркестратора |
| [semver](https://pypi.org/project/semver/3.1.0/) | 3.1.0 | Транзитивная зависимость окружения оркестратора |
| [shellingham](https://pypi.org/project/shellingham/1.5.4/) | 1.5.4 | Транзитивная зависимость окружения оркестратора |
| [six](https://pypi.org/project/six/1.17.0/) | 1.17.0 | Транзитивная зависимость окружения оркестратора |
| [sniffio](https://pypi.org/project/sniffio/1.3.1/) | 1.3.1 | Транзитивная зависимость окружения оркестратора |
| [starlette](https://pypi.org/project/starlette/1.10.0/) | 1.10.0 | Транзитивная зависимость окружения оркестратора |
| [text-unidecode](https://pypi.org/project/text-unidecode/1.3/) | 1.3 | Транзитивная зависимость окружения оркестратора |
| [toml](https://pypi.org/project/toml/0.10.2/) | 0.10.2 | Транзитивная зависимость окружения оркестратора |
| [typer](https://pypi.org/project/typer/0.27.3/) | 0.27.3 | Транзитивная зависимость окружения оркестратора |
| [typing-inspection](https://pypi.org/project/typing-inspection/0.4.4/) | 0.4.4 | Транзитивная зависимость окружения оркестратора |
| [typing_extensions](https://pypi.org/project/typing_extensions/4.16.0/) | 4.16.0 | Транзитивная зависимость окружения оркестратора |
| [tzdata](https://pypi.org/project/tzdata/2026.5/) | 2026.5 | Я использую ту же IANA базу для source health; также зависимость Pendulum |
| [tzlocal](https://pypi.org/project/tzlocal/5.4.5/) | 5.4.5 | Транзитивная зависимость окружения оркестратора |
| [uncalled-for](https://pypi.org/project/uncalled-for/0.4.1/) | 0.4.1 | Транзитивная зависимость окружения оркестратора |
| [urllib3](https://pypi.org/project/urllib3/2.8.0/) | 2.8.0 | Транзитивная зависимость окружения оркестратора |
| [uvicorn](https://pypi.org/project/uvicorn/0.54.0/) | 0.54.0 | Транзитивная зависимость окружения оркестратора |
| [websockets](https://pypi.org/project/websockets/16.1.1/) | 16.1.1 | Транзитивная зависимость окружения оркестратора |

## CG-304: мой воспроизводимый business timezone

Я добавил прямой tzdata2026.5/IANA2026e в analytics lock:62distributions, прежние61
pins/hashes не менял. В orchestration он уже был, все107версий сохранил, объявил
прямую зависимость. Оба lock синхронизировал с hashes; uv pip check62/107 OK.
Официальные [tzdata](https://pypi.org/project/tzdata/2026.5/),
[zoneinfo/resources](https://docs.python.org/3.12/library/zoneinfo.html) и
[PostgreSQL16 isolation](https://www.postgresql.org/docs/16/transaction-iso.html).

Я использую stdlib dataclasses/datetime/timedelta/importlib.resources и ZoneInfo.from_file,
а не неявную timezone базу ОС. Source health читает metadata одним REPEATABLE READ
READ ONLY; SQL/параметры Psycopg3.3.6, сервер16.15 прежние. Таблицы/миграции/9views
не менял. 53unit в обоих окружениях и оба integration runner прошли; CI/Windows нет.
Предельный возраст/late threshold — мои явные параметры, не внешний SLA.

## 26.10.2026 · каталог и локальное рабочее место

Я добавил JSON-каталог и HTTP/HTML адаптер стандартной библиотеки CPython3.12.15.
Использую `http.server.HTTPServer`, `html.escape`, `http.cookies`, `urllib.parse`,
`secrets`, `hashlib.pbkdf2_hmac`, `hmac.compare_digest`, `getpass`; новых сторонних
дистрибутивов и транзитивных зависимостей нет. Psycopg3.3.6/PostgreSQL16.15 остаются
прежними. HTML forms не требуют Node/React/сборки. PostgreSQL schema10 добавляет
web_user/web_user_merchant/web_session, прежние миграции1…9 не меняю.

Официальные источники:
[HTTPServer](https://docs.python.org/3.12/library/http.server.html),
[hashlib](https://docs.python.org/3.12/library/hashlib.html),
[secrets](https://docs.python.org/3.12/library/secrets.html),
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
Я сознательно ограничил HTTP адаптер loopback учебным использованием: Python
не рекомендует http.server для production. Web identity не PostgreSQL role и не
защищает от прямого владельца БД. Locks analytics62/orchestration107 сохраняются.

CG-403/404: я довёл схему до12миграций и28persistent tables; добавил два поля Case
и append-only ops_case_human_event, deferred PL/pgSQL guard и индекс очереди.
Я использую прежние UUID, SHA256 canonical JSON, row/advisory locks и REPEATABLE READ
PostgreSQL16, без новых Python distributions. Python3.12.15, analytics62 и
orchestration107distribution закреплены прежними hash locks. CI/Windows/нагрузку
не заявляю; concurrency проверил только двумя реальными соединениями для Case.

## 27.10.2026 · эксплуатация и рабочая поставка

Я добавил stdlib backfill/backup/metrics, schema13…14 (31persistent tables), WSGI
адаптер и выделенные runtime grants. Новых библиотек для CSV/backup/логов не вводил.
Для web выбрал Waitress3.0.2; hash lock requirements-web содержит5distributions:
psycopg3.3.6,psycopg-binary3.3.6,typing-extensions4.16.0,tzdata2026.5,waitress3.0.2.
Analytics62 и orchestration107 сохраняю раздельными /opt/analytics и/opt/orchestration
venv tools image. Docker Python bootstrap/pip и OS пакеты фиксирует базовый digest
и состав image; прикладные Python pins/hashes хранятся в трёх отдельных locks.

Я проверил Docker Engine29.9.2/Compose5.6.1 на Linuxx86_64. Базы:
Python3.12.15-slim-bookworm digest6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70;
PostgreSQL16.15-bookworm digestd81f7b51697014367236d07ec58b54153fc28f828b72bf247fe5c7487520bcb0;
Caddy2.11.7-alpine digesteb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f.
Я копирую PostgreSQL16 tools/libpq из закреплённого stage; OS support libraries
устанавливаю из Debian bookworm и сохраняю dpkg inventory в os-packages.txt image.

Официальные источники:
[Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html),
[Waitress3.0.2](https://pypi.org/project/waitress/),
[Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy),
[Compose services](https://docs.docker.com/reference/compose-file/services/),
[pg_dump16](https://www.postgresql.org/docs/16/app-pgdump.html),
[Backup/restore16](https://www.postgresql.org/docs/16/backup.html).
Я не переношу подтверждение Linux на другую ОС и не называю local HTTP готовым TLS.
