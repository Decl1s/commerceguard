# Мои критерии выпуска1.0

27.10.2026. Я завершил функциональный объём и проверяю release candidate1.0.0rc1. Stable tag создаю только после успешных обязательных CI jobs этого commit.

| Gate | Фактически подтверждённый результат |
| --- | --- |
| Unit | 99tests прошли во всех трёх локальных runtime профилях; CI далее |
| PostgreSQL | 15миграций,31persistent tables, old SHA, late/deadlines/settlement/Case/roles/CSRF/export/backfill/restore подтверждены итоговым runner PG16.15 |
| dbt | 9models+19tests, PASS28; финальный flow прошёл |
| Prefect | Normal/replay/preflight/PSP conflict/retry2и3/marts failure/resume, old SHA неизменен |
| Поставка | Реальные images/Compose, init/runtime SQL denial, owner tools, pg_dump verify, host import duplicate, sessions/volume restarts |
| Browser | Chrome156.0.8078.47/Playwright1.64.1, вход/CSV/assign/comment/stale409, внешних запросов0 |
| Ограниченный smoke | 40HTTP requests/concurrency4/0.368с; EXPLAIN2000Case/page50,planning0.179мс/execution0.049мс в итоговом core runner |
| Dependency security | Локально0known vulnerabilities для5/62/107runtime distributions; финальный CI далее |
| Public source audit | Только PUBLIC_FILES, UTF8/no symlinks, без private paths/контактов/секретов; финальное удалённое дерево проверяю отдельно |
| CI | Workflow добавлен; фактический run ещё не подтверждён |
| Archive/release | Source-only tar.gz+SHA256 строю; stable release ещё не подтверждён |

Я поддерживаю одну организацию, Linux x86_64 и localhost Docker Compose. Базы Python3.12.15/PG16.15/Caddy2.11.7 закреплены digest; runtime Python packages hashes. Waitress3.0.2 обслуживает4threads, web не получает raw/owner secret. Владельцу БД/хоста доверяю. Масштаб100тысяч заказов/сутки, Windows/macOS, публичныйTLS, HA/SSO/ретенцию/внешнюю сертификацию этим выпуском не подтверждаю.

Для воспроизведения запускаю README команды. Полный CI — `.github/workflows/validate.yml`; contents:write получает только release job после unit/integration/security. Я не сливаю PR автоматически. Source tag/архив позволяют установить проверенный выпуск независимо от состояния review. Исторические Draft PR сохраняют ход работы.
