# Официальные источники

## CG-102, обращение 24.10.2026

- [Python 3.12 csv](https://docs.python.org/3.12/library/csv.html): reader,
  newline='', dialect и ограничение полей.
- [Python 3.12 json](https://docs.python.org/3.12/library/json.html): object_pairs_hook,
  parse_int/parse_float/parse_constant; строгая политика — наш контракт.
- [Python 3.12 tempfile](https://docs.python.org/3.12/library/tempfile.html):
  TemporaryFile и жизненный цикл временного файла.
- [Python 3.12 io](https://docs.python.org/3.12/library/io.html): бинарные/текстовые
  потоки и TextIOWrapper. Эти свойства не доказывают корректность нашего parser.

Дата обращения к основным материалам: 24.10.2026. Пересказ своими словами;
бизнес-правила магазина придуманы для учебного запроса, не взяты из стандарта.

## Основа процесса и текущего кода

- [Scrum Guide, 2020](https://scrumguides.org/scrum-guide.html): Product Goal,
  Sprint Goal, артефакты, review/retrospective и роль Definition of Done.
- [Kanban Guide for Scrum Teams](https://www.scrum.org/resources/kanban-guide-scrum-teams):
  дополнение Scrum практиками управления потоком; наши WIP и состояния — локальная политика.
- [Python 3.12 dataclasses](https://docs.python.org/3.12/library/dataclasses.html):
  frozen, slots и отсутствие автоматической проверки аннотаций типов.
- [Python 3.12 datetime](https://docs.python.org/3.12/library/datetime.html): aware/naive,
  timezone и сравнение времени; запрет naive дат — наш контракт.
- [enum](https://docs.python.org/3.12/library/enum.html): StrEnum.
- [collections](https://docs.python.org/3.12/library/collections.html): defaultdict.
- [hashlib](https://docs.python.org/3.12/library/hashlib.html): SHA-256.
- [json](https://docs.python.org/3.12/library/json.html): сериализация ключа и отчёта.
- [argparse](https://docs.python.org/3.12/library/argparse.html): CLI.
- [sys](https://docs.python.org/3.12/library/sys.html),
  [io.TextIOWrapper](https://docs.python.org/3.12/library/io.html#io.TextIOWrapper): stdout/reconfigure.
- [re](https://docs.python.org/3.12/library/re.html),
  [typing](https://docs.python.org/3.12/library/typing.html): ограничения идентификаторов и интерфейсы.
- [Git documentation](https://git-scm.com/docs): самостоятельная история и ветки.
- [VS Code workspaces](https://code.visualstudio.com/docs/editing/workspaces/workspaces): окно навигации.
- [GitHub Markdown](https://docs.github.com/en/get-started/writing-on-github): документы/диаграммы.
- [TOML specification](https://toml.io/en/v1.0.0): формат метаданных.

## Целевая архитектура: не список установленных библиотек

- [PostgreSQL 16 transaction isolation](https://www.postgresql.org/docs/16/transaction-iso.html):
  различие READ COMMITTED и REPEATABLE READ. Выбор границы T3 — наше решение.
- [PostgreSQL COPY](https://www.postgresql.org/docs/16/sql-copy.html): будущее staging-поступление.
- [Psycopg 3](https://www.psycopg.org/psycopg3/docs/): будущий адаптер БД.
- [dbt documentation](https://docs.getdbt.com/docs/introduction): будущие модели и ref/lineage.
- [Prefect documentation](https://docs.prefect.io/v3/get-started): будущее управление потоком.
- [FastAPI](https://fastapi.tiangolo.com/), [Jinja2](https://jinja.palletsprojects.com/): будущее рабочее место.

Свойства библиотеки из документации не доказывают корректность нашего использования.
Ни наличие источника, ни архитектурная диаграмма не означают проведённых проверок.

## CG-101, обращение 24.10.2026

- [Psycopg 3.3.6 transactions, исходник закреплённого тега](https://github.com/psycopg/psycopg/blob/3.3.6/docs/basic/transactions.rst):
  явная транзакция, autocommit и SAVEPOINT. Основной сайт уже показывает 3.3.7.dev1;
  закреплённая зависимость остаётся 3.3.6.
- [Psycopg SQL composition](https://www.psycopg.org/psycopg3/docs/api/sql.html):
  разделение параметров и идентификаторов; наши имена схем/таблиц статические.
- [PostgreSQL advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS),
  [REVOKE](https://www.postgresql.org/docs/16/sql-revoke.html): lock и ACL собственной схемы.
- Реестр и pinned metadata:
  [psycopg 3.3.6](https://pypi.org/pypi/psycopg/3.3.6/json),
  [psycopg-binary 3.3.6](https://pypi.org/pypi/psycopg-binary/3.3.6/json),
  [typing_extensions 4.15.0](https://pypi.org/pypi/typing_extensions/4.15.0/json),
  [tzdata 2026.2](https://pypi.org/pypi/tzdata/2026.2/json).
  Отсюда взяты версии и Python-транзитивные зависимости; install/resolver не запускались.

## CG-103, обращение 24.10.2026

- [Psycopg 3.3.6 COPY, исходник тега](https://github.com/psycopg/psycopg/blob/3.3.6/docs/basic/copy.rst):
  copy context/write_row, адаптация Python-значений, транзакционная граница;
  write_row не сочетается с ручными FORMAT CSV/DELIMITER/NULL опциями.
- [Psycopg 3.3.6 adaptation](https://github.com/psycopg/psycopg/blob/3.3.6/docs/basic/adapt.rst):
  Jsonb wrapper и преобразование UUID/timestamps; параметры вместо SQL-склейки.
- [PostgreSQL 16 COPY](https://www.postgresql.org/docs/16/sql-copy.html):
  STDIN — поток клиента, а не доступ сервера к имени файла.
- [PostgreSQL 16 advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS):
  transaction shared/exclusive locks и cooperative характер протокола.
- [Python 3.12 os.link/fsync](https://docs.python.org/3.12/library/os.html#os.link):
  hard links, платформенные ограничения и синхронизация файлов.
- [Python 3.12 uuid](https://docs.python.org/3.12/library/uuid.html#uuid.uuid5):
  детерминированный UUIDv5 и namespace. Это ссылка, не криптографическое доказательство.

Canonical envelope, temporal rejection и receipt-grain — наши проектные решения,
не готовые гарантии этих библиотек. Код не исполнялся, ОС/СУБД не проверялись.

## CG-104, обращение 24.10.2026

Я использовал [Psycopg 3.3.6 transaction contexts](https://github.com/psycopg/psycopg/blob/3.3.6/docs/basic/transactions.rst),
[PostgreSQL 16 advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS)
и [Python 3.12 os.scandir](https://docs.python.org/3.12/library/os.html#os.scandir).
Из документации взял границы транзакций, cooperative locks и no-follow тип файлов.
Whole-package quarantine и независимые attempts — мои решения, не готовые гарантии
библиотеки. Работоспособность своего применения пока не проверял.

## CG-202, обращение 24.10.2026

Я прочитал [Psycopg 3.3.6 cursors/executemany](https://github.com/psycopg/psycopg/blob/3.3.6/docs/api/cursors.rst)
и [PostgreSQL 16 constraints](https://www.postgresql.org/docs/16/ddl-constraints.html).
Я использую bound parameters, отдельные FK и явный application count; CHECK не
подменяет межтабличную полноту. Bounded JSON result и execution lifecycle — мои
проектные решения, не доказанная гарантия библиотеки. Исполнение не выполнял.

25.10.2026, CG-203: я прочитал официальные разделы PostgreSQL 16
[explicit locking](https://www.postgresql.org/docs/16/explicit-locking.html) и
[constraints](https://www.postgresql.org/docs/16/ddl-constraints.html), чтобы выбрать
transaction-level advisory lock, FK и deferred проверку circular ссылки.
Документация не заменяет запуск написанного SQL; его я не выполнял.

25.10.2026, CG-204: я использую официальные разделы
[Python 3.12 datetime](https://docs.python.org/3.12/library/datetime.html#aware-and-naive-objects)
и [PostgreSQL 16 isolation](https://www.postgresql.org/docs/16/transaction-iso.html)
для определения aware моментов и снимка read-only сравнения. Исторический commit
snapshot не вывожу из transaction_timestamp; marker limitation сохраняю в LATE_DATA.

25.10.2026, CG-205: я прочитал официальный раздел
[PostgreSQL 16: Modifying Tables](https://www.postgresql.org/docs/16/ddl-alter.html).
Я использую constant default для legacy version и nullable deadline columns,
отдельно задаю CHECK/composite FK. Документация объясняет механизм ALTER TABLE,
но не подтверждает написанные имена constraints или применимость миграции 0008:
я её не выполнял. Бизнес-политика deadlines и Case upgrade — моё решение ADR-26.

25.10.2026, CG-301: я проверил официальные
[dbt-postgres setup](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup),
[ref](https://docs.getdbt.com/reference/dbt-jinja-functions/ref),
[data tests](https://docs.getdbt.com/docs/build/data-tests),
[dbt-core 1.12.6](https://pypi.org/project/dbt-core/1.12.6/) и
[dbt-postgres 1.11.0](https://pypi.org/project/dbt-postgres/1.11.0/).
Я учитываю доступность dbt v2, но здесь закрепил и фактически построил v1 SQL-проект.
Версии прямых/transitive пакетов — requirements-analytics.lock; resolver и sync
выполнил в отдельной .venv, hashes проверены. Документация объясняет инструменты,
выбор grain/NULL/scope — моё проектное решение ADR-28.

## CG-302 · 26.10.2026

Я сверил официальные [PostgreSQL16 LATERAL](https://www.postgresql.org/docs/16/queries-table-expressions.html#QUERIES-LATERAL)
и [INSERT/ON CONFLICT](https://www.postgresql.org/docs/16/sql-insert.html).
Использую их для выбора одного видимого receipt и защиты повторного assignment.
Правило gross-bps-half-up-v1/полнота advice — мои учебные контракты; внешнему
провайдеру их не приписываю. Новых библиотек и тарифных API не подключаю.
