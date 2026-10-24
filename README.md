# CommerceGuard

**Учебная информационная система сверки заказов, оплат и возвратов интернет-магазина.**

Я проектирую систему для финансового специалиста: он должен видеть расхождения между ожиданиями OMS и фактами платёжного провайдера, происхождение каждой суммы и историю разбора кейса. Дата-инженер должен повторять загрузки и пересчитывать прошлый период без дубликатов и потери истории.

**24.10.2026: Sprint 2, CG-201/202 написаны; S1/CG-101…105 тоже в Review. Код не запускался; тесты, сборка, линтеры, миграции и CI я пока не выполнял. Производственная готовность не заявляется.** Это учебный проект с синтетическими данными, без реальных клиентов и финансовых операций.

## Текущий этап

[Постоянная таблица прогресса](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg202-results-evidence/docs/PROGRESS.md)

| Этап | Что сделано | Следующий шаг |
| --- | --- | --- |
| S0 | Бизнес-запрос, контракты, архитектура, ядро сверки и план | Материалы в Draft PR #1 |
| S1 / CG-101…105 | Я написал parser/raw/COPY/publish, attempts/quarantine/recovery, status и генератор | Review/unverified |
| **S2 / CG-201/202** | Я написал immutable manifest, bounded сохранённую сверку и raw evidence; схема 15 таблиц | **CG-203: кейсы и ревизии** |

[Текущие исходники](https://github.com/Decl1s/commerceguard/tree/codex/s2-cg202-results-evidence) · [Draft PR #18](https://github.com/Decl1s/commerceguard/pull/18)

[Сохранённая сверка и происхождение](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg202-results-evidence/docs/RESULTS.md) · [Задания по CG-103](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg202-results-evidence/EXERCISES.md)

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
