# Kanban

Я сохраняю WIP1.

| Ready | In progress | Review |
| --- | --- | --- |
| CG-502 | — | CG-501 и предыдущие срезы |

Я реализовал календарный план, закрепление run IDs и bounded resume с отдельным состоянием job.

Я прошёл89unit и PG/dbt/HTTP integration; остановка backfill и повтор сохранили run identity, completed retry не создал новый результат.
