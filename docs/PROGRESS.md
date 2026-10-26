# Таблица этапов CommerceGuard

26.10.2026. Я продолжаю проверки с CG-301. Написанное, проверенное и принятое
разделяю: приложение ещё не завершено, Draft PR не равен внешней приёмке.

| Этап | Написано | Что подтверждено | Что осталось |
| --- | --- | --- | --- |
| S0 — продукт и ядро | 2/2 | Предметный пример и денежные инварианты в unit tests | Review документов, итоговый demo |
| S1 — приём и хранение | 5/5 | Миграции, parser/raw/COPY/publish, repeat и whole-package отказы на Linux | Конкуренция, все recovery варианты, legacy upgrade и аварийные исходы |
| S2 — сверка и Case | 5/5 | Run replay, evidence, late correction, case noop/history, input v1/v2 | Реальный legacy Case policy upgrade, расширенные fault/concurrency проверки |
| **S3 — контур данных, текущий** | **3/5: CG-301/302/303** | **Prefect normal/replay/retry/failure/resume; 38unit; 9views/19tests; settlement и schema8→9** | **CG-304 freshness**, затем catalog |
| S4 — рабочее место | 0/5 | Ещё нет | HTTP/UI, доступ, назначения, комментарии, закрытие/reopen, export |
| S5 — эксплуатация | 0/5 | Ещё нет | Backfill, backup/restore, метрики, поставка, индексы |
| S6 — портфолио/передача | 0/3 | Ещё нет | Итоговый demo, руководство изменения, публичная передача |

## Насколько я далеко от завершения

Я написал **15 из 30 историй (50% по количеству)**. Осталось **15 историй**:
2 в S3, 5 в S4, 5 в S5 и 3 в S6. Я не считаю эти задачи одинаковыми по трудоёмкости
и не выдаю 50% за долю времени или готовность продукта. Надёжной velocity пока нет.
До первого запланированного рабочего места аналитика остаются 7 историй S3/S4;
далее эксплуатация и передача. Это оценка backlog, не обещание даты.

## 26.10.2026 — CG-303: локальная оркестрация

Я написал pipeline run/resume, отдельные Prefect tasks, preflight frozen inputs,
cutoff после ingest и allowlist retry. Fail не публикует общий success; сохранённый
report остаётся доступен. Текущий source branch codex/s3-cg303-local-flow поверх
CG-302#28, issueCG-303#29. Публикацию фиксирую после завершения проверки состава.

Я прошёл38unit в двух окружениях и реальный Prefect3.8.8/PG16.15 flow: normal,
точный replay, partial OMS success/PSP conflict, bad bytes preflight, injected
transient2attempts/limit3attempts, marts failure и CLI resume. Dbт9models/19tests.
Временные backend остановил/удалил, SHA result сохранился. В ORCHESTRATION — карта,
команды, аргументы и5упражнений. Schema9/24tables неизменна. Следующий CG-304.

## 26.10.2026 — CG-302: перечисление и комиссия

Я добавил business settlement отдельно от доставки файла: immutable advice revision,
точный список PSP events, защита от двойного назначения, независимо заданный tariff,
четыре суммы и доказательства по receipt/raw. Неполнота даёт unknown/NULL, полный
пустой пакет — нули. Позднее событие видно новому cutoff, старый report не меняю.
Карта кода, аргументы, решения и пять заданий — [SETTLEMENT](SETTLEMENT.md).

Фактически прошли 27 Python tests, миграции1…9 и upgrade заполненной схемы8→9,
11 settlement reports/9 advice revisions, 9 dbt models+19 data tests (PASS28).
Четыре прежних order results сохранили SHA. Теперь schema9/24 tables+9views.
Область проверки — Linux/PostgreSQL16.15; CI/Windows/concurrency/power loss нет.
Ветка codex/s3-cg302-settlement поверх [Draft PR #26](https://github.com/Decl1s/commerceguard/pull/26).
Карточка [CG-302 #27](https://github.com/Decl1s/commerceguard/issues/27) — Review;
срез опубликован в [Draft PR #28](https://github.com/Decl1s/commerceguard/pull/28).

## История срезов

| Дата | Истории | Публикация | Исходный статус |
| --- | --- | --- | --- |
| 24.10.2026 | CG-001/002 | [#1](https://github.com/Decl1s/commerceguard/pull/1) | Написано без исполнения |
| 24.10.2026 | CG-101…105 | [#10](https://github.com/Decl1s/commerceguard/pull/10), [#11](https://github.com/Decl1s/commerceguard/pull/11), [#12](https://github.com/Decl1s/commerceguard/pull/12), [#13](https://github.com/Decl1s/commerceguard/pull/13), [#14](https://github.com/Decl1s/commerceguard/pull/14) | Написано без исполнения |
| 24.10.2026 | CG-201/202 | [#16](https://github.com/Decl1s/commerceguard/pull/16), [#18](https://github.com/Decl1s/commerceguard/pull/18) | Написано без исполнения |
| 25.10.2026 | CG-203/204/205 | [#20](https://github.com/Decl1s/commerceguard/pull/20), [#22](https://github.com/Decl1s/commerceguard/pull/22), [#24](https://github.com/Decl1s/commerceguard/pull/24) | Написано без исполнения |
| 25.10.2026 | CG-301 | [#26](https://github.com/Decl1s/commerceguard/pull/26) | Я включил проверки: 15unit,8migrations,8models/13tests |
| 26.10.2026 | CG-302 | [#28](https://github.com/Decl1s/commerceguard/pull/28) | 27unit,9migrations,9models/19tests, старые результаты неизменны |
| 26.10.2026 | CG-303 | codex/s3-cg303-local-flow | 38unit в двух окружениях, Prefect normal/replay/retry/failure/resume |

В CG-301 я исправил обнаруженный raw keyword-only TypeError. Новые проверки
относятся к текущему checkout, не ретроактивному исполнению старых коммитов.
Исторические факты сохраняю в WORKLOG и VALIDATION. Review не принимаю автоматически.
Следующий Ready — CG-304: watermark/freshness/completeness; CG-303 реализовал. Ежедневные мини-проекты отдельно.
