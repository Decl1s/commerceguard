# CommerceGuard

**Учебная информационная система сверки заказов, оплат и возвратов интернет-магазина.**

Финансовый специалист должен видеть расхождения между ожиданиями OMS и фактами платёжного провайдера, происхождение каждой суммы и историю разбора кейса. Дата-инженер должен повторять загрузки и пересчитывать прошлый период без дубликатов и потери истории.

**24.10.2026: Sprint 1, срезы CG-101…103 написаны без исполнения. Код не запускался; тесты, сборка, линтеры, миграции и CI не выполнялись по указанию пользователя. Производственная готовность не заявляется.** Это учебный проект с синтетическими данными, без реальных клиентов и финансовых операций.

## Текущий этап

[Постоянная таблица прогресса](https://github.com/Decl1s/commerceguard/blob/codex/s1-cg103-atomic-ingestion/docs/PROGRESS.md)

| Этап | Что сделано | Следующий шаг |
| --- | --- | --- |
| S0 | Бизнес-запрос, контракты, архитектура, ядро сверки и план | Материалы в Draft PR #1 |
| **S1 / CG-101…103** | Схема 9 таблиц, миграции 0001/0002, manifest/parser, постоянный raw, staging/COPY, атомарная публикация и receipts; написано без запуска | **CG-104: карантин и восстановление** |

[Текущие исходники](https://github.com/Decl1s/commerceguard/tree/codex/s1-cg103-atomic-ingestion) · [Draft PR #12](https://github.com/Decl1s/commerceguard/pull/12)

[Подробный разбор приёма и аргументов](https://github.com/Decl1s/commerceguard/blob/codex/s1-cg103-atomic-ingestion/docs/INGESTION.md) · [Задания по CG-103](https://github.com/Decl1s/commerceguard/blob/codex/s1-cg103-atomic-ingestion/EXERCISES.md)

Разработка публикуется по небольшим этапам в ветках codex/ и Draft PR. Полные материалы первого этапа: **[ветка Sprint 0](https://github.com/Decl1s/commerceguard/tree/codex/sprint-0-foundation)**.

- [Карта кода и начало изучения](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/START_HERE.md)
- [Бизнес-запрос](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/docs/PRD.md)
- [План шести спринтов](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/docs/ROADMAP.md)
- [Kanban-доска](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/docs/KANBAN.md)
- [30 историй с критериями и зависимостями](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/docs/BACKLOG.md)
- [Архитектура](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/docs/ARCHITECTURE.md) и [решения](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/DECISIONS.md)
- [Подробный конспект](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/NOTES.md) и [задания](https://github.com/Decl1s/commerceguard/blob/codex/sprint-0-foundation/EXERCISES.md)

Направление стека: Python + PostgreSQL, затем dbt, Prefect и FastAPI/Jinja2 по мере появления задач. Сейчас предметное ядро использует только стандартную библиотеку Python 3.12.

Порядок поставки: атомарный приём → сохранённая сверка → витрины/оркестрация → рабочее место → эксплуатация → целостная демонстрация портфолио. Scrum задаёт цели спринтов, Kanban — последовательный поток с WIP=1. Это адаптация процесса для одного исполнителя; фиктивная команда и результаты приёмки не выдумываются.
