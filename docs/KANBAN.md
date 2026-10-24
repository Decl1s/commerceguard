# Kanban: текущее состояние

Обновлено 24.10.2026. Product Goal — объяснимая сверка денежных потоков и история
разбора. Я написал S1/CG-101…105 без исполнения. Сейчас S2/CG-201/202 написаны, следующим беру CG-203. [Таблица фактов](PROGRESS.md).
Доска ведётся здесь как часть Git; GitHub Issues служат
обсуждению историй. GitHub Projects board не объявляется созданным без фактического создания.

| Backlog | Ready | In progress · WIP 1 | Authored · WIP 2 | Review | Accepted |
| --- | --- | --- | --- | --- | --- |
| CG-204/205: late data и сроки | CG-203: кейсы/ревизии | — | — | CG-001: план/контракты/архитектура | — |
| CG-301…305: контур данных | — | — | — | CG-002: предметное ядро, **unverified** | — |
| CG-301…305: dbt/Prefect/settlement | — | — | — | — | — |
| CG-401…405: рабочее место | — | — | — | — | — |
| CG-501…505: эксплуатация | — | — | — | — | — |
| CG-601…603: портфолио | — | — | — | — | — |
| — | — | — | — | CG-101: схема и мигратор, **unverified** | — |
| — | — | — | — | CG-102: manifest и parser, **unverified** | — |
| — | — | — | — | CG-103: raw/COPY/публикация, **unverified** | — |
| — | — | — | — | CG-104: карантин/recovery, **unverified** | — |
| — | — | — | — | CG-105: генератор/status, **unverified** | — |
| — | — | — | — | CG-201: immutable manifest, **unverified** | — |
| — | — | — | — | CG-202: result/evidence, **unverified** | — |

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
| CG-105: CLI | [#9](https://github.com/Decl1s/commerceguard/issues/9) | Review, unverified |
| Эпик S1–S6 | [#3](https://github.com/Decl1s/commerceguard/issues/3) | План |

Материалы S0: [Draft PR #1](https://github.com/Decl1s/commerceguard/pull/1).
Карточки не закрывались автоматически; полный backlog из 30 историй остаётся
единой спецификацией. Markdown-доска — текущее каноническое состояние потока.

## Следующий pull

CG-203 — кейсы и ревизии. Я читаю только опубликованные результаты, отделяю
finding snapshot от mutable Case и сохраняю историю изменений. Сначала определяю
канонический run/порядок применения, чтобы старый retry не открыл уже закрытый кейс.
Читаю RESULTS, DATA_CONTRACTS и ADR-07/23. Всё unverified, без запуска.

## Ограничения

Запрет исполнения действует на все следующие срезы. Это ограничение в VALIDATION,
а не основание игнорировать разработку. Инструкции мини-проектов об обязательных
тестах не должны перенести запуск в этот проект. Будущее изменение объёма фиксировать
в BACKLOG и WORKLOG; не создавать параллельно «улучшенную версию» той же ИС.

CG-103: raw, COPY, manifest identity, atomic publication и receipts — Review,
unverified; история #7 остаётся открытой. Приёмка и слияние PR не выполнялись.

CG-201: [карточка #15](https://github.com/Decl1s/commerceguard/issues/15), Review/unverified.

CG-202: [карточка #17](https://github.com/Decl1s/commerceguard/issues/17), Review/unverified.
