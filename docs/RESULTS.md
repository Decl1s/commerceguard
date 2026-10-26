# CG-202: сохранённый результат и происхождение цифр

24.10.2026, 0.1.0.dev7. Я написал этот срез без запуска. Команды, SQL и результаты
не проверял исполнением; весь материал остаётся unverified.

## Как я отделил план, попытку и результат

CG-201 закрепляет immutable run manifest. В CG-202 я добавил ops_run_attempt,
ops_run_result и ops_run_evidence. Схема содержит 15 постоянных таблиц.
Один manifest может иметь несколько попыток выполнения, но только один результат.
Failed/unknown попытка не меняет входы и не уничтожает прежде опубликованный отчёт.
Повтор с теми же входами и правилами не создаёт второй результат.

Я храню полный bounded результат kernel как canonical JSON snapshot: balances,
findings, expected/actual/delta, null неизвестности и счётчики. Текст задаёт точные
байты result SHA, JSONB позволяет читать структуру. Не смешиваю этот snapshot с
изменяемой операционной карточкой Case. SQL-витрины смогут извлекать эти поля в S3;
для начального bounded CLI не дублирую каждую сумму второй mutable таблицей.
Формат result_version=1 закреплён в SQL. Новый смысл структуры потребует версии.

## Входы я не выбираю заново

Перед выполнением читаю сохранённые run_key/text/JSON, сверяю SHA, UUID, balance-v1,
manifest version, knowledge basis и fingerprint kernel/selector. Несовпадение —
MANIFEST_OR_ENGINE_MISMATCH, без попытки молча выполнить старый план новым правилом.
Список ops_run_input должен точно совпасть с canonical manifest; каждый batch
остаётся published и совпадает по source/merchant/file hashes.

OMS читаю ровно по выбранному snapshot. PSP читаю через receipts выбранных batch,
а не через все нынешние события магазина. Это важно: canonical факт мог впервые
появиться в другом пакете, но данный run узнал его через конкретную receipt.
Передаю в kernel значение observed_at этой receipt, не переписывая canonical факт.
Semantic hash подтверждает бизнес-поля; per-batch counts сверяю с declared rows.
Потерянная связь receipt/event/raw не должна превратить неполный JOIN в нулевой платёж.

В kernel поступает одна запись на receipt, поэтому дубликаты доставки учитываются
в duplicates_removed, но не удваивают capture/refund. В evidence сохраняю все receipt
refs, включая равные повторы. Правила остаются в прежнем reconcile, CLI не считает
денежные формулы самостоятельно. Source IDs, валюты и суммы проходят domain types.

## Моя граница исполнения

1. Короткой транзакцией подтверждаю manifest/engine и started attempt.
2. Отдельным READ ONLY/REPEATABLE READ снимком материализую ровно закреплённые входы.
3. Закрываю read transaction и вызываю чистый kernel. Не держу idle transaction,
   пока Python считает. Повторно сверяю fingerprint после расчёта.
4. Короткой финальной транзакцией беру run advisory lock. При прежнем result SHA
   отмечаю новую attempt как duplicate. При другом SHA отказываю RESULT_IDENTITY_CONFLICT.
5. Для нового результата одним COMMIT сохраняю header/JSON, все evidence refs и
   published attempt. Пока транзакция не завершена, частичного отчёта нет.

Две попытки могут параллельно посчитать один и тот же plan; публикация сериализована
отдельным run key. Это допускает лишнее вычисление, но не второй результат. Locks
остаются cooperative, а не защитой от владельца/DBA. Все успешные данные защищаю
append-only triggers. Историю терминальных попыток не переписываю.

После исключения пробую отдельное соединение для safe error code. Обновляю только
started, поэтому потерянный ответ COMMIT не затирает опубликованный успех. При
недоступной БД показываю journal=unavailable. Ошибку контракта или известный отказ
отделяю от unknown; driver DETAIL, payload и DSN не попадают в журнал. Kill/power loss
может оставить started. Повтор execute снова проверит весь plan и входы.

## Ограничения начального результата

Я ограничил один расчёт 10000 OMS orders и 50000 PSP receipts. При превышении
отказываю EXECUTION_INPUT_LIMIT, не обрезаю вход. Это меньше целевого масштаба PRD;
производительность и RSS не измерял. На v1 важнее явная граница, чем заявление,
что in-memory kernel уже обрабатывает полный плановый поток.

Canonical result ограничен 16 MiB и 100000 findings. Числа ограничивают сохраняемый
snapshot, а не обещают заданную скорость. Нормальные bound-данные всё равно могут
упереться в размер текста: тогда отказываю без частичной публикации. Для larger scale
нужны измерения и порционная модель, но без потери атомарности видимости.
JSONB просмотр пока получает bounded snapshot целиком и ограничивает stdout через
--limit. Это не SQL pagination бесконечного массива и не готовая веб-витрина.

