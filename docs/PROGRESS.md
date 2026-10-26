# Таблица этапов CommerceGuard

Я довожу первую рабочую версию по RELEASE_PLAN и подтверждаю готовность отдельно от количества задач.

| Этап | Написано |
| --- | --- |
| S0 | 2/2 |
| S1 | 5/5 |
| S2 | 5/5 |
| S3 | 5/5 |
| S4 | 5/5 |
| S5 | 3/5 |
| S6 | 0/3 |

Сейчас **CG-503**, написано **25/30**. Следующий **CG-504**.

Я добавил live/readiness, scoped метрики, безопасные JSON события и X-Request-ID.

Я прошёл92unit и PG/HTTP/dbt/restore integration; health/metrics authorization и плохой Host POST проверены фактически.

Подробности: [OPERATIONS](OPERATIONS.md). Публикацию фиксирую в WORKLOG.
