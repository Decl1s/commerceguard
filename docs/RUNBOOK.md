# Как я диагностирую локальное приложение

27.10.2026, schema15. Я завершил backfill, backup/restore и реальную Compose поставку. Актуальные команды — DEPLOYMENT/HANDBOOK/BACKUP, проверки — RELEASE_CHECKLIST. Ранний локальный маршрут ниже сохраняю для разработки.

## Запуск и остановка

Я задаю DSN отдельной своей БД через внешнюю COMMERCEGUARD_DATABASE_URL и проверяю
`python -m commerceguard db status`. При pending миграциях выполняю `db migrate`
явно после сохранения своей БД; web/pipeline сами схему не обновляют. Временный
integration runner создаёт собственный кластер, не заменяет эти административные
действия. Команды исполняю Python из локального окружения приложения.

Я создаю web аккаунты CLI access create, запускаю workbench serve на127.0.0.1,
останавливаю Ctrl+C. Пароли ввожу getpass, готового default password нет.
Чужие порты/службы, настройки аккаунта и PostgreSQL за пределами своих каталогов
не изменяю. Локальный интерфейс нельзя считать внешним production deployment.

## Приём и восстановление отдельного пакета

Я сначала читаю [RECOVERY](RECOVERY.md): там реализованные ingest status/scan/recover
и точные аргументы. Raw first означает возможный orphan; отсутствие строки БД не
доказывает отсутствие raw. При неизвестном COMMIT повторяю тот же manifest/bytes,
а не подменяю identity. Whole-package conflict не исправляю UPDATE canonical fact.
Отказ до begin_attempt может отсутствовать в журнале; diagnosis not_registered
сохраняю явно. Отдельного attempt journal/recovery для standalone advice ещё нет.

## Run и витрины

Я читаю manifest/result по точному run_id. Pipeline resume не переизбирает inputs,
не применяет Case и не создаёт новый исторический ответ под старым ID. Dbт views
не переключаются одной общей транзакцией; после marts failure повторяю build через
resume и проверяю фактический status. Старый saved result читается независимо от
нового kernel; повтор старого execute требует прежних точных байтов движка.
[ORCHESTRATION](ORCHESTRATION.md) и [RESULTS](RESULTS.md) содержат сценарии.

## Рабочее место

401 требует повторного входа/проверки active/expiry,403 — scope/role/CSRF/Origin,
409 — перечитывания текущей карточки/очереди. Я не меняю expected_version наугад.
После503 неизвестного COMMIT сохраняю прежний request_id и тело: exact retry
возвращает прежнее audit событие, changed request под тем же ID отвергается.
Access disable отзывает серверные сессии, history не удаляет.

Presence present/absent отдельно от workflow open/closed. Автоматического close
или reopen нет. Closed finding с новой revision требует явного просмотра решения;
banner очереди не изменяет финансовый baseline. Подробности — [WORKPLACE](WORKPLACE.md).

## Что я реально проверил

Unit79, PostgreSQL/HTTP runner, dbt9views/19tests и отдельный Prefect runner прошли
на Linux. Я подтвердил две concurrent Case transactions и injected audit rollback,
не общую нагрузочную/concurrency/аварийную матрицу. Полная история и ограничения —
[VALIDATION](../VALIDATION.md). Backup restore/power loss/Windows/CI ещё не проверял.
