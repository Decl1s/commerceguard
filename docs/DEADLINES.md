# CG-205: версии ожиданий и отдельные сроки двух денежных плеч

25.10.2026, `0.1.0.dev10`. Я написал этот срез без исполнения приложения,
импорта, генератора, SQL, миграций, проверок и CI. Все числа ниже я разбираю
по спецификации вручную. Фактическую работоспособность пока не подтверждал.

## Какую задачу я решаю

Я представляю заказ на 16000 minor units. Срок подтверждения оплаты уже истёк,
а PSP сообщает только 15000. Позже магазин одобряет возврат 3000 и даёт ещё
несколько дней на его исполнение. Если я заменю общий deadline сроком возврата,
то скрою уже просроченную недоплату. Если оставлю прежний общий срок, то объявлю
недовозврат раньше согласованного срока. Одного timestamp для этих обязательств
недостаточно.

Я отделяю capture_due_at от refund_due_at. Суммы по-прежнему считаю двумя
плечами: возврат не уменьшает ожидаемый capture. Новое одобрение возврата
сохраняю новым полным OMS snapshot, не UPDATE прежней строки. Тогда я могу
объяснить и старое ожидание, и новое, и то, когда каждое стало известно.

## Какие версии я различаю

| Версия | За что она отвечает | Что я сделал |
| --- | --- | --- |
| Файловый OMS v1/v2 | Поля CSV и их смысл | v1 читает общий срок, v2 — два отдельных |
| PSP v1 | Факты оплат/возвратов | Формат, semantic hash и dedup не меняю |
| OMS snapshot ID | Конкретная бизнес-редакция полного ожидания | Новое одобрение — новый snapshot/пакет |
| balance-v2 | Правила наступления расхождения | Срок и состояние каждого плеча независимы |
| Manifest v3 | Закреплённые параметры расчёта | Добавляю input contract_version и deadline_version |
| Result v3 | Представление сохранённого ответа | Добавляю сроки, состояния и версию ожидания в balance |
| Schema 8 | Физическая структура хранения | Добавляю 0008, не переписывая 0001…0007 |
| Case policy v2 | Порядок применения новых правил к карточкам | Переход с v1 делаю явно с ожидаемым head |

Я не называю новым форматом каждое изменение суммы. Два snapshot могут оба
иметь OMS contract_version=2, но разные значения одобренного возврата. Версия
файла отвечает за понимание полей; snapshot ID и raw hash — за конкретную редакцию.
Engine SHA дополнительно связывает run с байтами реализации. Эти идентичности
решают разные задачи и не заменяют друг друга.

## Как я определил новый вход

У OMS v1 остаётся прежний точный CSV header:

```text
merchant_id,order_id,currency,capture_due_minor,refund_due_minor,settle_after
```

У OMS v2 header другой:

```text
merchant_id,order_id,currency,capture_due_minor,refund_due_minor,capture_due_at,refund_due_at
```

Я выбираю parser по contract_version в manifest, а не угадываю формат по числу
запятых. Envelope полей не изменяю; версия 2 разрешена только OMS, PSP остаётся 1.
Оба срока v2 обязательны, имеют RFC3339 timezone и нормализуются в UTC.
Пустое поле, только один срок или смешанный header отвергаю. Уникальность
merchant/order внутри полного snapshot и денежные ограничения сохраняю.

Я не навязываю порядок capture_due_at<=refund_due_at: вход должен явно описать
оба обязательства, а не вывести второе из первого. Срок может быть раньше
observed_at, если источник поздно сообщил уже просроченное ожидание. Иначе я
не смог бы описать позднюю корректировку честными timestamps.

## Как я сохраняю совместимость

В OrderExpectation я оставил прежний settle_after и прежние первые шесть
аргументов. Если отдельных сроков нет, версия ожидания равна 1 и оба эффективных
deadline берутся из settle_after. Если оба заданы, версия равна 2, а
settle_after должен равняться их максимуму. Это общий горизонт совместимости,
он больше не откладывает проверку второго, уже просроченного плеча.

В core я добавил expectation_version с default 1 и два nullable deadline.
У старой строки новые сроки остаются NULL; я не выполняю UPDATE её сумм,
срока, raw или snapshot. Новый v2 сохраняет оба срока и вычисленный максимум.
FK связывает expectation_version с версией соответствующего ingest_batch.
SQL check различает допустимую legacy/v2 форму и не позволяет сохранить
половину нового контракта. Table count остаётся 20; новых таблиц здесь нет.

