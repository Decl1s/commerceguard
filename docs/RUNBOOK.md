# План эксплуатации и восстановления

**Состояние: спецификация S1–S5. Написаны db, input inspect и ingest publish.**
Ни один сценарий ниже не выполнялся. Не копировать выдуманные команды в терминал:
в текущей версии есть demo, --version, db status/migrate, input inspect и ingest publish.
Описание — [STORAGE](STORAGE.md), [INPUTS](INPUTS.md), [INGESTION](INGESTION.md).
Recovery/status по партии и backfill ещё не написаны; никаких попыток восстановления
я пока не выполнял. Publish — написанный мной код, без подтверждения запуском.

## Проектные состояния

CG-103: received → staged → published внутри одной транзакции. Parsing происходит
в TEMP до INSERT batch; промежуточных состояний извне не видно. Persistent
quarantined/failed и attempts — будущий CG-104, не текущий журнал ошибок.
Run: planned → running → published либо failed. Источник «последний успешный»
обновляется только при published. Технический retry создаёт попытку, но не новый
бизнес-факт; новая версия входа или cutoff создаёт новый смысловой запуск.

Case: open → in_progress → closed_manual; из вычисления возможны auto_resolved
и reopen. Точные allowed transitions и названия будут закреплены CG-404;
сейчас состояния кейсов не используются в kernel.

## Инцидент: файл есть, manifest отсутствует

Проверить имя/размер/hash и источник только в выделенной raw-папке проекта.
Без canonical manifest и исходного envelope identity нельзя угадать по одному
content hash. Сохранить объект для будущего CG-104. Если envelope доступен,
повторять его целиком, не копировать файл с новым
искусственным business ID. Если файл не соответствует contract version,
карантин с причиной; не разрешать автоматическое исполнение содержимого.

## Инцидент: процесс умер после COPY до публикации

Attempt ещё не сохраняется. Проверить опубликованный batch по ID после независимого
подключения; последний published snapshot остаётся доступным. Если связь оборвалась
на COMMIT, исход неизвестен, а не обязательно rollback.
После отката staging не является опубликованным источником. Повтор с тем же
ключом партии должен завершить одну публикацию либо сообщить об уже завершённой.
Не удалять core для удобного «перезапуска с нуля».

## Инцидент: поздний факт изменил сверку

Сохранить прежний run. Новый run получает более поздний cutoff и причину late-data.
Сопоставить finding revisions по case_key, зафиксировать исчезновение/изменение.
Не переписывать время первого наблюдения факта на время retry.

## Инцидент: конфликт содержимого PSP ID

Остановить публикацию партии, показать error code и ссылки на обе raw-версии.
Не выбирать более новую строку автоматически. Решение — новый correction contract
или исправленный источник; финансовый аналитик не редактирует normalized fact из UI.

## План резервирования

Согласованный backup должен включать PostgreSQL, raw-файлы, manifest и версии
контрактов/правил. Секреты не входят в публичный архив. Порядок восстановления:
БД → совпадающий набор raw по hash → сверка доступности manifest → application config.
Без фактического восстановления RPO/RTO не объявляются. «Backup файл создан»
не означает доказанной восстановимости. Автоматическое удаление backup не предусмотрено.

## Диагностическая информация будущей версии

batch_id, run_id, attempt_id, source, merchant, counts, error_code, duration и
published_at. Не логировать пароли, HTTP headers авторизации и полный raw payload.
Метрики: fresh watermark, batches quarantined, last successful run age, pending/
blocked orders, open cases по валюте/правилу. Суммировать абсолютные delta двух
плеч как «убыток магазина» запрещено: бизнес-смысл разный.

## Написанное восстановление CG-104

Я добавил ingest scan-raw и ingest recover --manifest-sha. Использую только явный
raw root и identity canonical manifest, ничего не удаляю. Сначала смотрю published
batch, затем attempts; started/unknown не считаю доказанным отказом. Карантин —
whole-package attempt, а не частично принятый core. Команды и границы в RECOVERY.
Статусы unavailable/not_registered не заменяю утверждением, что диагноз сохранён.

## Кейсы · будущий маршрут CG-203

Я читаю CASES перед case apply. Нужен уже опубликованный result; apply не считает
его заново. CASE_STREAM_BUSY — повтор позже, CANONICAL_RUN_REGRESSION/TIME_TIE —
выбор времени/политики, не blind retry с новым UUID. Неизвестный COMMIT проверяю
повтором того же run: already_applied не меняет stream. Не удаляю ledger/кейсы
ради восстановления. Все команды я пока не запускал.

## Корректировка истории · будущий маршрут CG-204

Я выбираю опубликованный baseline того же merchant/as_of, задаю knowledge явно
после его границы, mode as-known-now и reason. Сначала prepare, затем execute,
потом changes; в CASE_CORRECTION_REPORT_ONLY не пытаюсь обходить запрет через SQL.
Если engine_changed, отдельно рассматриваю изменение алгоритма. Для старого
manifest mismatch не переписываю SHA вручную: нужен соответствующий checkout.
Маршрут, параметры, входы и ограничения фиксирую в LATE_DATA. Ничего не выполнял.

## Следующий маршрут сроков и policy · CG-205

Я читаю DEADLINES перед будущим запуском 0008: legacy данные не backfill,
миграции 0001…0007 не редактирую. Старые reports доступны для чтения; старый
prepared run с engine mismatch не исправляю подменой SHA. Создаю новый v3 run
либо использую соответствующую историческую реализацию/совместимую схему.
Перед v1→v2 Case upgrade читаю canonical head магазина; при HEAD_MISMATCH
сначала заново разбираю контекст, не подставляю новый UUID в автоматическом retry.
При неизвестном COMMIT повторяю ту же identity и читаю application ledger.
Это инструкция без исполнения; резервирование/аварийные процедуры ещё не проверены.

## CG-302: как я повторяю публикацию выписки

При SETTLEMENT_REVISION_CONFLICT я не делаю UPDATE: исправляю данные новой revision.
При EVENT_ALREADY_ASSIGNED проверяю business membership; перенос/отмена пока не
поддерживаются. Missing PSP/неполный состав дают unknown, не технический success
с нулями. Для late fact создаю новый cutoff/report и сохраняю старый.

Raw-first может оставить orphan. Ingest scan-raw/recover не восстанавливает standalone
advice автоматически; я повторяю settlement publish с исходным файлом. При COMMIT
unknown повторяю ту же identity и читаю результат, не объявляю rollback. Отдельного
settlement attempt journal/GC нет. Команды и пределы — SETTLEMENT; проверенный
одноразовый runner — README. Backup/restore и fault-сценарии ещё не выполнены.

## CG-303: как я продолжаю pipeline

При PSP conflict я сохраняю уже принятый OMS, исправляю вход и запускаю новый
run, не reset БД. При failure execute/marts и наличии run_id использую pipeline
resume: входы заново не выбираю, saved result не заменяю. Unknown COMMIT не
объявляю rollback. Настройки/пароль Prefect не сохраняю; stdout report держу
локально при необходимости. Ephemeral history после команды удаляется, отдельного
flow journal пока нет. Commands/limits/retries/failures — ORCHESTRATION.
При обновлении зависимостей воспроизвожу реальный flow, не только pip install.
