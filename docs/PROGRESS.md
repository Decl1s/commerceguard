# Таблица этапов CommerceGuard

26.10.2026. Я веду последовательные срезы WIP1; Review не означает merge/Accepted.

| Этап | Написано | Что я сделал | Остаток |
| --- | --- | --- | --- |
| S0 | 2/2 | Продукт, предметное ядро | Финальная демонстрация |
| S1 | 5/5 | Приём, raw/COPY, журнал и recovery | Расширенные аварийные проверки |
| S2 | 5/5 | Immutable run/result/evidence, Case, два времени | Расширенная concurrency/legacy матрица |
| S3 | 5/5 | Dbт, settlement, Prefect, freshness, каталог | Финальная приёмка |
| S4 | 5/5 | Я добавил согласованный CSV выбранной очереди с одной валютой, версиями и моментом среза. | Оставшиеся истории рабочего места |
| S5 | 0/5 | Пока план | Backfill, recovery, метрики, поставка, индексы |
| S6 | 0/3 | Пока план | Demo, адаптация, передача |

Я написал **22/30 историй**, осталось **8**. Это количество, не доля времени
или готовность к эксплуатации. Сейчас **CG-405**. Следующий — **CG-501**.

## Текущий срез CG-405

Я добавил согласованный CSV выбранной очереди с одной валютой, версиями и моментом среза.

Я прошёл84unit и PostgreSQL/HTTP/dbt integration: export filters, scope, canonical run, SHA и запрет смешения валют;dbtPASS28.

Материалы: [EXPORT](EXPORT.md). Публикацию/PR отмечаю в WORKLOG после фактического создания.

## 26.10.2026 — CG-304: свежесть и полнота

Я реализовал source health для OMS/PSP/settlement: observed/business/event watermarks,
последнюю публикацию, last attempt/success, явные cutoff/timezone/пороги. Неизвестность
и полный ноль различаю по контракту источника. Чтение ничего не записывает; будущий
terminal diagnosis в прошлом cutoff не показываю. Конспект/карта/пять заданий —
[FRESHNESS](FRESHNESS.md). Ветка codex/s3-cg304-source-health поверх #30, issue#31;
я опубликовал [Draft PR #32](https://github.com/Decl1s/commerceguard/pull/32).

Я прошёл53unit в обоих окружениях, core/source health integration и Prefect runner
на PG16.15. Dbт9models/19tests PASS28; saved reports неизменны. Analytics lock теперь
62distribution с tzdata2026.5/IANA2026e, orchestration107 версий сохранил. Схема9,
24таблицы/9views без изменений. Следующий CG-305; CI/Windows/concurrency ещё нет.

## 26.10.2026 — CG-303: локальная оркестрация

Я написал pipeline run/resume, отдельные Prefect tasks, preflight frozen inputs,
cutoff после ingest и allowlist retry. Fail не публикует общий success; сохранённый
report остаётся доступен. Текущий source branch codex/s3-cg303-local-flow поверх
CG-302#28, issueCG-303#29 — Review. Я опубликовал
[Draft PR #30](https://github.com/Decl1s/commerceguard/pull/30).

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
| 26.10.2026 | CG-303 | [#30](https://github.com/Decl1s/commerceguard/pull/30) | 38unit в двух окружениях, Prefect normal/replay/retry/failure/resume |
| 26.10.2026 | CG-304 | [#32](https://github.com/Decl1s/commerceguard/pull/32) | 53unit в двух окружениях, health/core/Prefect/dbt integration |

В CG-301 я исправил обнаруженный raw keyword-only TypeError. Новые проверки
относятся к текущему checkout, не ретроактивному исполнению старых коммитов.
Исторические факты сохраняю в WORKLOG и VALIDATION. Review не принимаю автоматически.
Следующий Ready — [CG-305 #33](https://github.com/Decl1s/commerceguard/issues/33): каталог показателей; CG-304 реализовал. Ежедневные мини-проекты отдельно.


## Мои пять последовательных срезов 26.10.2026

| История | Что я поставил | Review |
| --- | --- | --- |
| CG-305 | Каталог9SQL views, grain/key/currency/time/lineage | [DraftPR#34](https://github.com/Decl1s/commerceguard/pull/34) |
| CG-401 | Очередь/карточка/evidence, filters/keyset/empty state | [DraftPR#36](https://github.com/Decl1s/commerceguard/pull/36) |
| CG-402 | Accounts/roles/scope/sessions/CSRF | [DraftPR#38](https://github.com/Decl1s/commerceguard/pull/38) |
| CG-403 | Assignment/comments/request/version/atomic audit | [DraftPR#40](https://github.com/Decl1s/commerceguard/pull/40) |
| CG-404 | Close/reopen/reason/history/сигнал пересмотра | [DraftPR#42](https://github.com/Decl1s/commerceguard/pull/42) |

Я опубликовал137разрешённых исходников в отдельной source ветке
codex/s4-cg404-case-decisions. Следующий Ready — [CG-405#43](https://github.com/Decl1s/commerceguard/issues/43).
Merge/Accepted/stable release не выполняю; CI отдельно от локальных проверок.
