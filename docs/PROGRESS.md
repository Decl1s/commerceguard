# Таблица этапов CommerceGuard

Я довожу первую рабочую версию по RELEASE_PLAN и подтверждаю готовность отдельно от количества задач.

| Этап | Написано |
| --- | --- |
| S0 | 2/2 |
| S1 | 5/5 |
| S2 | 5/5 |
| S3 | 5/5 |
| S4 | 5/5 |
| S5 | 4/5 |
| S6 | 0/3 |

Сейчас **CG-504**, написано **26/30**. Следующий **CG-505**.

Я добавил проверенную Compose поставку с Waitress/Caddy, private backend, runtime SQL правами, независимыми tools venv и управлением аккаунтами.

Я прошёл96unit в трёх средах и реальный Compose scenario: fresh install, full Prefect/dbt, pg_dump/verify, UI decisions/export, SQL denial,40requests/concurrency4 за0.393с, restart/session/volume persistence. Я ограничиваю подтверждение Linuxx86_64.

Подробности: [DEPLOYMENT](DEPLOYMENT.md). Публикацию фиксирую в WORKLOG.
