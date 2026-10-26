# CG-302: я сверяю перечисление и комиссию провайдера

26.10.2026, `0.1.0.dev12`. Я добавил отдельную сверку расчётного пакета PSP,
сохранил выписку, состав событий и объяснение результата. Основной сценарий
проверил на Linux/PostgreSQL 16.15. Это учебная модель финансового контроля:
реальный эквайринг, банковские переводы и коммерческого клиента не подключаю.

## Какой бизнес-вопрос я решаю

Финансист видит оплату заказа, но этого недостаточно для проверки перечисления.
Провайдер может объединить несколько оплат и возвратов, удержать комиссию и
сообщить итоговую сумму net. Я хочу ответить: «Какие события вошли в этот пакет,
правильно ли посчитаны четыре суммы и на каких исходных строках основан вывод?»

Я разделил ingest batch и settlement batch. Первый означает доставку файла:
повторно присланная оплата создаёт receipt, но не новые деньги. Второй означает
расчётный пакет провайдера с собственным settlement_id. Идентификатор файла или
время его получения не определяет принадлежность денег к перечислению. Поэтому
состав settlement я принимаю явно через event_ids, а не угадываю по дате загрузки.
OMS при этом не нужен для формулы комиссии: я не распределяю удержание по заказам
пропорционально их суммам и не меняю существующие Case.

## Мой контракт выписки

Я принимаю один UTF-8 JSON object с ровно следующими полями:

```json
{
  "contract_version": 1,
  "merchant_id": "M01",
  "settlement_id": "PSP-20261022-RUB",
  "revision": 1,
  "currency": "RUB",
  "period_start": "2026-10-22T00:00:00Z",
  "period_end": "2026-10-23T00:00:00Z",
  "observed_at": "2026-10-23T13:00:00Z",
  "is_complete": true,
  "expected_event_count": 4,
  "event_ids": ["C01", "C02", "C03", "R03"],
  "gross_minor": 36000,
  "refund_minor": 1000,
  "fee_minor": 720,
  "net_minor": 34280
}
```

Я храню деньги целыми minor units: для RUB 36000 означает 360 рублей. Gross,
refund и fee неотрицательны, net может быть отрицательным. Float, bool вместо
integer, NaN, повтор JSON key, лишнее поле, повтор event ID и наивное время
отклоняю. Версия контракта — 1; валюты RUB/USD/EUR не конвертирую. Все timestamps
нормализую в UTC. Период полуоткрытый: start включён, end исключён; для complete
выписки observed_at не может быть раньше end.

Лимиты: 1 MiB исходного и нормализованного документа, до 10000 событий,
revision от 1 до 1000000. Каждая неотрицательная сумма ограничена 10^16,
net — диапазоном ±2×10^16. JSON parser для этой агрегированной выписки явно
разрешает до 18 цифр integer token; денежные границы проверяю отдельно.
Для прежних OMS/PSP сохранил стандартный предел 16 цифр. Это разные уровни
защиты: лексический предел не заменяет предметный диапазон.

Я сортирую event_ids и ключи, нормализую даты, добавляю LF и считаю canonical SHA.
Из него получаю advice_id UUIDv5. Другие пробелы или порядок участников меняют raw
SHA исходного файла, но не смысл выписки. SHA фиксирует байты, подлинность
отправителя он не доказывает.

## Почему у меня есть revision и assignment

Ключ business revision — merchant/settlement_id/revision. Равный смысл при повторе
даёт noop. Другой смысл с тем же ключом даёт SETTLEMENT_REVISION_CONFLICT.
Для исправления я создаю новую revision; автоматического выбора latest нет.
Историческую revision могу загрузить позже новой. Валюта и период у семейства
settlement_id фиксированы: их изменение требует отдельного business ID.

Я закрепляю merchant/event за одним settlement_id в assignment. Повторное
упоминание в revision того же пакета допустимо, перенос в другой пакет — отказ
всей публикации. FK на canonical PSP fact намеренно нет: выписка может прийти
раньше события, и тогда нужен unknown. Это консервативная политика: даже удаление
участника в новой revision не освобождает его для другого пакета. Отмену или
переназначение я ещё не реализовал; прямое удаление assignment не предлагаю.

## Как я считаю деньги независимо от выписки

Я передаю тариф отдельно, обязательным --fee-bps. Один basis point равен 0,01%;
200 bps означает 2%. Допускаю целый тариф от 0 до 10000. Версия моей политики —
gross-bps-half-up-v1: комиссия с общей суммы capture, одно округление половины
minor unit вверх, без возврата комиссии при refund.

```text
gross = сумма capture участников
refund = сумма refund участников
fee = (gross * fee_bps + 5000) // 10000
net = gross - refund - fee
delta = reported - expected
```

