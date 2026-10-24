# CG-105: учебное рабочее место приёма

24.10.2026, 0.1.0.dev5. Я написал команды и сценарии без запуска. Ожидаемые числа
ниже вывел из контракта вручную; stdout, успешную БД и пройденный S1 не заявляю.

## Какую задачу я закрыл в исходниках

Раньше для знакомства с ingestion надо было самому составлять строгий manifest
и считать SHA/размеры. Я добавил input generate: он формирует только синтетический
OMS CSV и PSP JSONL, отдельно позднее поступление и соответствующие manifest.
Теперь один учебный маршрут связывает generate → inspect → publish → status → replay.
Для ошибочного пакета добавил подготовленные варианты и путь к quarantine/recover.
Это CLI, без веб-сервера, постоянной службы, реального магазина и облака.

## Файлы и границы

| Файл | Что я в нём сделал |
| --- | --- |
| sample_data.py | Чистое построение байтов, затем запись только в новый каталог |
| ingest_status.py | Read-only metadata по batch, attempt или manifest hash |
| __main__.py | Аргументы и JSON-вывод; без бизнес-расчёта в обработчике CLI |

В наборе шесть data/manifest файлов и GENERATED.md, записанный последним:
oms.csv, oms.manifest.json, psp.jsonl, psp.manifest.json, psp-late.jsonl,
psp-late.manifest.json. Ни одна из этих выгрузок не входит в исходники Git.
Я использую постоянные ID M01/O1001… и даты предметной модели октября 2026 года.
Системные часы, контакты, документы и окружение не служат источником данных.
Повтор одинакового сценария даёт одинаковые data/manifest байты; имя output-каталога
на identity пакета не влияет. Номер попытки при публикации при этом всегда новый.

Существующий output-каталог, даже пустой, не заменяю. При сбое записи могу оставить
частичный набор; не удаляю пользовательские файлы ради повторного запуска. Успех
возвращаю после записи всех файлов, но общей транзакции filesystem для набора
не обещаю. Для повторной генерации выбираю новое имя каталога.

## Базовый маршрут, который я подготовил

Команды ниже предназначены для самостоятельного запуска позже, из корня checkout.
Нужны Python 3.12, отдельная БД commerceguard/PostgreSQL 16 и драйвер из
requirements-postgres.lock. Подключение задаю внешней переменной
COMMERCEGUARD_DATABASE_URL; пароль не передаю как аргумент и не записываю в Git.
Сервер, роль, системную службу и глобальные библиотеки этими командами не создаю.

```bash
.venv/bin/python -m commerceguard input generate --output workspace/input
.venv/bin/python -m commerceguard input inspect --manifest workspace/input/oms.manifest.json --data workspace/input/oms.csv
.venv/bin/python -m commerceguard input inspect --manifest workspace/input/psp.manifest.json --data workspace/input/psp.jsonl
.venv/bin/python -m commerceguard db migrate
.venv/bin/python -m commerceguard ingest publish --manifest workspace/input/oms.manifest.json --data workspace/input/oms.csv
.venv/bin/python -m commerceguard ingest publish --manifest workspace/input/psp.manifest.json --data workspace/input/psp.jsonl
```

На Windows заменяю .venv/bin/python на .venv/Scripts/python.exe. Установка драйвера
и создание БД описаны в STORAGE. Generate и inspect не нуждаются ни в PostgreSQL,
ни в Psycopg; они не мигрируют схему и не публикуют факты.

Ручные ориентиры для пустого core: OMS — 5 raw-строк/5 ожиданий/1 snapshot;
PSP — 7 raw-строк, 6 уникальных событий и 1 внутрипакетный дубль, 7 receipts.
C01 встречается дважды, но даёт одну оплату. C05 имеет USD вместо ожидаемого RUB,
C99 ссылается на неизвестный O1999. Это валидные входные факты; их бизнес-разбор
относится к сверке S2, а не к структурному карантину.

После publish смотрю batch_id и attempt_id. Статус по одному из ключей:

