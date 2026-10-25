# Таблица этапов CommerceGuard

Обновлено 25.10.2026. Здесь фиксируется факт написания, а не неподтверждённая
работоспособность. Я пока не запускаю программу и проверки.
Задачи — [Kanban](KANBAN.md), хронология — [WORKLOG](WORKLOG.md).

| Этап | Состояние | Что сделано | Что дальше |
| --- | --- | --- | --- |
| S0 — основа | Написано, Review | PRD, архитектура, контракты, 30 историй, 12 первоначальных ADR, ядро сверки, конспект и задания | Материалы в Draft PR #1; приёмка не выдумывается |
| S1 — приём и хранение | CG-101…105 написаны, Review/unverified | Схема 10 таблиц, parser/raw/COPY/publish, receipts, attempts/quarantine/recovery, status и синтетический генератор | Материалы S1 доступны; переход к S2 без фиктивной приёмки |
| S2 — сохранённая сверка | CG-201…205 написаны, Review/unverified | Я написал manifest/result, evidence, кейсы, два времени, OMS v2 и раздельные сроки; ничего не исполнял | Review, без фиктивной приёмки |
| **S3 — контур данных, следующий** | **CG-301 Ready; реализацию не начинал** | Я определил вход: завершённые immutable run, currency и grain | **CG-301: dbt staging/core marts**, затем settlement, оркестрация и свежесть |
| S4 — рабочее место | Запланирован | Есть сценарии и роли | Список/карточка, сессии, назначения, закрытие и аудит |
| S5 — эксплуатация | Запланирован | Есть проектный runbook и риски | Backfill, recovery, метрики и локальная поставка |
| S6 — портфолио | Запланирован | Стартовый публичный репозиторий и навигация | Сквозная демонстрация, руководства и итоговое оформление |

## Срезы с фактической датой

| Дата | Истории | Артефакт | Факт исполнения |
| --- | --- | --- | --- |
| 24.10.2026 | CG-001/002 | [S0](sprints/S0.md), [Draft PR #1](https://github.com/Decl1s/commerceguard/pull/1) | Не запускалось |
| 24.10.2026 | CG-101 | [S1](sprints/S1.md), [миграции и схема](STORAGE.md), [Draft PR #10](https://github.com/Decl1s/commerceguard/pull/10) | Написано; PostgreSQL не подключался, SQL не применялся, зависимости не устанавливались |
| 24.10.2026 | CG-102 | [Контракт и parser](INPUTS.md), [Draft PR #11](https://github.com/Decl1s/commerceguard/pull/11) | Написано без запуска parser, inspect, тестов или CI |
| 24.10.2026 | CG-103 | [Путь публикации и карта кода](INGESTION.md), [Draft PR #12](https://github.com/Decl1s/commerceguard/pull/12) | Написано без запуска raw store, COPY, CLI, SQL, тестов или CI |
| 24.10.2026 | CG-104 | [Журнал и восстановление](RECOVERY.md), [Draft PR #13](https://github.com/Decl1s/commerceguard/pull/13) | Я написал код без исполнения; SQL, raw scan, recovery и проверки не запускал |
| 24.10.2026 | CG-105 | [Маршрут и параметры](WORKBENCH.md), [Draft PR #14](https://github.com/Decl1s/commerceguard/pull/14) | Я написал генератор и status; команды и проверки не запускал |
| 24.10.2026 | CG-201 | [Manifest запуска](RUN_MANIFEST.md), [Draft PR #16](https://github.com/Decl1s/commerceguard/pull/16) | Я написал selector/manifest и SQL; prepare/show и проверки не запускал |
| 24.10.2026 | CG-202 | [Результат и происхождение](RESULTS.md), [Draft PR #18](https://github.com/Decl1s/commerceguard/pull/18) | Я написал execute/result/evidence и SQL, без запуска |

Ежедневные мини-проекты ведутся отдельно; их автоматизация не изменена.

## 25.10.2026 — CG-203

| История | Что я написал | Публикация | Исполнение |
| --- | --- | --- | --- |
| CG-203 | [Case/application/stream/revision/event и CLI](CASES.md), миграция 0006, порядок run и пять упражнений | [Draft PR #20](https://github.com/Decl1s/commerceguard/pull/20) | Я не запускал исходники, SQL и проверки |

## 25.10.2026 — CG-204

| История | Что я написал | Публикация | Исполнение |
| --- | --- | --- | --- |
| CG-204 | [Два времени, reason/baseline, run changes и visible evidence](LATE_DATA.md), миграция 0007 | [Draft PR #22](https://github.com/Decl1s/commerceguard/pull/22) | Я не запускал исходники, SQL и проверки |

### Навигация по текущему коду

Я актуализировал START_HERE и ARCHITECTURE для CG-205: 20 таблиц, schema 8,
два времени, раздельные сроки, result v3 и явный переход Case policy. В [PROJECT_MAP](PROJECT_MAP.md)
собрал все Python-модули, миграции, маршруты изменений и пять задач для чтения.
Эта работа над документацией не добавляет выполненных проверок приложения.

## 25.10.2026 — CG-205

| История | Что я написал | Публикация | Исполнение |
| --- | --- | --- | --- |
| CG-205 | [OMS v2, сроки двух плеч, balance-v2, manifest/result v3 и явный Case upgrade](DEADLINES.md), миграция 0008, split-deadlines и пять упражнений | [Draft PR #24](https://github.com/Decl1s/commerceguard/pull/24), ветка `codex/s2-cg205-expectation-deadlines` | Я не запускал исходники, генератор, SQL и проверки |

Я написал все пять историй S2; это факт наличия исходников, не приёмка спринта.
WIP 1 освобождаю после публикации; CG-301 остаётся Ready, dbt пока не добавлен.

Следующая Ready история: [CG-301 #25](https://github.com/Decl1s/commerceguard/issues/25).
