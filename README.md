# CommerceGuard

**Я разрабатываю учебную информационную систему сверки заказов, оплат и возвратов интернет-магазина.**

Я хочу объяснять финансовому специалисту расхождения между ожиданиями OMS и фактами платёжного провайдера, показывать источник каждой суммы и сохранять историю разбора. Сценарий приближен к бизнес-задаче; реального клиента, коммерческого опыта и финансовых операций этому проекту не приписываю. Все входы синтетические.

**25.10.2026: S2, CG-201…205 написаны, версия 0.1.0.dev10. Приложение, SQL, миграции, проверки, сборку и CI я не запускал. Исходники unverified, производственную готовность и приёмку не заявляю.**

[Открыть текущие исходники](https://github.com/Decl1s/commerceguard/tree/codex/s2-cg205-expectation-deadlines) · [Текущий Draft PR #24](https://github.com/Decl1s/commerceguard/pull/24) · [Таблица этапов](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/PROGRESS.md)

## С чего я предлагаю начать

1. [Маршрут на 10 минут](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/START_HERE.md): бизнес-пример, порядок чтения и workspace редактора.
2. [Единая карта кода](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/PROJECT_MAP.md): ответственность всех модулей, миграции и места для изменений.
3. [Архитектура](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/ARCHITECTURE.md) и [решения](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/DECISIONS.md): движение данных, COMMIT, повторы и компромиссы.
4. [Кейсы и ревизии](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/CASES.md), [поздние данные и два времени](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/LATE_DATA.md): подробный разбор с десятью упражнениями и ожидаемыми ответами.

## На каком этапе я нахожусь

| Этап | Что я написал | Состояние |
| --- | --- | --- |
| S0 | Бизнес-запрос, контракты, ядро и план шести спринтов | Review/unverified, Draft PR #1 |
| S1 / CG-101…105 | Файловый контракт, raw/COPY/publish, receipts, attempts/quarantine/recovery, генератор и status | Review/unverified |
| S2 / CG-201…205 | Immutable manifests/results/evidence, Case history, temporal corrections, OMS v2 и раздельные сроки | Review/unverified |
| CG-301 | SQL-витрины завершённых run, grain, отдельная pre-aggregation и currency | Следующий Ready, [#25](https://github.com/Decl1s/commerceguard/issues/25); реализацию не начинал |
| S3 | Settlement, dbt, Prefect, витрины и свежесть | План |
| S4 | Веб-рабочее место, роли, назначения, комментарии и ручное закрытие | План |
| S5/S6 | Эксплуатация и итоговая демонстрация | План |

Я использую Python 3.12, PostgreSQL 16 и Psycopg 3.3.6; новые библиотеки добавляю по задаче. Сейчас написал schema 8 и 20 persistent tables. Денежные плечи считаю отдельно, валюты не суммирую, неизвестность сохраняю как null.

В CG-203 я отделил карточку от результата: старая попытка не меняет актуальный head, изменение суммы даёт ревизию, исчезновение finding сохраняется событием и не означает ручное закрытие. [Draft PR #20](https://github.com/Decl1s/commerceguard/pull/20).

В CG-204 я разделил business cutoff и knowledge cutoff: поздний факт может изменить новый отчёт о старой дате, а исходный отчёт остаётся неизменяемым. Сохраняю reason/baseline, показываю raw lineage и изменение движка. Историческая корректировка пока report-only для текущих Case. [Draft PR #22](https://github.com/Decl1s/commerceguard/pull/22).

В CG-205 я разделил сроки capture/refund и сохраняю состояния каждого плеча. OMS v1 читаю без смены его identity; новый manifest/result v3 закрепляет версии входов и balance-v2. Переход существующего Case stream требует явного current head. [Draft PR #24](https://github.com/Decl1s/commerceguard/pull/24), [подробный разбор и пять упражнений](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/DEADLINES.md). Старые результаты не переписываю, приложение и SQL не запускал.

## Как я веду проект

Я адаптирую Scrum и Kanban для личного учебного проекта: цель спринта, упорядоченный backlog, одна активная история, конкретный срез в Draft PR и фактический журнал. Командные встречи, внешнюю приёмку и результаты выполнения не выдумываю. [Доска](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/KANBAN.md), [backlog](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/BACKLOG.md), [журнал](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg205-expectation-deadlines/docs/WORKLOG.md).

Я сохраняю main как навигацию по опубликованным исходникам в ветках codex/. Draft PR автоматически не сливаю; стабильный релиз непроверенного кода не создаю. История начала — [Sprint 0](https://github.com/Decl1s/commerceguard/tree/codex/sprint-0-foundation). Ежедневные мини-проекты веду отдельно от флагмана.
