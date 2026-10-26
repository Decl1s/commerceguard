# Kanban: текущее состояние

26.10.2026. Я веду WIP 1. CG-302 реализовал и проверил; публикацию фиксирую отдельно.
Review не означает Accepted или merge. Полная область подтверждения — VALIDATION.

| Backlog | Ready | In progress · WIP 1 | Review | Accepted |
| --- | --- | --- | --- | --- |
| CG-304/305, S4, S5, S6 | CG-303: Prefect local flow | CG-302: сохраняю проверенный срез | CG-301: dbt marts | — |
| — | — | — | S0/CG-001/002, S1/CG-101…105, S2/CG-201…205 | — |

Я не закрываю старые истории автоматически: основной путь S1/S2 теперь проверен,
но legacy upgrade, fault/concurrency и полная приёмка ещё не подтверждены.
В [PROGRESS](PROGRESS.md) храню 14/30 написанных историй и оставшиеся 16.
GitHub Projects board не объявляю созданной; эта Markdown доска каноническая.

## Карточки и следующий pull

CG-302: [#27](https://github.com/Decl1s/commerceguard/issues/27), gross/refund/fee/net,
immutable revision и membership. 27 unit tests, schema8→9, dbt9models/19tests прошли.
Разбор, команды и упражнения — [SETTLEMENT](SETTLEMENT.md).
Предыдущий CG-301: [#25](https://github.com/Decl1s/commerceguard/issues/25),
[Draft PR #26](https://github.com/Decl1s/commerceguard/pull/26), Review.

Далее я беру CG-303: параметризованный локальный ingest→reconcile→marts,
ограниченные retry только идемпотентных шагов и отказ success после упавшего шага.
БД остаётся источником истины; daemon/cloud/HTTP не добавляю в эту историю.
Версию Prefect и совместимость окружения проверю по официальным материалам,
перед написанием следующего среза. Сейчас Prefect не установлен и flow не написан.
