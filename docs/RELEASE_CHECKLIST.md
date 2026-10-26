# Мои критерии выпуска1.0.0

27.10.2026. Я завершил функциональный объём30 историй и прошёл полный [CI кандидата22a4b832](https://github.com/Decl1s/commerceguard/actions/runs/40408987370), conclusion=success. Сводку фактических результатов сохранил в [release-candidate.json](evidence/release-candidate.json). Для окончательного commit workflow повторяет те же gates; stable tag/архив создаются отдельным job только после их успеха.

| Gate | Фактически подтверждённый результат |
| --- | --- |
| Unit | 99tests во всех3runtime профилях локально и в CI; pip check/каталог9views успешны |
| PostgreSQL | PG16.15,15 миграций/31 таблица, old SHA, late/deadlines/settlement/Case/roles/CSRF/export/backfill/restore |
| dbt | 9models+19tests, PASS28 |
| Prefect | Normal/replay/preflight/PSP conflict/retry2 и3/marts failure/resume, old SHA неизменен |
| Поставка | Реальные images/Compose, init/runtime SQL denial, owner tools, pg_dump verify, host import duplicate, sessions/volume restarts |
| Browser | Chrome156.0.8078.47 локально и155.0.8059.39 вCI/Playwright1.64.1, login/CSV/assign/comment/stale409, внешних запросов0 |
| Smoke | 40HTTP requests/concurrency4: локально0.368 с, CI0.555 с; это не SLA |
| EXPLAIN | 2000Case/page50, локально planning0.179 мс/execution0.049 мс; CI0.249/0.063 мс, реальные indexes без forced planner |
| Dependency security | 0known vulnerabilities/0skips для5/62/107runtime distributions локально; CI audit также успешен |
| Source audit | Candidate remote183blob SHA/paths совпали с allowlist; финальная версия добавляет только JSON сводку и изменения выпуска |
| Archive | scripts/source_archive проверяет список и bytes tar, выдаёт SHA256; runtime данные/секреты/AGENTS исключены |
| Release gate | Unit3profiles/integration/security — обязательные dependencies; tag на точный проверенный SHA, existing tag/asset conflict не перезаписываю |

Я проверяю итоговую публикацию отдельно по [releasev1.0.0](https://github.com/Decl1s/commerceguard/releases/tag/v1.0.0) и [Actions](https://github.com/Decl1s/commerceguard/actions): conclusion последнего push run, target SHA, публичность, состав source tree, assets и SHA256. Сами ссылки не доказывают состоявшуюся публикацию. Финальную квитанцию с actual run/asset digest храню в навигации main и локальном журнале, чтобы не менять immutable tag задним числом.

Я поддерживаю одну организацию, Linuxx86_64 и localhost Docker Compose. Базы Python3.12.15/PG16.15/Caddy2.11.7 закреплены digest, runtime packages hashes. Waitress3.0.2/4threads, web не получает raw/owner secret. Владельцу БД/хоста доверяю. Масштаб100 тысяч заказов/сутки, Windows/macOS, публичныйTLS, HA/SSO/ретенцию/внешнюю сертификацию не подтверждаю.

Я не сливаю PR автоматически. Source tag/архив позволяют установить проверенный выпуск независимо от review. Исторические Draft PR сохраняют ход работы. Полные локальные сценарии — README/VALIDATION, поставка — DEPLOYMENT, восстановление — BACKUP. Загружать реальные файлы следует только в свой закрытый экземпляр, не в публичные GitHub assets.
