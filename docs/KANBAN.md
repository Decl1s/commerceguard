# Kanban: текущее состояние

26.10.2026. Я веду WIP1. CG-304 реализовал и проверил, сохраняю публикацию.
Review не означает Accepted/merge. Факты и ограничения — VALIDATION.

| Backlog | Ready | In progress · WIP1 | Review | Accepted |
| --- | --- | --- | --- | --- |
| S4, S5, S6 | CG-305: data catalog | CG-304: сохраняю source health #31 | CG-301/302/303 | — |
| — | — | — | S0, S1/CG-101…105, S2/CG-201…205 | — |

Я написал16/30историй, остаются14;6до первого рабочего места аналитика. Это
количество задач, не время/качество. Полную приёмку старых срезов не объявляю.
GitHub Projects board не создавал; эта Markdown доска каноническая.

CG-304 [#31](https://github.com/Decl1s/commerceguard/issues/31): source watermarks,
явный timezone, last attempt/success, no_data/zero/incomplete/unknown и read-only
snapshot. 53unit в двух окружениях, core/health и Prefect integration прошли.
Карта, параметры, ограничения и задания — [FRESHNESS](FRESHNESS.md).
Предыдущий CG-303 — [Draft PR#30](https://github.com/Decl1s/commerceguard/pull/30).

Далее я беру только CG-305: каталог каждой публичной витрины/показателя с зерном,
ключами, валютой, cutoff, происхождением, владельцем смысла и ограничениями.
HTTP/UI/роли — S4, эксплуатация — S5/S6. Daily мини-проекты отдельно.
