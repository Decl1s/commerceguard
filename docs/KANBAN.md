# Kanban: текущее состояние

Обновлено 25.10.2026. Product Goal — объяснимая сверка денежных потоков и история
разбора. Я написал S1/CG-101…105 без исполнения. Сейчас S2/CG-201…204 написаны, следующим беру CG-205. [Таблица фактов](PROGRESS.md).
Доска ведётся здесь как часть Git; GitHub Issues служат
обсуждению историй. GitHub Projects board не объявляется созданным без фактического создания.

| Backlog | Ready | In progress · WIP 1 | Authored · WIP 2 | Review | Accepted |
| --- | --- | --- | --- | --- | --- |
| CG-301…305: контур данных | CG-205: сроки/ожидания | — | — | CG-001: план/контракты/архитектура | — |
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
| — | — | — | — | CG-203: кейсы и ревизии, **unverified** | — |
| — | — | — | — | CG-204: два времени и correction, **unverified** | — |

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

CG-205 — версии ожиданий и отдельные deadlines. Я уточняю OMS v2, совместимость
старых пакетов и сроков capture/refund; не переписываю immutable core и прошлые
results. Читаю DATA_CONTRACTS, INPUTS, LATE_DATA и ADR-25. Всё без запуска.

## Ограничения

Запрет исполнения действует на все следующие срезы. Это ограничение в VALIDATION,
а не основание игнорировать разработку. Инструкции мини-проектов об обязательных
тестах не должны перенести запуск в этот проект. Будущее изменение объёма фиксировать
в BACKLOG и WORKLOG; не создавать параллельно «улучшенную версию» той же ИС.

CG-103: raw, COPY, manifest identity, atomic publication и receipts — Review,
unverified; история #7 остаётся открытой. Приёмка и слияние PR не выполнялись.

CG-201: [карточка #15](https://github.com/Decl1s/commerceguard/issues/15), Review/unverified.

CG-202: [карточка #17](https://github.com/Decl1s/commerceguard/issues/17), Review/unverified.

CG-203: [карточка #19](https://github.com/Decl1s/commerceguard/issues/19), Review/unverified.


CG-204: [карточка #21](https://github.com/Decl1s/commerceguard/issues/21), Review/unverified.

CG-205: [карточка #23](https://github.com/Decl1s/commerceguard/issues/23), Ready.
