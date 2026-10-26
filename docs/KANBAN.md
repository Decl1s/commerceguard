# Kanban: текущее состояние

26.10.2026. Я веду WIP1. CG-303 реализовал, проверил и опубликовал в Draft PR#30.
Review не означает Accepted/merge. Факты и пробелы — VALIDATION.

| Backlog | Ready | In progress · WIP1 | Review | Accepted |
| --- | --- | --- | --- | --- |
| CG-305, S4, S5, S6 | CG-304: freshness/completeness #31 | — | CG-303 #30, CG-301/302 | — |
| — | — | — | S0, S1/CG-101…105, S2/CG-201…205 | — |

Я написал15/30историй, остаются15;7до первого рабочего места аналитика. Это счёт
задач, не время/качество. Полная приёмка прежних срезов ещё не подтверждена.
GitHub Projects board не объявляю созданной; эта Markdown доска каноническая.

CG-303 [#29](https://github.com/Decl1s/commerceguard/issues/29): local run/resume,
frozen inputs, fixed cutoff, bounded retry, failed stage stops downstream.
38unit в двух окружениях, real Prefect/PG/dbt путь и fault injection прошли.
Подробности, аргументы, карта и5задач — [ORCHESTRATION](ORCHESTRATION.md).
Предыдущий CG-302: [Draft PR#28](https://github.com/Decl1s/commerceguard/pull/28).

Следующим я беру только CG-304: source watermarks, business timezone, last successful
vs last attempt, различие late/no-data/zero. Не подменяю финансовую baseline часами
оркестратора. Catalog/HTTP/UI/эксплуатацию не смешиваю с этой историей. Daily отдельно.

Я сохранил [Draft PR#30](https://github.com/Decl1s/commerceguard/pull/30),
issue#29 Review и [Ready#31](https://github.com/Decl1s/commerceguard/issues/31).
WIP свободен; в следующем продолжении беру только CG-304. Merge/Accepted нет.
