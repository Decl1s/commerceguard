# Kanban: текущее состояние

Обновлено 24.10.2026. Product Goal — объяснимая сверка денежных потоков и история
разбора. Текущий этап — S1, первый срез CG-101 написан. [Таблица фактов](PROGRESS.md).
Доска ведётся здесь как часть Git; GitHub Issues служат
обсуждению историй. GitHub Projects board не объявляется созданным без фактического создания.

| Backlog | Ready | In progress · WIP 1 | Authored · WIP 2 | Review | Accepted |
| --- | --- | --- | --- | --- | --- |
| CG-103…105: приём полного пакета | CG-102: контракты и manifest | — | — | CG-001: план/контракты/архитектура | — |
| CG-201…205: сохранённая сверка | — | — | — | CG-002: предметное ядро, **unverified** | — |
| CG-301…305: dbt/Prefect/settlement | — | — | — | — | — |
| CG-401…405: рабочее место | — | — | — | — | — |
| CG-501…505: эксплуатация | — | — | — | — | — |
| CG-601…603: портфолио | — | — | — | — | — |
| — | — | — | — | CG-101: схема и мигратор, **unverified** | — |

Срезы S0 подготовлены для обсуждения; пользователь ещё не принимал их.
Статус Review не означает запуск или корректность. Никакой «100% готовности».

## Карточки в GitHub

| История | Карточка | Состояние |
| --- | --- | --- |
| CG-001: основа продукта | [#2](https://github.com/Decl1s/commerceguard/issues/2) | Review |
| CG-002: ядро | [#4](https://github.com/Decl1s/commerceguard/issues/4) | Review, unverified |
| CG-101: схема PostgreSQL | [#5](https://github.com/Decl1s/commerceguard/issues/5) | Review, unverified |
| CG-102: manifest | [#6](https://github.com/Decl1s/commerceguard/issues/6) | Ready |
| CG-103: публикация | [#7](https://github.com/Decl1s/commerceguard/issues/7) | Backlog |
| CG-104: карантин/recovery | [#8](https://github.com/Decl1s/commerceguard/issues/8) | Backlog |
| CG-105: CLI | [#9](https://github.com/Decl1s/commerceguard/issues/9) | Backlog |
| Эпик S1–S6 | [#3](https://github.com/Decl1s/commerceguard/issues/3) | План |

Материалы S0: [Draft PR #1](https://github.com/Decl1s/commerceguard/pull/1).
Карточки не закрывались автоматически; полный backlog из 30 историй остаётся
единой спецификацией. Markdown-доска — текущее каноническое состояние потока.

## Следующий pull

CG-102 — контракты файлов OMS CSV / PSP JSONL, manifest и bounded parser.
Ровно одна история, без COPY/публикации (CG-103), UI и оркестратора.
Сначала читать sprints/S1.md, STORAGE, DATA_CONTRACTS и ADR-13/14.

## Ограничения

Запрет исполнения действует на все следующие срезы. Это ограничение в VALIDATION,
а не основание игнорировать разработку. Инструкции мини-проектов об обязательных
тестах не должны перенести запуск в этот проект. Будущее изменение объёма фиксировать
в BACKLOG и WORKLOG; не создавать параллельно «улучшенную версию» той же ИС.
