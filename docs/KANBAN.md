# Kanban

Я сохраняю WIP1.

| Ready | In progress | Review |
| --- | --- | --- |
| CG-601 | — | CG-505 и предыдущие срезы |

Я измерил реальный план очереди на2000Case и заменил полную загрузку health history на bounded SQL summaries.

Я прошёл97unit и полный PG15migrations/core/HTTP/dbt/restore runner. EXPLAIN дал50строк,planning0.211мс/execution0.056мс; старые health semantics/SHA сохранены, искусственно планировщик не ограничивал.
