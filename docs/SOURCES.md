# Официальные источники

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
