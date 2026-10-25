# CG-201: какие данные участвовали в сверке

24.10.2026, 0.1.0.dev6. Я написал этот срез без исполнения программы и SQL.
Статус unverified. Здесь я сохраняю план расчёта, а не результат сверки.

## Бизнес-смысл

Вчерашний отчёт не должен незаметно меняться после новой доставки PSP или новой
версии ожиданий OMS. Для объяснения цифры недостаточно сохранить «cutoff 24 октября»:
нужно знать, какие именно пакеты и правила были доступны конкретному расчёту.
Поэтому сначала фиксирую immutable manifest и список входов. Балансы, findings,
evidence и жизненный цикл выполнения добавлю следующим CG-202, кейсы — CG-203.

Я отделяю три уровня: ingest batch — пакет источника, ingest attempt — попытка
доставки, run manifest — набор входов вычисления. Retry доставки не создаёт новый
платёж, а повтор подготовки того же manifest не создаёт новый run ID.

## Что я сохраняю

| Поле | Зачем я его фиксирую |
| --- | --- |
| run_id / run_key | Детерминированный UUIDv5 и SHA-256 canonical manifest |
| merchant_id | Граница выбранного магазина, не межклиентская авторизация |
| as_of | Предметный cutoff для effective/observed времени |
| knowledge_at | В v1 равен as_of; предел технического published_at marker |
| mode | Пока только as-was; as-known-now и коррекции относятся к CG-204 |
| knowledge_basis | Явное published-at-marker-v1, без обещания точного commit timestamp |
| ruleset_version | balance-v1 из того же kernel, который будет выполнять расчёт |
| engine_sha256 | Fingerprint точных source bytes kernel, контрактов и selector |
| inputs | Упорядоченные source/batch/snapshot IDs, manifest/data hashes |

Я храню canonical текст и JSONB: текст задаёт точные байты hash, JSONB удобен для
чтения. Формат v1 — compact sorted ASCII JSON с одним LF, UTC microseconds/Z.
Из canonical текста получаю run_key, из префикса commerceguard:run:v1: и run_key —
UUIDv5. prepared_at — техническое время записи, не часть identity.

Fingerprint читаю из четырёх собственных файлов: domain.py, file_contracts.py,
reconcile.py и run_plans.py. Каждый ограничен 256000 байт, конечные symlink отклоняю.
Файл не исполняю ради fingerprint. Изменение комментария в Python тоже меняет этот
hash — это цена точного исходного происхождения. Markdown-правка ID не меняет.
Hash не доказывает подлинность автора и не заменяет сохранение исходников Git.

## Как я выбираю входы

Я использую shared lock схемы и тот же merchant try-lock, что загрузчик S1.
После lock читаю READ COMMITTED: следующие команды видят завершённого предыдущего
писателя, а сотрудничающий ingest этого магазина до конца подготовки не публикуется.
Другие магазины независимы. Писатель в обход протокола и DBA вне этой гарантии.

OMS выбираю только из published batch с is_complete=true, effective_at <= as_of,
observed_at <= as_of и published_at <= knowledge_at. Из доступных версий беру
максимальное effective_at, затем observed_at. Если в этой позиции два разных
снимка с равными effective/observed временами, отказываю OMS_INPUT_AMBIGUOUS.
Не использую произвольный UUID как бизнес-правило «последний победил».
Если полного снимка нет — OMS_INPUT_MISSING, а не пять тысяч ложных orphan-кейсов.

PSP беру из published пакетов того же merchant, с envelope observed_at <= as_of
и published_at <= knowledge_at. Требую хотя бы один пакет: отсутствие PSP не равно
известной нулевой оплате. Я допускаю явно переданный пустой PSP-пакет; он всё равно
не доказывает полноту периода всего провайдера. Watermarks/ожидаемая полнота — S3.
В этом срезе не устанавливаю канонический операционный run и не закрываю кейсы.

Число PSP-пакетов ограничил 10000. При превышении отказываю INPUT_LIMIT, не беру
первые 10000 как полный источник. Сначала записываю один OMS input, затем PSP
в порядке batch UUID. Такой порядок стабилен и входит в canonical identity.
Технические попытки загрузки не входят в inputs: повтор не должен менять набор фактов.

## Атомарность и неизменяемость

Миграция 0004 добавляет ops_run_manifest и ops_run_input: всего 12 постоянных таблиц.
Manifest и все inputs записываю одной транзакцией, затем сверяю число входов до
COMMIT. У inputs есть FK на свой merchant/run, batch/merchant/source и OMS snapshot.
Частичный unique index допускает один OMS, CHECK требует snapshot только для OMS.
Обе таблицы защищаю прежним append-only trigger от UPDATE/DELETE обычного DML.
Полноту количества и наличие PSP обеспечивает application service; PK/FK не
подменяют этот контракт. Прямые привилегии владельца схемы не называю безопасным API.

При точном replay сравниваю сохранённые run_id и весь manifest_text. Возвращаю тот
же ID с duplicate_manifest=true. Конфликт identity не исправляю UPDATE. Если при
неизменном cutoff появился новый допустимый пакет, canonical inputs изменятся и
подготовка создаст другой manifest. Старый остаётся доступен по своему run_id.
Для точного повторения истории нужно читать сохранённый ID, а не заново выбирать
«последние» входы. Выполнение существующего manifest станет отдельной командой CG-202.

