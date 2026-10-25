# Таблица этапов CommerceGuard

25.10.2026. С CG-301 я включил проверки. Написанное, проверенное и принятое
разделяю: приложение ещё не завершено, Draft PR не равен внешней приёмке.

| Этап | Написано | Что подтверждено | Что осталось |
| --- | --- | --- | --- |
| S0 — продукт и ядро | 2/2 истории | Предметный пример и денежные инварианты в unit tests | Review документов, финальная сквозная демонстрация позже |
| S1 — приём и хранение | 5/5 | Миграции, parser/raw/COPY/publish, repeat и три whole-package отказа на Linux | Конкуренция, все recovery варианты, legacy upgrade и аварийные исходы |
| S2 — сверка и Case | 5/5 | Run replay, evidence, поздняя оплата/correction, case noop/history, input v1/v2 | Реальный legacy Case policy upgrade, расширенные fault/concurrency проверки |
| **S3 — контур данных, текущий** | **1/5: CG-301** | **8 dbt views, 13 data tests, pre-aggregation/currency/NULL, prepared exclusion** | **CG-302 settlement**, затем Prefect, freshness и catalog |
| S4 — рабочее место | 0/5 | Ещё нет | HTTP/UI, доступ, назначения, комментарии, закрытие/reopen, export |
| S5 — эксплуатация | 0/5 | Ещё нет | Backfill, backup/restore, метрики, поставка, индексы |
| S6 — портфолио/передача | 0/3 | Ещё нет | Итоговый demo, руководство изменения, публичная передача |

## Насколько я далеко от завершения

Я написал **13 из 30 историй (43% по количеству)**. Осталось **17 историй**:
4 в S3, 5 в S4, 5 в S5 и 3 в S6. Я не считаю эти задачи одинаковыми по трудоёмкости
и не выдаю 43% за долю времени или готовность продукта. Надёжной velocity пока нет.
До первого запланированного рабочего места аналитика остаются 9 историй S3/S4;
до полного исходного объёма — ещё эксплуатация и передача. Это оценка по backlog,
не обещание конкретной даты. Если scope изменится, я отдельно запишу новую границу.

## 25.10.2026 — CG-301 и включение проверок

Я написал [MARTS](MARTS.md), analytics/dbt_project.yml, 8 SQL models, ref DAG,
13 data tests, 15 Python unit tests и одноразовый integration runner. Нашёл и
исправил TypeError повторного чтения raw. Подтвердил 8 миграций и четыре сохранённых
run в сквозном пути. Полная матрица результатов/пробелов — [VALIDATION](../VALIDATION.md).
Новых core таблиц и миграций не добавлял: schema8/20 tables + 8 mart views.
Срез сохраняю в codex/s3-cg301-verified-marts, [Draft PR #26](https://github.com/Decl1s/commerceguard/pull/26).
Состояние Review, основной Linux сценарий проверен; CI не подключён, stable release нет.

## История срезов

| Дата | Истории | Публикация | Исходный статус |
| --- | --- | --- | --- |
| 24.10.2026 | CG-001/002 | [#1](https://github.com/Decl1s/commerceguard/pull/1) | Написано без исполнения |
| 24.10.2026 | CG-101…105 | [#10](https://github.com/Decl1s/commerceguard/pull/10), [#11](https://github.com/Decl1s/commerceguard/pull/11), [#12](https://github.com/Decl1s/commerceguard/pull/12), [#13](https://github.com/Decl1s/commerceguard/pull/13), [#14](https://github.com/Decl1s/commerceguard/pull/14) | Написано без исполнения |
| 24.10.2026 | CG-201/202 | [#16](https://github.com/Decl1s/commerceguard/pull/16), [#18](https://github.com/Decl1s/commerceguard/pull/18) | Написано без исполнения |
| 25.10.2026 | CG-203/204/205 | [#20](https://github.com/Decl1s/commerceguard/pull/20), [#22](https://github.com/Decl1s/commerceguard/pull/22), [#24](https://github.com/Decl1s/commerceguard/pull/24) | Написано без исполнения; текущие подтверждения выше |

Я сохраняю прежние PR и журнал WORKLOG. Новые проверки относятся к текущему
checkout, не ретроактивному исполнению старых коммитов. Ежедневные мини-проекты отдельно.

Следующая Ready карточка: [CG-302 #27](https://github.com/Decl1s/commerceguard/issues/27).