```bash
.venv/bin/python -m commerceguard ingest status --batch-id UUID
.venv/bin/python -m commerceguard ingest status --attempt-id UUID
.venv/bin/python -m commerceguard ingest status --manifest-sha SHA256 --limit 20
```

UUID/SHA256 заменяю на свои значения. Status читает batch counts, source, hash,
received/published времена и ограниченную историю попыток; payload raw и полный
manifest JSON не выводит. Снимок READ ONLY/REPEATABLE READ согласует обе таблицы.
Невалидный ID вызывает безопасный отказ, отсутствие объекта даёт found=false,
не искусственный failed. attempts_truncated сообщает об обрезанной истории.
У status нет побочного эффекта восстановления или автоматического migrate.

Повторяю publish с тем же PSP manifest/data. Ориентир: duplicate_batch=true,
raw_rows_inserted=0 и new_facts=0, новая попытка duplicate, canonical фактов всё ещё 6.
Инвариант new+known+duplicate_rows относится к первой публикации нового batch;
отчёт повторного вызова показывает действия текущего replay, не старые счётчики.

## Позднее поступление я вынес отдельно

psp-late содержит только C02L на 1000 minor units с observed_at 25 октября.
Основной PSP manifest наблюдался 24-го. Если смешать их в один envelope с более
поздним observed_at, выбор входов для исторического run стал бы менее очевидным.
Отдельный пакет позволяет явно закрепить, что система знала 24-го и 25-го.

После его публикации PSP canonical событий станет 7, raw PSP-строк/receipts — 8.
Ожидаемая недоплата O1002 закроется только в новом расчёте с допустимыми входами
и cutoff; сохранённого run в S1 ещё нет. Я не обновляю старый результат сверки
путём редактирования события или его времени. Это следующий этап S2.

## Три сценария отказа

```bash
.venv/bin/python -m commerceguard input generate --output workspace/broken --scenario invalid-json
.venv/bin/python -m commerceguard input generate --output workspace/conflict --scenario conflict
.venv/bin/python -m commerceguard input generate --output workspace/earlier --scenario earlier-observed
```

Я намеренно пересчитываю file hash для каждого варианта: это не транспортное
повреждение, а контрактный/бизнес-отказ после сохранения корректно идентифицированного raw.

- invalid-json: в PSP-строке 7 нарушен JSON. Ориентир — quarantined/structural,
  JSON_SYNTAX, error_row=7; новый core не появляется даже для предыдущих строк.
- conflict: второе C01 имеет amount_minor=10001 вместо 10000. Ориентир —
  quarantined/business/PSP_CONFLICT, строка 2. Я не выбираю «последнее значение».
- earlier-observed: первое C01 имеет observed_at 10:00:30 вместо 10:01.
  После уже опубликованного baseline ожидаю TEMPORAL_CONFLICT относительно core.
  На пустой БД это допустимое первое наблюдение, поэтому сценарий требует baseline.

Сами generate-команды лишь записывают файлы. Для попытки загрузки использую publish
с manifest и PSP data соответствующего каталога. Inspect поймает первые два случая
без БД, но временной конфликт с сохранённым core виден только publish.
Recovery того же ошибочного manifest не исправляет данные и снова отклонит пакет.
Путь разбора диагноза я описал в RECOVERY; всё это пока не исполнял.

## Как я предлагаю менять проект под себя

Новые синтетические суммы и ID меняю в sample_files, формат и допустимые значения —
сначала в DATA_CONTRACTS/file_contracts. Ключ hash/UUID не меняю ради обхода дубликатов.
Новый показатель status добавляю явной колонкой SELECT и в _record, не печатаю
весь объект драйвера. Лимит истории ограничивает ответ, а не доказанную нагрузку.
Смена fixture сама по себе не меняет ruleset и не превращает учебный случай в
реальную выгрузку. Новых сторонних библиотек и миграций в CG-105 я не добавлял.

Ограничения: нет интерактивного UI, автоматического provisioning, profile-secret
хранилища, бесконечной истории в stdout, полной пагинации raw scan, offline failure
spool и сохранённой сверки. Весь S1 написан, но не принят как проверенный Increment.
Производительность, права, ОС, транзакции и реальные результаты я пока не проверял.