## Существенная граница as-was

published_at записываю до COMMIT, поэтому это marker публикации, а не точное время
видимости транзакции. Например, marker 11:59:59 и COMMIT 12:00:01 не позволяют
доказать, что данные уже были видимы ровно в 12:00. Явно фиксирую knowledge_basis;
ретроспективный выбор по marker не выдаю за побайтовую реконструкцию MVCC на прошлую
секунду. Точный as-was повтор относится к уже сохранённым inputs конкретного run.
Для иной гарантии потребуется отдельный протокол capture/commit timeline.

На этом этапе поддерживаю только as-was с равными cutoff. Я не подменяю observed_at
платежа, чтобы запихнуть поздний факт в старый kernel. Раздельные business/knowledge
оси as-known-now требуют нового контракта фильтрации и относятся к CG-204.
Будущее значение cutoff относительно часов БД отклоняю FUTURE_KNOWLEDGE.
Если учебные файлы доставлены позже выбранного cutoff, отсутствие входов — ожидаемый
отказ. Подготовка не должна изображать, что магазин уже загрузил их раньше.

## Подготовленные команды

После самостоятельной установки и db migrate из корня checkout:

```bash
.venv/bin/python -m commerceguard run prepare --merchant M01 --as-of CUTOFF
.venv/bin/python -m commerceguard run show --run-id UUID
```

CUTOFF заменяю на RFC3339 с известным поясом, например свой момент после публикации
baseline; UUID — на ID из prepare. Я не предлагаю фиксированное «время после загрузки»:
реальную загрузку ещё не выполнял. В Windows использую .venv/Scripts/python.exe.
--dsn-env задаёт имя внешней переменной подключения. Prepare возвращает state=prepared,
число входов, ruleset и engine hash. Show читает manifest и calculation_invoked=false (имя CLI поля с CG-202).
Ни одна команда здесь не вызывает reconcile и не показывает выдуманные findings.

Я использую прежние Python/Psycopg/PostgreSQL и pins; новой библиотеки нет.
Модуль run_plans.py связывает storage-adapter с существующим kernel version,
но domain/reconcile не начинают импортировать БД. Не добавляю оркестратор,
HTTP-сервер или новые реальные данные ради подготовки manifest.

## Пример на бумаге и упражнения

Если к cutoff доступны один OMS и один основной PSP, manifest содержит два input.
Повтор подготовки при тех же данных и source bytes даёт тот же ID. Точный replay
PSP-пакета добавит ingest attempt, но inputs manifest останутся прежними.
Публикация нового допустимого PSP-пакета меняет список и даёт новый ID. Пакет с
observed_at после cutoff в старый as-was manifest не попадает, даже если уже есть в БД.

16. Я предлагаю сравнить два OMS с равными effective/observed, но разными content hashes.
Ориентир: OMS_INPUT_AMBIGUOUS, никакого частичного manifest. Найди проверку первых
двух строк selector, объясни, почему сортировка UUID не решает бизнес-конфликт.

17. Повтор PSP создал новую ingest attempt, но не новый batch. Ориентир: повтор
prepare даёт duplicate_manifest=true. Новая попытка доставки не является входом сверки.

18. Измени только комментарий reconcile.py. Ориентир: engine hash и run ID изменятся,
даже если логика та же. Объясни разницу точного source fingerprint и semantic version;
не переписывай сохранённый manifest, чтобы скрыть цену этого решения.

Наблюдённых запусков, ошибок SQL или результатов восстановления у меня нет:
я не исполнял этот код. Не проверял locks, concurrent ingest, права, количество
входов, replay, ОС и временные границы. Подготовленный manifest не равен принятому
бизнес-отчёту. Следующая история — CG-202, сохранённые балансы и evidence.

## Расширение CG-204 · v2

Я теперь создаю manifest v2 с двумя временами, visibility_version и request.
As-known-now требует явный knowledge, reason и опубликованный baseline той же
business даты; as-was сохраняет старое равенство границ. Выбор OMS/PSP и ограничения
описал в LATE_DATA/ADR-25. Предыдущие разделы v1 сохраняю как исторический контракт.
SHA kernel изменился, сохранённый run v1 не переписываю и не обещаю execute новым
движком. Show/result/evidence читают старые сохранённые данные. Всё без запуска.

## Актуальное расширение CG-205 · manifest v3

Я теперь создаю manifest_version=3, ruleset_version=balance-v2,
deadline_version=per-leg-v2; temporal visibility/request v2 сохраняю.
В каждом input закрепляю contract_version из ingest_batch и ту же версию
в ops_run_input. Новое исполнение требует совпадения версии membership с batch
и core OMS. Временной selection и ambiguous snapshot отказ не меняю. Manifest
version, input version, ruleset, deadline version и engine SHA имеют разные задачи.
Старые show/result читаю без пересчёта; старый prepared run нельзя исполнить
новым v3 executor под прежним SHA. Нужен соответствующий checkout/совместимая схема
либо новый run по прежним input v1. Подробности — DEADLINES. Ничего не запускал.