Я не беру reported fee как ожидаемую: иначе удержание провайдера проверяло бы
само себя. Для примера я получил 36000/1000/720/34280 и matched. Выписка с fee800
и net34200 арифметически согласована сама с собой, но даёт fee delta +80 и net
−80 относительно тарифа. Её состояние discrepancy. Если reported net не равен
reported gross−refund−fee, добавляю reported_arithmetic_mismatch при известных
входах. Знак delta здесь reported−expected; он не обязан совпадать с соглашением
дельты в OMS order reconciliation.

Для capture25 при 200bps комиссия равна 1 minor unit, поскольку 0,5 округляю вверх.
Пакет только с refund1000 даёт gross0/fee0/net−1000. Это допустимый signed net.
Политика — явное учебное допущение, не универсальный тариф всех эквайеров:
минимальную комиссию, сложный тариф, chargeback, FX и банковский T+N не моделирую.

## Когда я отказываюсь называть число известным

Я сохраняю unknown, если период ещё открыт, выписка incomplete, число членов
меньше expected_event_count, отсутствует видимый PSP факт, валюта не совпадает
или occurred_at лежит вне периода. Причины сохраняю кодами, проблемные IDs —
отдельными списками. Expected и delta всех четырёх сумм тогда NULL; частичный
итог не выдаю за перечисление. Reported суммы и факт их внутренней арифметической
согласованности остаются доступны для объяснения.

Я отличаю «ничего не поступило» от явного complete пакета с expected_event_count0
и пустым event_ids. Только во втором случае могу получить известные нули.
Само утверждение complete приходит извне, сверка не доказывает полноту внешнего
провайдера: если он исключил событие и занизил ожидаемое количество согласованно,
независимого банковского источника для обнаружения такой потери пока нет.

## Как я фиксирую время и происхождение

Run принимает один явный as_of, не будущий относительно часов БД. К нему должны
быть видимы сама выписка, published PSP batch и receipt; occurred_at и observed_at
также не позже cutoff. Published_at — marker до COMMIT, не точное время фиксации
транзакции. Я не обещаю восстановить исторический MVCC snapshot по одному marker.

Для каждого участника я выбираю один допустимый receipt через LEFT JOIN LATERAL,
сначала по observed_at, затем batch_id/row. Повторная доставка не размножает
сумму; отсутствие receipt остаётся строкой с NULL, а не исчезает из состава.
Evidence содержит event_id, batch_id, номер raw записи, record SHA и raw key.
Отдельно сохраняю advice canonical/raw SHA и raw key исходной выписки.

Request identity включает advice_id, cutoff, тариф, visibility policy и SHA
точных исходников движка. По request key получаю report_id. Повтор возвращает
сохранённый результат без пересчёта. Поздний PSP факт требует нового cutoff и
нового report; старый unknown не заполняется задним числом. Я читаю старые
сохранённые результаты независимо от текущего engine SHA, но архив исполнения
любой прежней версии движка автоматически не поставляю.

## Где я разместил реализацию

| Файл / таблица | Зачем я выделил эту границу |
| --- | --- |
| settlement_contract.py | Я проверяю JSON, нормализую identity и создаю три synthetic примера без БД |
| settlement.py | Я держу чистую формулу и completeness отдельно от SQL/CLI |
| settlement_store.py | Я публикую revision, выбираю evidence и сохраняю неизменяемый report |
| raw_store.py | Я повторно использую content-addressed объекты для одного документа |
| 0009_settlement.sql | Я добавляю четыре таблицы, не меняя опубликованные 0001…0008 |
| core_settlement_advice | Я храню business revision, canonical/raw происхождение |
| core_settlement_event_assignment | Я исключаю двойное назначение события разным пакетам |
| core_settlement_member | Я фиксирую точный состав каждой revision |
| ops_settlement_result | Я сохраняю request, payload, SHA и состояние одним COMMIT |
| mart_settlement_reconciliation.sql | Я показываю одну строку на report_id, без суммирования revisions |

На публикации я использую merchant advisory lock, проверку schema и одну DB
транзакцию. Все четыре таблицы защищаю от UPDATE/DELETE. Финансовую формулу не
переношу в CLI. dbt читает сохранённые отчёты: новые fee/NULL data tests независимо
проверяют их контракт, но не изменяют core. Теперь в схеме 24 persistent tables,
в аналитике 9 views.

## Как я пробую сценарий руками

Для полного безопасного прогона я использую README: unit tests и
scripts/check_postgres.py. Runner сам создаёт и удаляет свою БД без TCP. Для
ручного изучения я сначала готовлю собственную отдельную БД по STORAGE и внешнюю
COMMERCEGUARD_DATABASE_URL. Следующие команды выполняю из корня checkout:

