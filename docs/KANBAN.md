# Kanban

26.10.2026. Я сохраняю WIP1 и публикую каждый срез до начала следующего.

| Backlog | Ready | In progress | Review | Accepted |
| --- | --- | --- | --- | --- |
| Оставшиеся S4/S5/S6 | CG-404 | — | CG-403; предыдущие S0…S3 | — |

Я написал 20/30 историй. Я добавил назначения, комментарии, workflow version и атомарный append-only аудит человеческих действий.
Я прошёл75unit и PG/HTTP integration: schema8→11, exact replay, changed-request409, настоящий конфликт двух соединений, rollback между UPDATE/audit, deferred guard и stored-XSS escape;dbtPASS28. Принятие и автоматический merge не выполняю.
Точные PR/heads фиксирую в WORKLOG и локальном журнале проекта.
