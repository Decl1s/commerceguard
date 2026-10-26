# С чего я начинаю CommerceGuard

Я реализовал21/30историй. Основное рабочее место есть, export/эксплуатация/передача
ещё впереди. Все примеры учебные, запуск и проверки подтвердил на Linux.

1. Я открываю [README](README.md): возможности и команды установки/проверки.
2. Я читаю [WORKPLACE](docs/WORKPLACE.md): путь аналитика, формы, версии и аудит.
3. Я открываю [PROGRESS](docs/PROGRESS.md): таблица этапов и точный остаток.
4. Для кода использую [PROJECT_MAP](docs/PROJECT_MAP.md), для решений — [ADR](DECISIONS.md).
5. Я отделяю выполненные проверки в [VALIDATION](VALIDATION.md) от будущей приёмки.

## Мой маршрут по новому срезу

Я начинаю с catalog check, читаюgrain/key/time/currency mart_reconciliation_currency.
Затем иду в workbench_store.queue и вижу snapshot, filters, keyset/head guard.
В workbench.Handler я прослеживаю HTML escape, session, scope и форму POST.
В access.authorize вижу actor из БД, роль иCSRF, в case_workflow.mutate — request
lock, Case row lock, optimistic expectations, UPDATE+audit и один COMMIT.
Заканчиваю0011/0012guards и scripts/workbench_scenarios.py с двумя настоящими
соединениями и injected rollback. Формулы сверки не переношу в HTTP handler.

## Как я пробую руками

Для быстрого подтверждения всех слоёв запускаю README integration runner: он сам
создаёт и удаляет только свой PostgreSQL/HTTP. Для самостоятельного редактирования
готовлю свою синтетическую БД по WORKBENCH/RESULTS/CASES, создаю локальные accounts
и запускаю workbench serve. Готовых паролей нет, DSN не помещаю в Git.

Я открываю одну карточку в двух вкладках: первое действие сохраняется, второе409.
Повтор того же request_id не создаёт второй комментарий. Manager close требует
причину, analyst не может подменить эту роль. После нового system observation
история human решения остаётся на месте. Упражнения и ожидаемые ответы — WORKPLACE,
CATALOG, FRESHNESS, SETTLEMENT иORCHESTRATION.

## Как я продолжаю разработку

Следующий Ready — CG-405 безопасный export выбранной очереди. Я сначала определю
срез/контекст/лимит и безопасные CSV cells, затем API/UI и проверки. Старые PR не
сливаю автоматически, published migrations не переписываю. Daily мини-проекты
веду отдельно. IDE workspace `commerceguard.code-workspace` открывает только этот
репозиторий и не захватывает Git родительского каталога.