```bash
.venv/bin/python -m commerceguard input generate --output workspace/input-cg302
.venv/bin/python -m commerceguard db migrate
.venv/bin/python -m commerceguard ingest publish --manifest workspace/input-cg302/psp.manifest.json --data workspace/input-cg302/psp.jsonl
.venv/bin/python -m commerceguard settlement generate --output workspace/settlement
.venv/bin/python -m commerceguard settlement inspect --input workspace/settlement/matched.json
.venv/bin/python -m commerceguard settlement publish --input workspace/settlement/matched.json --raw-root workspace/raw
.venv/bin/python -m commerceguard settlement run --advice-id UUID_ИЗ_PUBLISH --as-of ТЕКУЩИЙ_UTC_RFC3339 --fee-bps 200
.venv/bin/python -m commerceguard settlement result --report-id UUID_ИЗ_RUN --limit 50
```

Я заменяю UUID placeholders значениями JSON ответа; cutoff беру текущим UTC после
publish, например получаю через `date -u +%Y-%m-%dT%H:%M:%SZ`. Для гарантии, что
секунда позже publication marker, жду следующую секунду либо задаю timestamp с
микросекундами. Старую дату предметного периода вместо текущего cutoff не
подставляю: сегодняшняя публикация тогда ещё не была видима. Генератор settlement
создаёт только три выписки; PSP facts создаёт и публикует отдельный input маршрут.
OMS для этой сверки не требуется. Существующие output каталоги не перезаписываю.

--input означает один файл, --raw-root — мой managed raw store, --dsn-env — имя
переменной подключения, --advice-id — конкретную revision, --as-of — границу
видимости, --fee-bps — независимый тариф. Result --limit принимает 1…1000 и режет
только вывод evidence/списков IDs с флагами truncation. Result SHA относится к
полному сохранённому payload, а не к сокращённому ответу viewer.

## Сбои, повторы и мои реальные проверки

Я сначала записываю raw, затем публикую DB. Конфликт может оставить orphan object;
другие пробелы при равном смысле также могут сохранить дополнительный raw, а
ссылка опубликованной revision останется первоначальной. Автоматическую GC не
написал. Ingest scan-raw/recover перечисляет manifest-based OMS/PSP, standalone
выписку автоматически не обнаруживает. Для неё повторяю settlement publish с
исходным файлом. Отдельного settlement attempt/failure journal пока нет.

При неопределённом результате COMMIT я повторяю тот же файл или точный request,
не объявляю rollback по сетевой ошибке. Идентичность и immutable result позволяют
найти успешную публикацию, если она состоялась. Доступность raw и резервное
копирование БД остаются отдельными эксплуатационными задачами S5.

Я прошёл 27 Python tests, обновил заполненную схему8 до9, сохранил SHA четырёх
прежних run и получил 11 settlement reports/9 advice revisions. Проверил late
fact, mismatch80, NULL, zero, negative net, исключённый end, конфликт revision/
assignment и отказ UPDATE. dbt завершил 9 models+19 tests: PASS28, ERROR0.
При разработке я заметил конфликт старого 16-значного JSON лимита с агрегатом
10^16: добавил отдельный явный предел и регрессию до integration. Это найденное
несоответствие контрактов, не выдуманный производственный инцидент.
Windows, конкурентных writers, power loss и CI я не проверял; полная матрица —
VALIDATION. Тарифный справочник, HTTP/RBAC и ручной финансовый workflow впереди.

## Пять моих упражнений с проверкой ответа

1. Я меняю только --fee-bps с 200 на 201 для той же advice/cutoff. Ожидаю новый
   report_id, fee724, net34276, delta fee−4/net+4 и discrepancy. Исходный report
   сохраняет fee720. Я объясняю, почему тариф входит в identity.
2. Я публикую incomplete.json после matched.json. Ожидаю новую advice revision,
   unknown и NULL expected/net, хотя четыре PSP события уже доступны. Я не
   исправляю это COALESCE в SQL.
3. Я публикую fee-mismatch.json. Ожидаю reported_arithmetic_ok=true и одновременно
   fee_mismatch/net_mismatch. Я объясняю различие арифметической проверки выписки
   и независимой проверки тарифа.
4. Я меняю пробелы и порядок event_ids в копии matched.json. Ожидаю прежний
   advice_id и duplicate_advice=true, другой raw SHA файла возможен. Меняю сумму
   без увеличения revision — ожидаю SETTLEMENT_REVISION_CONFLICT.
5. Я делаю complete пустой пакет с новым settlement_id и нулевыми суммами,
   затем incomplete пустой пакет другой revision. Первый matched с нулями,
   второй unknown с NULL. Я добавляю свою проверку этого различия в SQL.

Для собеседования я объясняю grain report_id, различие fact/receipt/membership,
почему не делаю INNER JOIN при неизвестном событии, зачем independent fee policy,
чем deterministic request отличается от исторического snapshot и какие свойства
требуют fault/concurrency проверок сверх зелёного основного сценария.