Semantic hash старого OMS v1 я сохраняю прежним: версия payload oms:v1,
те же поля и canonical settle_after. PSP hash тоже не меняю. Для нового OMS
использую oms:v2 и оба срока. Поэтому старый пакет не становится новым только
из-за обновления parser, а изменение любого срока v2 меняет смысл новой строки.
Canonical file manifest v1 также сохраняет прежнее представление.

## Где я разместил изменения

| Файл | Что я в нём делаю | Почему |
| --- | --- | --- |
| domain.py | Совместимый объект ожидания и расширенный balance | Не связываю деньги и сроки с драйвером |
| file_contracts.py, file_inputs.py | Явный выбор CSV v1/v2 и отдельный semantic payload | Не смешиваю неизвестные headers и не меняю v1 identity |
| ingestion.py, sql/stage_input.sql | Передаю version/deadlines через COPY в core | Временная staging форма соответствует полям публикации |
| 0008_expectation_deadlines.sql | Добавляю поля/FK/checks и расширяю версии | Предыдущую историю миграций сохраняю побайтно |
| reconcile.py | Считаю состояние каждого плеча | Просроченная оплата не ждёт срока возврата |
| run_plans.py, run_execution.py | Manifest/result v3, contract membership и сериализация сроков | Прошлый отчёт не зависит от latest snapshot |
| run_changes.py | Показываю ruleset/deadline change отдельно | Не приписываю изменение правил поздним фактам |
| case_store.py | Явный policy upgrade с ожидаемым head | Не меняю значение истории автоматически |
| sample_data.py, __main__.py | Сценарий split-deadlines и аргумент перехода | Даю понятный маршрут для будущего ручного знакомства |

## Как я вывожу состояние заказа

Для каждого плеча я сначала считаю actual и delta=actual−expected. Затем
сравниваю as_of с его deadline. До срока состояние pending, даже если суммы
уже совпадают. В сам момент deadline я считаю срок наступившим: совпадение
даёт matched, отличная сумма — discrepancy и соответствующий finding.
Ту же политику применяю к shortfall и excess; немедленное обнаружение excess
до срока было бы другим бизнес-правилом, которое я здесь не добавлял.

Общее состояние выбираю явно: discrepancy важнее pending, pending важнее
matched. Поэтому заказ может иметь capture_state=discrepancy,
refund_state=pending и общий discrepancy. Если первое плечо matched, а второе
pending, общий pending. При currency mismatch обе денежные оценки blocked,
actual/delta остаются NULL; я не складываю RUB и USD ради частичного ответа.

В Result v3 я сохраняю оба срока, оба состояния и expectation_version каждого
balance. Если finding по суммам/evidence не изменился, отдельная Case revision
не создаётся только из-за нового snapshot. Однако application и last_seen run
сохраняют новое наблюдение, а balance/input manifest объясняют его сроки и источник.

## Как я разбираю пример по времени

В split-deadlines у O1003 ожидаемый capture=16000, фактический=15000.
Capture deadline — 23 октября 12:00 UTC. После одобрения возврата ожидаю refund=3000,
фактический refund=1000, refund deadline — 26 октября 12:00 UTC.

На 24 октября 12:00 UTC при подходящем знании я вручную ожидаю payment_shortfall
на 1000, capture discrepancy и refund pending. Я ещё не создаю refund_missing.
На 26 октября 12:00 UTC при тех же суммах я ожидаю дополнительно refund_missing
на 2000. Общее состояние в обоих случаях discrepancy, но основания разные.
Именно поэтому один общий state без per-leg details был бы неполным объяснением.

Я добавил два полных v2 snapshots: oms-before с refund_due=0 и oms с одобренными
3000. Effective/observed определяют, когда snapshot действует и когда стал известен.
Выбор latest по effective, затем observed остаётся прежним; одинаковая пара
времён двух разных snapshots по-прежнему неоднозначна и приводит к отказу.
Я не выбираю формат v2 только потому, что его номер больше: время и полнота
важнее номера формата. Поздний v1 snapshot также может быть выбран по контракту.

## Как я связываю run с версиями

Я закрепляю contract_version каждого input в manifest v3 и ops_run_input.
Execution сравнивает его с опубликованным batch, затем проверяет версию core OMS.
Ограничения 10000 orders / 50000 receipts / 16 MiB result сохраняю.
Result v3 сериализует deadline как canonical UTC, а не произвольную локальную строку.

Я не переписываю manifests/results v1/v2 и не подменяю их engine SHA.
Новый executor принимает v3/balance-v2; старые show/result/evidence продолжают
читать сохранённый ответ без повторного вычисления. Для исторического execute
нужны соответствующая реализация и совместимая схема; автоматического архива
всех старых executors я пока не написал. Старые input файлы при этом можно
использовать в новом run: их общий срок адаптируется к двум одинаковым deadline.

