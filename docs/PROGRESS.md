# Таблица этапов CommerceGuard

Обновлено 24.10.2026. Здесь фиксируется факт написания, а не неподтверждённая
работоспособность. Я пока не запускаю программу и проверки.
Задачи — [Kanban](KANBAN.md), хронология — [WORKLOG](WORKLOG.md).

| Этап | Состояние | Что сделано | Что дальше |
| --- | --- | --- | --- |
| S0 — основа | Написано, Review | PRD, архитектура, контракты, 30 историй, 12 первоначальных ADR, ядро сверки, конспект и задания | Материалы в Draft PR #1; приёмка не выдумывается |
| S1 — приём и хранение | CG-101…105 написаны, Review/unverified | Схема 10 таблиц, parser/raw/COPY/publish, receipts, attempts/quarantine/recovery, status и синтетический генератор | Материалы S1 доступны; переход к S2 без фиктивной приёмки |
| **S2 — сохранённая сверка, текущий** | **CG-201/202 написаны, Review/unverified** | Я написал manifest, bounded расчёт, immutable result и raw evidence; ничего не исполнял | **CG-203: кейсы и ревизии**, затем late data |
| S3 — контур данных | Запланирован | Есть цели и истории | dbt, Prefect, settlement и свежесть |
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
