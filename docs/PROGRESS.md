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
| S6 | 2/3 |

Сейчас **CG-602**, написано **29/30**. Следующий **CG-603**.

Я завершил руководство сопровождения и bounded stdin импорт выбранных файлов без host mounts.

Я прошёл99unit, полный Prefect/PG/dbt normal/replay/failure/retry/resume и повторный Compose/Chrome: host import duplicate, CSV/stale409, сохранность sessions/volumes,40requests/concurrency4/0.368с. Схема15 и финансовый kernel не менялись.

Подробности: [HANDBOOK](HANDBOOK.md). Публикацию фиксирую в WORKLOG.
