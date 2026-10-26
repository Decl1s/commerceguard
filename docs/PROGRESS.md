# Таблица этапов CommerceGuard

Я довожу первую рабочую версию по RELEASE_PLAN и подтверждаю готовность отдельно от количества задач.

| Этап | Написано |
| --- | --- |
| S0 | 2/2 |
| S1 | 5/5 |
| S2 | 5/5 |
| S3 | 5/5 |
| S4 | 5/5 |
| S5 | 5/5 |
| S6 | 0/3 |

Сейчас **CG-505**, написано **27/30**. Следующий **CG-601**.

Я измерил реальный план очереди на2000Case и заменил полную загрузку health history на bounded SQL summaries.

Я прошёл97unit и полный PG15migrations/core/HTTP/dbt/restore runner. EXPLAIN дал50строк,planning0.211мс/execution0.056мс; старые health semantics/SHA сохранены, искусственно планировщик не ограничивал.

Подробности: [PERFORMANCE](PERFORMANCE.md). Публикацию фиксирую в WORKLOG.
