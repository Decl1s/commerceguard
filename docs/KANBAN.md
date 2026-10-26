# Kanban

Я сохраняю WIP1.

| Ready | In progress | Review |
| --- | --- | --- |
| CG-505 | — | CG-504 и предыдущие срезы |

Я добавил проверенную Compose поставку с Waitress/Caddy, private backend, runtime SQL правами, независимыми tools venv и управлением аккаунтами.

Я прошёл96unit в трёх средах и реальный Compose scenario: fresh install, full Prefect/dbt, pg_dump/verify, UI decisions/export, SQL denial,40requests/concurrency4 за0.393с, restart/session/volume persistence. Я ограничиваю подтверждение Linuxx86_64.
