# Kanban: текущее состояние

Обновлено 24.10.2026. Product Goal — объяснимая сверка денежных потоков и история
разбора. Текущий этап — S1, CG-101…104 написаны. [Таблица фактов](PROGRESS.md).
Доска ведётся здесь как часть Git; GitHub Issues служат
обсуждению историй. GitHub Projects board не объявляется созданным без фактического создания.

| Backlog | Ready | In progress · WIP 1 | Authored · WIP 2 | Review | Accepted |
| --- | --- | --- | --- | --- | --- |
| — | CG-105: status и генератор | — | — | CG-001: план/контракты/архитектура | — |
| CG-201…205: сохранённая сверка | — | — | — | CG-002: предметное ядро, **unverified** | — |
| CG-301…305: dbt/Prefect/settlement | — | — | — | — | — |
| CG-401…405: рабочее место | — | — | — | — | — |
| CG-501…505: эксплуатация | — | — | — | — | — |
| CG-601…603: портфолио | — | — | — | — | — |
| — | — | — | — | CG-101: схема и мигратор, **unverified** | — |
| — | — | — | — | CG-102: manifest и parser, **unverified** | — |
| — | — | — | — | CG-103: raw/COPY/публикация, **unverified** | — |
| — | — | — | — | CG-104: карантин/recovery, **unverified** | — |

Я подготовил срезы S0 для review; выполнение и приёмку пока не подтверждал.
Статус Review не означает запуск или корректность. Никакой «100% готовности».

## Карточки в GitHub

| История | Карточка | Состояние |
| --- | --- | --- |
| CG-001: основа продукта | [#2](https://github.com/Decl1s/commerceguard/issues/2) | Review |
| CG-002: ядро | [#4](https://github.com/Decl1s/commerceguard/issues/4) | Review, unverified |
| CG-101: схема PostgreSQL | [#5](https://github.com/Decl1s/commerceguard/issues/5) | Review, unverified |
| CG-102: manifest | [#6](https://github.com/Decl1s/commerceguard/issues/6) | Review, unverified |
| CG-103: публикация | [#7](https://github.com/Decl1s/commerceguard/issues/7) | Review, unverified |
| CG-104: карантин/recovery | [#8](https://github.com/Decl1s/commerceguard/issues/8) | Review, unverified |
| CG-105: CLI | [#9](https://github.com/Decl1s/commerceguard/issues/9) | Ready |
| Эпик S1–S6 | [#3](https://github.com/Decl1s/commerceguard/issues/3) | План |

Материалы S0: [Draft PR #1](https://github.com/Decl1s/commerceguard/pull/1).
Карточки не закрывались автоматически; полный backlog из 30 историй остаётся
единой спецификацией. Markdown-доска — текущее каноническое состояние потока.

## Следующий pull

CG-105 — status по batch/attempt и воспроизводимый синтетический вход.
Я написал CG-104 без исполнения; перед продолжением читаю RECOVERY и ADR-20.
Recovery повторяет весь протокол, не снимает бизнес-конфликт и не удаляет raw.

## Ограничения

Запрет исполнения действует на все следующие срезы. Это ограничение в VALIDATION,
а не основание игнорировать разработку. Инструкции мини-проектов об обязательных
тестах не должны перенести запуск в этот проект. Будущее изменение объёма фиксировать
в BACKLOG и WORKLOG; не создавать параллельно «улучшенную версию» той же ИС.

CG-103: raw, COPY, manifest identity, atomic publication и receipts — Review,
unverified; история #7 остаётся открытой. Приёмка и слияние PR не выполнялись.