Я фиксирую отдельный executor source SHA рядом с result и kernel SHA в manifest.
Не редактирую checkout во время процесса; fingerprint source не является доказательством
поведения произвольно подменённого загруженного bytecode. Trusted owner и checkout —
граница текущей локальной модели. Подлинность источника и полноту PSP-периода этим
срезом также не доказываю. Канонический бизнес-run и управление кейсами ещё впереди.

## Как я провожу evidence до файла

```text
finding.case_key → evidence_event_ids → ops_run_evidence
→ receipt(batch_id, raw_row_number) → ingest_raw_record + record SHA
→ ingest_batch.raw_object_key → точные raw bytes
```

Для ожидаемой суммы путь другой: result.oms_snapshot_id → core_order_expectation
по merchant/order → raw ordinal/hash → исходный OMS CSV. Отсутствующая оплата может
иметь пустое PSP evidence; это не отсутствие происхождения ожидаемой суммы.
У orphan нет соответствующей OMS-строки, но есть PSP receipt refs. У blocked
валютного баланса сохраняю null, не подменяю его нулём или курсом обмена.
Для matched balance также показываю источник ожидания и все события заказа.

## Подготовленные команды

После самостоятельного db migrate и подготовки run manifest:

```bash
.venv/bin/python -m commerceguard run execute --run-id UUID
.venv/bin/python -m commerceguard run result --run-id UUID --limit 50
.venv/bin/python -m commerceguard run evidence --run-id UUID --order-id O1002
.venv/bin/python -m commerceguard run evidence --run-id UUID --case-key CASE_SHA256
```

UUID и CASE_SHA256 заменяю на свои ID. На Windows использую .venv/Scripts/python.exe.
Result/evidence — read-only команды. Evidence выводит относительный raw key, batch,
ordinal и hash, не raw_text и абсолютный путь. Отсутствующий result даёт found=false,
не вычисление по нынешним данным. Точный replay execute отдаёт duplicate_result=true.
Show продолжает показывать manifest; факт публикации смотрю через result.

Ручной ориентир kernel для baseline при cutoff 24.10 до будущего deadline:
5 balances, 4 findings, 6 unique visible events, 1 duplicate. Для O1002:
12000 expected capture, 11000 actual, delta=-1000; evidence C02 и OMS O1002.
Эти числа я не получил выполнением CLI. При другом cutoff deadline-статус может
измениться; подготовка plan также требует реальной доступности выбранных batch.

19. Я предлагаю проследить payment_shortfall без единого PSP-события. Ориентир:
пустое PSP evidence, но OMS raw reference есть. Не сочиняй receipt ради красивого FK.

20. Execute потерял ответ финального COMMIT. Ориентир: сначала читаю result; затем
тот же manifest исполняю повторно. При сохранённом совпадающем result SHA получу
новую duplicate attempt, старый result/evidence останется неизменным.

21. В уже сохранённый plan не входит новый batch магазина. Ориентир: execute старого
ID его не подхватывает; новый prepare может дать другой ID. Найди receipt JOIN через
ops_run_input и объясни отличие от выборки всех core_payment_event магазина.

Наблюдавшихся запусков, сбоев и успешных проверок у меня нет. Я не запускал этот
код, SQL, concurrency, replay и viewers. Следующим CG-203 начну сохранять кейсы
и их ревизии, не превращая immutable finding snapshot в редактируемую карточку.

## Расширение CG-204 · result v2

Я добавил knowledge_at/mode/visibility_version в новые results, передаю отдельную
границу knowledge в kernel. В evidence receipt содержит occurred/observed и
visible_in_run; все raw refs не выдаю за участвовавшие в сумме. Run changes читает
baseline из manifest, сравнивает findings/inputs/newly visible event receipts,
показывает engine_changed и visibility_changed. Старые result v1 не обновляю.
Карта и ограничения в LATE_DATA. Код, SQL и команды не запускал.

## Актуальное расширение CG-205 · result v3

Я сохраняю result_version=3 и payload deadline_version=per-leg-v2. Каждый balance
содержит capture_due_at/refund_due_at (canonical UTC), capture_state/refund_state
и expectation_version. В demo JSON применяю ту же сериализацию сроков.
Findings, stable case key и evidence shape не меняю; общий state выбираю по
приоритету discrepancy > pending > matched. Видимость event/receipt и границы
as_of/knowledge сохраняю. Result/evidence прошлых версий читаю как сохранены,
не вычисляю заново. New executor требует manifest v3; автоматической поставки
старых executors нет. Числа примера DEADLINES — расчёт на бумаге, не stdout.

## CG-302: отдельный settlement result v1

Я сохраняю request(advice/cutoff/tariff/visibility/engine) и payload(state/four sums/
completeness/evidence) в ops_settlement_result. Это не order result v3 и не Case.
Exact request повторно читает прежний payload; late fact требует нового cutoff.
Viewer settlement result ограничивает evidence и ID списки, SHA относится к полному
сохранённому JSON. Grain SQL mart — report_id. Формулы и примеры — SETTLEMENT.
