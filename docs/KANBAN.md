# Kanban: текущее состояние

25.10.2026. Я веду WIP 1; после публикации CG-301 беру CG-302. Проверки включены,
точная область подтверждения — VALIDATION. Review не равно Accepted или merge.

| Backlog | Ready | In progress · WIP 1 | Review | Accepted |
| --- | --- | --- | --- | --- |
| CG-303…305, S4, S5, S6 | CG-302: settlement/fee | — после публикации | CG-301: dbt marts, основной Linux путь проверен | — |
| — | — | — | S0/CG-001/002, S1/CG-101…105, S2/CG-201…205 | — |

Я не закрываю старые истории автоматически: основной путь S1/S2 теперь проверен,
но legacy upgrade, fault/concurrency и полная приёмка ещё не подтверждены.
В [PROGRESS](PROGRESS.md) храню 13/30 написанных историй и оставшиеся 17.
GitHub Projects board не объявляю созданной; эта Markdown доска каноническая.

## Карточки и следующий pull

CG-301: [#25](https://github.com/Decl1s/commerceguard/issues/25), Review, [Draft PR #26](https://github.com/Decl1s/commerceguard/pull/26).
Предыдущий CG-205: [#23](https://github.com/Decl1s/commerceguard/issues/23),
[Draft PR #24](https://github.com/Decl1s/commerceguard/pull/24).
Остальные ссылки сохраняю в BACKLOG/PROGRESS/WORKLOG.

CG-302: я начну с нового settlement batch контракта: gross/refund/fee/net,
уровень PSP batch, currency и completeness. Комиссию не распределяю произвольно
по OMS заказам. Prefect/UI/метрики не смешиваю с этой историей. Сначала ADR/данные,
затем код и подходящие проверки. Мини-проекты и их расписание не меняю.

CG-302: [карточка #27](https://github.com/Decl1s/commerceguard/issues/27), Ready; реализацию не начинал.
