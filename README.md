# CommerceGuard

**Я разрабатываю учебную ИС сверки заказов, оплат и возвратов интернет-магазина.**

Я хочу объяснять финансовому специалисту расхождения между OMS и платёжным
провайдером, показывать происхождение каждой суммы и сохранять историю разбора.
Сценарий приближен к бизнес-запросу; реального клиента и коммерческого опыта
этому проекту не приписываю. Все примеры синтетические, финансовые операции не выполняю.

**26.10.2026: S3/CG-303, `0.1.0.dev13`. Я добавил локальную оркестрацию и подтвердил основной
сквозной сценарий на Linux. Продукт ещё в разработке, полной приёмки нет.**

Я выполнил 38 Python tests в analytics и orchestration окружениях. Временный
Prefect flow прошёл полный путь, точный повтор, permanent PSP conflict, preflight
отказ, ограниченные retry, сбой marts и CLI resume. SHA отчёта сохранился.
Построил 9 dbt models и выполнил 19 data tests. Проверки старого контура и
точные границы — [VALIDATION](VALIDATION.md). CI/Windows пока не проверял,
стабильный релиз не создавал.

## Что я уже написал

| Часть | Текущее поведение | Граница |
| --- | --- | --- |
| Приём | OMS v1/v2 CSV, PSP v1 JSONL, строгий manifest, frozen input, raw, COPY, публикация целого пакета, receipts | Отказы/replay проверил; нагрузку и аварийный COMMIT ещё нет |
| Сверка | Отдельные capture/refund, два времени, per-leg deadlines/states, manifest/result v3, evidence и corrections | Исторические отчёты immutable; старый executor не поставляется автоматически |
| Кейсы | Явный canonical apply, revision/event history, old retry noop, correction report-only | HTTP, роли, назначения и ручное закрытие ещё впереди |
| Settlement | Явный business batch/revision/membership, gross/refund/fee/net, независимый тариф, unknown и evidence | Один тариф на gross; банковский settlement/FX и распределение fee по заказам ещё не моделирую |
| Аналитика | 9 dbt моделей, объявленное зерно, pre-aggregation перед JOIN, order/currency/settlement reports | Не выбираю latest и не складываю ревизии одного пакета |
| Оркестрация | Prefect run/resume, frozen inputs, fixed cutoff, bounded retry и safe failure summary | Временный loopback backend, без Cloud/schedule; отдельного durable flow journal ещё нет |
| Хранение | Schema 9, 24 persistent tables и 9 аналитических views | Core не обновляю из dbt; локальные данные в Git не включаю |

## Как я предлагаю читать проект

1. [START_HERE](START_HERE.md) — маршрут по коду и команды проверок.
2. [PROGRESS](docs/PROGRESS.md) — таблица этапов и расстояние до исходного объёма.
3. [PROJECT_MAP](docs/PROJECT_MAP.md) — где менять каждый слой.
4. [ORCHESTRATION](docs/ORCHESTRATION.md) — текущий срез: шаги, ошибки/повторы, команды и пять заданий.
   [SETTLEMENT](docs/SETTLEMENT.md) — перечисления: формулы, контракт и карта кода.
   [MARTS](docs/MARTS.md) — SQL-контур: граф, зерно, поля, решения и задания.
5. [DEADLINES](docs/DEADLINES.md), [LATE_DATA](docs/LATE_DATA.md), [CASES](docs/CASES.md) — предметные контракты.
6. [TECHNOLOGIES](TECHNOLOGIES.md), [DECISIONS](DECISIONS.md), [VALIDATION](VALIDATION.md) — зависимости, причины и факты проверок.

## Как я запускаю проверки

Я получаю текущие исходники отдельной веткой, затем перехожу в commerceguard:

```bash
git clone --branch codex/s3-cg303-local-flow --single-branch https://github.com/Decl1s/commerceguard.git
cd commerceguard
```

В корне этого репозитория, с Python 3.12.15:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-analytics.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m commerceguard demo
.venv/bin/python scripts/check_postgres.py --pg-bin /usr/lib/postgresql/16/bin
```

Для последней команды нужны уже доступные PostgreSQL 16 binaries и обычный
пользователь ОС. Runner сам создаёт одноразовую БД, генерирует примеры, проходит
ingest→run→case→settlement→dbt и затем останавливает/удаляет свой кластер, включая при ошибке.
TCP не открывает и к существующим БД не подключается. Команду с `--pg-bin`
я проверил на Linux; перенос на Windows не объявляю выполненным.

Для нового flow я дополнительно создаю отдельное окружение, сохраняя analytics .venv:

```bash
python3.12 -m venv .venv-orchestration
.venv-orchestration/bin/python -m pip install --require-hashes -r requirements-orchestration.lock
.venv-orchestration/bin/python scripts/check_pipeline.py --pg-bin /usr/lib/postgresql/16/bin
```

Новый runner также создаёт и удаляет только свою PostgreSQL без TCP, а Prefect
на время команды открывает loopback backend и останавливает его. Пошаговый
`pipeline run/resume` по своей БД, все аргументы и упражнения — ORCHESTRATION.
Никаких постоянных служб эти команды не устанавливают.

Отдельный запуск dbt по уже подготовленной своей БД и переменные соединения —
[MARTS](docs/MARTS.md). Я не кладу пароль в profiles.yml. Локальный core-only набор
requirements-postgres.lock сохраняю отдельно; в этом срезе устанавливал analytics lock.

## Насколько я близко к завершению

Я написал 15 из 30 исходных историй: S0 (2), S1 (5), S2 (5), S3 (3).
Это **50% количества историй**, не процент готовности и не оценка оставшихся часов.
Остаются 15: S3 — 2, S4 — 5, S5 — 5, S6 — 3. До первого рабочего места аналитика
по плану ещё 7 историй S3/S4; затем остаётся эксплуатация и итоговая передача.
Часть старых сценариев теперь проверена, полной проверки всех S1/S2 нет.
Точные границы я сохраняю в PROGRESS и VALIDATION.

## Как я веду работу

Я использую Scrum + Kanban: цель этапа, упорядоченный backlog, WIP 1, конкретный
срез в Draft PR, фактические проверки и журнал. PR не сливаю автоматически.
Следующий срез — CG-304: freshness/completeness источников.
[CG-303 #29](https://github.com/Decl1s/commerceguard/issues/29) реализовал и проверил;
я опубликовал его в [Draft PR #30](https://github.com/Decl1s/commerceguard/pull/30).
CG-304 [#31](https://github.com/Decl1s/commerceguard/issues/31) — Ready; CG-302 остаётся Review.
Ежедневные мини-проекты веду отдельно. Публичный состав — [PUBLIC_FILES](PUBLIC_FILES.txt);
секреты, raw, БД, окружение и результаты dbt target/logs в него не входят.

Исходники CG-303 сохраняю в ветке `codex/s3-cg303-local-flow` поверх
[CG-302 #28](https://github.com/Decl1s/commerceguard/pull/28).
Я опубликовал срез в [Draft PR #30](https://github.com/Decl1s/commerceguard/pull/30).
[Истории](https://github.com/Decl1s/commerceguard/issues).
