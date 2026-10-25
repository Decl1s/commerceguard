# CommerceGuard

**Я разрабатываю учебную информационную систему сверки заказов, оплат и возвратов интернет-магазина.**

Я хочу объяснять финансовому специалисту расхождения между ожиданиями OMS и фактами платёжного провайдера, показывать источник каждой суммы и сохранять историю разбора. Сценарий приближен к бизнес-задаче; реального клиента, коммерческого опыта и финансовых операций этому проекту не приписываю. Все входы синтетические.

**25.10.2026: S2, CG-201…204 написаны, версия 0.1.0.dev9. Приложение, SQL, миграции, проверки, сборку и CI я не запускал. Исходники unverified, производственную готовность и приёмку не заявляю.**

[Открыть текущие исходники](https://github.com/Decl1s/commerceguard/tree/codex/s2-cg204-late-data) · [Текущий Draft PR #22](https://github.com/Decl1s/commerceguard/pull/22) · [Таблица этапов](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/PROGRESS.md)

## С чего я предлагаю начать

1. [Маршрут на 10 минут](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/START_HERE.md): бизнес-пример, порядок чтения и workspace редактора.
2. [Единая карта кода](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/PROJECT_MAP.md): ответственность всех модулей, миграции и места для изменений.
3. [Архитектура](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/ARCHITECTURE.md) и [решения](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/DECISIONS.md): движение данных, COMMIT, повторы и компромиссы.
4. [Кейсы и ревизии](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/CASES.md), [поздние данные и два времени](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/LATE_DATA.md): подробный разбор с десятью упражнениями и ожидаемыми ответами.

## На каком этапе я нахожусь

| Этап | Что я написал | Состояние |
| --- | --- | --- |
| S0 | Бизнес-запрос, контракты, ядро и план шести спринтов | Review/unverified, Draft PR #1 |
| S1 / CG-101…105 | Файловый контракт, raw/COPY/publish, receipts, attempts/quarantine/recovery, генератор и status | Review/unverified |
| S2 / CG-201…204 | Immutable manifests/results/evidence, канонический поток Case, ревизии/события, temporal corrections и сравнение | Review/unverified |
| CG-205 | Версии ожиданий и раздельные сроки capture/refund | Следующий Ready, [#23](https://github.com/Decl1s/commerceguard/issues/23) |
| S3 | Settlement, dbt, Prefect, витрины и свежесть | План |
| S4 | Веб-рабочее место, роли, назначения, комментарии и ручное закрытие | План |
| S5/S6 | Эксплуатация и итоговая демонстрация | План |

Я использую Python 3.12, PostgreSQL 16 и Psycopg 3.3.6; новые библиотеки добавляю по задаче. Сейчас написал schema 7 и 20 persistent tables. Денежные плечи считаю отдельно, валюты не суммирую, неизвестность сохраняю как null.

В CG-203 я отделил карточку от результата: старая попытка не меняет актуальный head, изменение суммы даёт ревизию, исчезновение finding сохраняется событием и не означает ручное закрытие. [Draft PR #20](https://github.com/Decl1s/commerceguard/pull/20).

В CG-204 я разделил business cutoff и knowledge cutoff: поздний факт может изменить новый отчёт о старой дате, а исходный отчёт остаётся неизменяемым. Сохраняю reason/baseline, показываю raw lineage и изменение движка. Историческая корректировка пока report-only для текущих Case. [Draft PR #22](https://github.com/Decl1s/commerceguard/pull/22).

## Как я веду проект

Я адаптирую Scrum и Kanban для личного учебного проекта: цель спринта, упорядоченный backlog, одна активная история, конкретный срез в Draft PR и фактический журнал. Командные встречи, внешнюю приёмку и результаты выполнения не выдумываю. [Доска](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/KANBAN.md), [backlog](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/BACKLOG.md), [журнал](https://github.com/Decl1s/commerceguard/blob/codex/s2-cg204-late-data/docs/WORKLOG.md).

Я сохраняю main как навигацию по опубликованным исходникам в ветках codex/. Draft PR автоматически не сливаю; стабильный релиз непроверенного кода не создаю. История начала — [Sprint 0](https://github.com/Decl1s/commerceguard/tree/codex/sprint-0-foundation). Ежедневные мини-проекты веду отдельно от флагмана.
