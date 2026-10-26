# Kanban

Я сохраняю WIP1.

| Ready | In progress | Review |
| --- | --- | --- |
| CG-503 | — | CG-502 и предыдущие срезы |

Я добавил согласованный DB+raw backup, проверку повреждений и восстановление в пустую БД с server receipt и finish-restore.

Я прошёл89unit и полный PG/HTTP/dbt runner: реальный restore в другой кластер/owner, old SHA/Case/audit comparison, session revocation, tampering/nonempty denial и остановка после DB COMMIT.
