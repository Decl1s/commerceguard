# С чего я начинаю CommerceGuard

1. Я читаю README: бизнес-смысл, поддерживаемый профиль и запуск Compose.
2. Я открываю `commerceguard.code-workspace` в VS Code или совместимой IDE: workspace содержит только этот репозиторий, родительский Git и локальные данные не захватывает.
3. Я прохожу [DEMO](docs/DEMO.md): очередь → сумма → источники → решение → CSV.
4. Я читаю [HANDBOOK](docs/HANDBOOK.md): карта изменений, эксплуатация и задания с ответами.
5. Я сверяю [RELEASE_CHECKLIST](docs/RELEASE_CHECKLIST.md) и [VALIDATION](VALIDATION.md): что фактически проверено, какой CI и какая версия опубликованы.

## Мой маршрут по коду

Я начинаю с чистой функции `reconcile.py` и типов `domain.py`, затем прослеживаю manifest/parser → raw_store → ingestion/COPY → run_plans → run_execution. Эти слои объясняют происхождение суммы. `case_store` проектирует system observation, `case_workflow` хранит решение с ролью, versions и audit в одном COMMIT. UI в `workbench` вызывает сервисы, WSGI в `server` задаёт границы запросов. Для SQL читаю миграции0001…0015, затем dbt DAG и каталог. Для эксплуатации — `backup`, `backfill`, `observability`, `runtime_role` и deploy. Подробности в [PROJECT_MAP](docs/PROJECT_MAP.md).

## Как я учусь менять проект

Я создаю свою ветку codex/, меняю один сценарий и проверяю его границу. Сначала правлю только оформление/фильтр, затем отдельную витрину, затем адаптер внешнего формата. Новое денежное правило требует новой engine identity; опубликованные миграции не редактирую. DSN/пароли/raw/БД держу в ignored workspace, не в Git. Задания с ожидаемыми ответами находятся в HANDBOOK, EXERCISES, WORKPLACE, MARTS, FRESHNESS, SETTLEMENT и ORCHESTRATION. Первый полный запуск беру из README.

Я написал30историй исходного объёма. Текущий выпуск и отдельные оставшиеся релизные gates вижу в [PROGRESS](docs/PROGRESS.md). Дневные мини-проекты веду отдельно.
