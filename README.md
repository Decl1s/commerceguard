# CommerceGuard

**Я разрабатываю учебную ИС сверки заказов, оплат и возвратов интернет-магазина.**

Я хочу объяснять финансовому специалисту расхождения между OMS и платёжным
провайдером, показывать происхождение каждой суммы и сохранять историю разбора.
Сценарий приближен к бизнес-запросу; реального клиента и коммерческого опыта
этому проекту не приписываю. Все примеры синтетические, финансовые операции не выполняю.

**26.10.2026: CG-402, `0.1.0.dev17`. Я добавил локальные аккаунты, роли и merchant scopes, серверные сессии, CSRF и отзыв доступа.**

Я написал 19/30 историй исходного backlog. Я прошёл70unit и PostgreSQL/HTTP integration: schema8→10 на данных, login/logout/disable, role/scope denial, Origin/CSRF, challenge replay, account throttle;dbtPASS28.
Проверки относятся к Linux; полной приёмки, CI и стабильного релиза пока нет.
Карта текущего среза, команды, решения и упражнения — [WORKPLACE](docs/WORKPLACE.md).
Таблицу этапов веду в [PROGRESS](docs/PROGRESS.md).

## Что я уже написал

| Часть | Текущее поведение | Граница |
| --- | --- | --- |
| Приём | OMS v1/v2 CSV, PSP v1 JSONL, строгий manifest, frozen input, raw, COPY, публикация целого пакета, receipts | Отказы/replay проверил; нагрузку и аварийный COMMIT ещё нет |
| Сверка | Отдельные capture/refund, два времени, per-leg deadlines/states, manifest/result v3, evidence и corrections | Исторические отчёты immutable; старый executor не поставляется автоматически |
| Кейсы | Явный canonical apply, revision/event history, old retry noop, correction report-only | HTTP, роли, назначения и ручное закрытие ещё впереди |
| Settlement | Явный business batch/revision/membership, gross/refund/fee/net, независимый тариф, unknown и evidence | Один тариф на gross; банковский settlement/FX и распределение fee по заказам ещё не моделирую |
| Аналитика | 9 dbt моделей, объявленное зерно, pre-aggregation перед JOIN, order/currency/settlement reports | Не выбираю latest и не складываю ревизии одного пакета |
| Оркестрация | Prefect run/resume, frozen inputs, fixed cutoff, bounded retry и safe failure summary | Временный loopback backend, без Cloud/schedule; отдельного durable flow journal ещё нет |
| Наблюдение источников | OMS/PSP/settlement, observed watermark, last success/attempt, completeness и явный timezone | Только чтение; максимум наблюдений не доказывает полноту внешнего источника |
| Хранение | Schema 9, 24 persistent tables и 9 аналитических views | Core не обновляю из dbt; локальные данные в Git не включаю |

## Как я предлагаю читать проект

1. [START_HERE](START_HERE.md) — маршрут по коду и команды проверок.
2. [PROGRESS](docs/PROGRESS.md) — таблица этапов и расстояние до исходного объёма.
3. [PROJECT_MAP](docs/PROJECT_MAP.md) — где менять каждый слой.
4. [FRESHNESS](docs/FRESHNESS.md) — текущий срез: времена, полнота, команды и пять заданий.
   [ORCHESTRATION](docs/ORCHESTRATION.md) — шаги потока, ошибки/повторы и продолжение.
   [SETTLEMENT](docs/SETTLEMENT.md) — перечисления: формулы, контракт и карта кода.
   [MARTS](docs/MARTS.md) — SQL-контур: граф, зерно, поля, решения и задания.
5. [DEADLINES](docs/DEADLINES.md), [LATE_DATA](docs/LATE_DATA.md), [CASES](docs/CASES.md) — предметные контракты.
6. [TECHNOLOGIES](TECHNOLOGIES.md), [DECISIONS](DECISIONS.md), [VALIDATION](VALIDATION.md) — зависимости, причины и факты проверок.

## Как я запускаю проверки

Я получаю текущие исходники отдельной веткой, затем перехожу в commerceguard:

```bash
git clone --branch codex/s3-cg304-source-health --single-branch https://github.com/Decl1s/commerceguard.git
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

Для чтения состояния своей подготовленной БД я использую явные учебные пороги:

```bash
.venv/bin/python -m commerceguard source health --merchant M01 --as-of now --business-timezone Europe/Moscow --max-age-seconds 86400 --late-after-seconds 3600
```

Пакет tzdata2026.5 входит в обновлённый analytics lock; одинаковую IANA базу читаю
из wheel на обеих средах. Значение подключения задаю внешней переменной, аргумент
--dsn-env при необходимости меняет её имя. Read-only команда не выполняет migrate.

## Насколько я близко к завершению

Я написал 16 из 30 исходных историй: S0 (2), S1 (5), S2 (5), S3 (4).
Это **53% количества историй**, не процент готовности и не оценка оставшихся часов.
Остаются 14: S3 — 1, S4 — 5, S5 — 5, S6 — 3. До первого рабочего места аналитика
по плану ещё 6 историй S3/S4; затем остаётся эксплуатация и итоговая передача.
Часть старых сценариев теперь проверена, полной проверки всех S1/S2 нет.
Точные границы я сохраняю в PROGRESS и VALIDATION.

## Как я веду работу

Я использую Scrum + Kanban: цель этапа, упорядоченный backlog, WIP 1, конкретный
срез в Draft PR, фактические проверки и журнал. PR не сливаю автоматически.
Следующий срез — CG-305: каталог показателей и происхождения данных.
CG-304 [#31](https://github.com/Decl1s/commerceguard/issues/31) реализовал и проверил;
я опубликовал его в [Draft PR #32](https://github.com/Decl1s/commerceguard/pull/32).
[CG-305 #33](https://github.com/Decl1s/commerceguard/issues/33) — Ready. Прежние срезы остаются Review.
Ежедневные мини-проекты веду отдельно. Публичный состав — [PUBLIC_FILES](PUBLIC_FILES.txt);
секреты, raw, БД, окружение и результаты dbt target/logs в него не входят.

Исходники CG-304 сохраняю в ветке `codex/s3-cg304-source-health` поверх
[CG-303 #30](https://github.com/Decl1s/commerceguard/pull/30).
Я опубликовал срез в [Draft PR #32](https://github.com/Decl1s/commerceguard/pull/32).
[Истории](https://github.com/Decl1s/commerceguard/issues).