В run changes я разрешил сравнение известных balance-v1/v2 findings при том же
merchant/as_of и возрастающем knowledge. Показываю оба ruleset и ruleset_changed,
engine_changed, deadline_version_changed. Это сравнение отчётов, не доказательство,
что все отличия возникли из-за новых платежей. Неизвестные будущие ruleset
не объявляю совместимыми автоматически.

## Как я перевожу существующие Case

Первый stream нового магазина может начаться с balance-v2. Для магазина, у
которого уже есть v1 stream, обычный case apply v2 возвращает CASE_UPGRADE_REQUIRED.
Я должен явно передать --upgrade-from-run-id с точным текущим canonical run.
Под тем же merchant lock проверяю predecessor, strictly newer as_of и
неубывающий knowledge. Исторические as-known-now corrections остаются report-only.

Если head успел измениться, получаю CASE_UPGRADE_HEAD_MISMATCH, не автоматический
повтор с новой базой. Я сохраняю upgrade_from_run_id и policy v2 в immutable
application ledger одним COMMIT с карточками и событиями. Case key и история
остаются прежними; обратный переход на v1 не поддерживаю. Повтор уже применённого
run остаётся noop даже после дальнейшего продвижения. Case show показывает
текущую application policy и upgrade source, включая случай без новой revision.

Я не выдаю этот CLI флаг за систему человеческого согласования или RBAC.
Роли/назначения/ручное закрытие относятся к S4. Нынешний workflow пока open,
absence по-прежнему не означает человеческое resolved.

## Как я предлагаю познакомиться с изменением

Команды ниже я не выполнял. Сначала отдельно нужно разрешить запуск и подготовить
БД/миграции. Значения NEW_RUN и CURRENT_HEAD заменяю реальными UUID.

```text
python -m commerceguard input generate --output workspace/split --scenario split-deadlines
python -m commerceguard input inspect --manifest workspace/split/oms.manifest.json --data workspace/split/oms.csv
python -m commerceguard case list --merchant M01 --presence all
python -m commerceguard case apply --run-id NEW_RUN --upgrade-from-run-id CURRENT_HEAD
```

Генератор должен создать 9 файлов, включая GENERATED.md: два OMS CSV/manifest,
основной и late PSP JSONL/manifest. Он не вызывает reconcile и не заменяет output.
Между inspect и case apply нужны обычные publish → prepare → execute из WORKBENCH
и RESULTS; это не четыре команды полного сценария с пустой БД.

Для знакомства с двумя snapshot я сначала публикую oms-before и PSP, создаю
baseline с фактическим T0 после публикации. Затем публикую oms и выбираю T1 после
нового COMMIT marker. Фиксированные прошлые даты fixture не позволяют создать
as-was до фактического приёма пакета. Для мысленного примера 24/26 октября выше
я использовал контракт данных, а не наблюдённый запуск PostgreSQL. Ограничение
published_at как marker до COMMIT из LATE_DATA сохраняю.

## Пять заданий с проверкой ответа

1. Я ставлю as_of между capture и refund deadline O1003. Ожидаю один денежный
   finding по capture, refund pending, общий discrepancy. Проверяю условие
   deadline в цикле reconcile и приоритет общего состояния.
2. Я переношу as_of точно на refund deadline. Ожидаю второй finding и refund
   discrepancy; equality означает наступивший срок, а не ещё одну секунду ожидания.
3. Я беру v1 файл с settle_after=T. Ожидаю оба deadline=T, expectation_version=1
   и прежний semantic hash v1. Не переписываю CSV/manifest ради нового parser.
4. Я меняю только refund deadline в новом v2 snapshot. Ожидаю новый semantic SHA,
   новый batch/snapshot identity при соответствующем manifest, прежнюю историю
   старого run. Одного изменения файла без пересчёта content SHA недостаточно.
5. Я применяю новый v2 run к существующему v1 stream сначала без upgrade source,
   затем с устаревшим head. Ожидаю REQUIRED и HEAD_MISMATCH, старую карточку
   сохраняю. Только точный актуальный predecessor разрешает запись перехода.

Я пока не выполнял ни один из этих сценариев. Новых библиотек не добавлял.
Реальные ошибки исполнения неизвестны; синтаксис, SQL, сериализацию, replay,
конкуренцию и совместимость ОС не проверял. Следующий отдельный срез — CG-301,
SQL-витрины по завершённым результатам; S2 остаётся Review/unverified.
