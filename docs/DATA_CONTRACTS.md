# Контракты v1: единица строки, деньги и время

Предметный контракт описан domain.py; CG-101 добавил SQL основы хранения
([STORAGE](STORAGE.md)). CG-102 описывает envelope/parser в [INPUTS](INPUTS.md)
и file_contracts.py / file_inputs.py. CG-103 написал постоянный приём и атомарную
публикацию ([INGESTION](INGESTION.md)); выбор snapshot для run остаётся S2.
Все исходники без исполнения.

## OMS expectation: один заказ в одном полном снимке

| Поле | Тип и ограничение | Смысл |
| --- | --- | --- |
| merchant_id | ASCII ID 1–64, буквы/цифры/_/-; первый символ буква/цифра | Магазин, часть всех бизнес-ключей |
| order_id | Такой же ID | Заказ внутри магазина |
| currency | RUB, USD, EUR | Валюта всех сумм ожидания |
| capture_due_minor | int, 0..10^12, без bool | Полная ожидаемая сумма подтверждённых capture |
| refund_due_minor | int, 0..capture_due_minor | Сумма одобренных возвратов, ожидаемых к deadline |
| settle_after | datetime с поясом, нормализуется UTC | С этого момента обычные отклонения становятся findings |

Ключ текущего снимка — merchant_id/order_id; повтор запрещён даже для равных строк.
Версия v1 получает один полный snapshot от вызывающего кода. Загрузчик S1 дополнит
manifest snapshot_id, contract_version, effective_at, observed_at, row_count,
content_sha256 и признак полноты. Исторический выбор snapshot должен учитывать
effective_at <= as_of и observed_at <= as_of, затем выбирать согласованную версию.
Kernel пока не умеет доказывать полноту или выбирать версию OMS.

refund_due_minor — **не** вычитаемая скидка и не перечень всех запросов покупателей.
Это уже одобренная обязанность вернуть сумму. Отмена неоплаченного заказа задаёт
0/0, отмена оплаченного с полным возвратом — capture_due/refund_due одинаковы.
Споры, chargeback, reversal и авторизации в v1 не входят. Общий settle_after упрощает
пример: разные deadlines для каждого денежного плеча — отдельная будущая версия.

## PSP event: один неизменяемый подтверждённый факт

| Поле | Тип и ограничение | Смысл |
| --- | --- | --- |
| merchant_id | ID | Пространство имён одного PSP v1 |
| source_event_id | ID | Уникальный ID факта, ключ вместе с merchant_id |
| order_id | ID | Бизнес-ссылка на OMS, не FK при сырой загрузке |
| currency | RUB, USD, EUR | Валюта именно этой операции |
| kind | EventKind.CAPTURE или EventKind.REFUND | Фактическое подтверждённое списание/возврат |
| amount_minor | int, 1..10^12; bool/float запрещены | Положительный размер факта; знак определяет kind |
| occurred_at | aware datetime → UTC | Время совершения факта у провайдера |
| observed_at | aware datetime → UTC, >= occurred_at | Первое наблюдение системой |

Семантический fingerprint: order_id, currency, kind, amount_minor, occurred_at.
Два видимых события с одним merchant/source_event_id и равным fingerprint — один
факт. Наименьший observed_at сохраняется. Разный fingerprint под тем же ID —
ContractError всей партии, без «последняя строка победила». Перед дедупликацией
kernel исключает факты за пределами as_of, чтобы конфликт из будущего не менял прошлое.
Это локальная дедупликация одного расчёта, ещё не гарантии повторной загрузки в БД.

Источнику с исправляемыми ID нужен отдельный correction/reversal-контракт.
Связь refund с конкретным capture и ограничение возврата по capture ещё не реализованы;
сейчас сравнивается сумма на уровне заказа. Добавление второго PSP требует provider_id
в ключе и миграции версии, а не молчаливого объединения пространств имён.

## Расчёт

```text
visible(event) = occurred_at <= as_of AND observed_at <= as_of
capture_actual = SUM(amount_minor WHERE kind=capture)
refund_actual  = SUM(amount_minor WHERE kind=refund)
capture_delta  = capture_actual - capture_due_minor
refund_delta   = refund_actual - refund_due_minor
```

Суммируем только уникальные видимые факты одной валюты. Положительная delta означает
избыток фактического плеча; отрицательная — нехватку. refund_delta=-2000 означает
неисполненный ожидаемый возврат 20 рублей, а не «магазин потерял 20 рублей».
Два плеча не неттируются при поиске расхождений. Даже при нулевом net-delta
могут появиться два разных finding.

## Приоритет правил

1. Отсутствие заказа в переданном полном снимке → orphan_payment по валюте;
   финансового баланса такого заказа нет. Это повод проверить связь, не признание убытка.
2. Любой видимый факт другой валюты → currency_mismatch, весь баланс blocked;
   actual и delta равны null, потому что частичная сумма может ввести в заблуждение.
3. До settle_after → pending даже при временном совпадении сумм; денежные findings
   пока не создаются. Структурные правила 1–2 не ждут срока.
4. На границе as_of == settle_after и позже применяются payment_shortfall/excess
   и refund_missing/excess. Обе delta равны нулю → matched, иначе discrepancy.

## Finding и будущий case

Finding — результат правила, case — операционная карточка человека. Нельзя смешивать
их жизненные циклы. Ключ finding/case v1:
SHA256(JSON([merchant_id, order_id, currency, rule_code])). Для currency_mismatch
currency — неожиданная валюта события. Одна и та же проблема с новой суммой имеет
тот же case_key, но новую finding_revision в новом run. Исчезновение finding
также должно быть записано; отсутствие новой строки не равно удалению старой карточки.

expected/actual/delta для структурных правил — null; для денежных — int.
evidence_event_ids содержит PSP ID рассматриваемого плеча. Если оплаты нет совсем,
evidence пусто, а ожидаемая сумма берётся из OMS. Полный raw-lineage и snapshot_id
будущий application service добавит через run; текущий Finding не является
самодостаточным аудиторским документом.

## Синтетический пример, посчитанный по спецификации

as_of=2026-10-24T12:00:00Z; оба времени обычных событий раньше cutoff.

| Заказ | Ожидаемый capture/refund | Фактический capture/refund | Ожидаемый вывод |
| --- | --- | --- | --- |
| O1001 | RUB 10000/0 | 10000/0, C01 пришёл дважды | matched, дубль не увеличивает capture |
| O1002 | RUB 12000/0 | 11000/0 | payment_shortfall, delta=-1000 |
| O1003 | RUB 15000/3000 | 15000/1000 | refund_missing, delta=-2000 |
| O1004 | RUB 5000/0 | 0/0, deadline завтра | pending, без денежного finding |
| O1005 | RUB 5000/0 | USD capture=5000 | blocked, currency_mismatch, actual=null |
| O1999 | Заказа нет | RUB capture=7000 | orphan_payment, без баланса OMS |

C02L ещё на 1000 совершён раньше cutoff, но впервые наблюдался завтра. В старый
run он не входит. В будущем run закроет разницу O1002 при том же ожидании.
Восемь переданных строк → одна невидимая и один точный дубль → шесть фактов.
Эта таблица — ожидаемое поведение, **не фактический результат исполнения**.

## CG-103: зерно batch, факта и receipt

Batch равен canonical manifest SHA, включая normalized времена, counts и file hash.
UUID детерминирован от manifest hash, raw object — от content hash. Новый OMS
snapshot с другим effective_at допустим при одинаковых данных. Точная копия
manifest не создаёт новую партию. См. ADR-17 и алгоритм в INGESTION.

PSP canonical observed_at — минимум первого принятого пакета. Последующие равные/
поздние поступления дают receipts, более ранние отклоняют весь пакет. Receipt имеет
зерно batch/raw_row_number и собственный observed_at, не увеличивает actual суммы.
Источник observed_at не заменяет техническое received_at/published_at и входные IDs
будущего run. Полноценная historical correction и as-was persistence ещё не написаны.

## CG-104: контракт попытки

Я разделил зерно batch и attempt. Batch равен canonical envelope, attempt — отдельный
UUIDv4 на каждый вызов. Принятые факты и receipts не удваиваются из-за нового attempt.
Журнал хранит только code/category/ordinal/известное поле и относительные raw keys.
Историю ошибки не включаю в канонический источник сверки. Терминальные attempts
не меняю; исправленный вход создаёт новый manifest и новую попытку.

## CG-201: manifest расчёта v1

Я фиксирую merchant, as_of=knowledge_at, mode=as-was, knowledge_basis=published-at-marker-v1,
balance-v1, engine hash и упорядоченные source/batch/snapshot IDs с file hashes.
При missing/ambiguous OMS и отсутствии PSP отказываю; пустой PSP-пакет не заменяю
отсутствующим источником. Неизменяемый manifest и статус исполнения — разные записи.
Поздние observed факты не включаю в старый cutoff подменой времени; CG-204 введёт
отдельный режим корректировки. Границы и replay — RUN_MANIFEST.

## CG-202: result v1

Я сохраняю весь Reconciliation как canonical JSON snapshot с result_version=1,
SHA точных bytes, executor SHA и счётчиками. Null blocked сумм не заменяю нулём.
Evidence имеет зерно run/batch/raw_row и ссылается на выбранный input, receipt,
raw record и canonical PSP event. По finding event IDs нахожу все receipts,
по result OMS snapshot/order — источник ожидания. Границы — RESULTS.

## Кейсы · CG-203

Я отделяю observation presence (present/absent) от workflow (пока только open).
Ключ не меняю; сумму/evidence фиксирую в immutable revision. Повторное неизменное
наблюдение продвигает last_seen/evaluated без события. Disappearance/reappearance
дают отдельные ревизии. Я применяю целый run явно в монотонном потоке merchant;
правила canonical-as-was-v1, порядок и ограничения описал в CASES/ADR-24.
Все пять таблиц проекции и один stream head фиксирую одной транзакцией.

## Два времени · CG-204

Я расширил новый manifest до v2: mode as-was/as-known-now, visibility_version
occurred-observed-v2, request.reason/baseline_run_id. Для as-was knowledge=as_of,
для corrective report knowledge явно позже опубликованного baseline того же
merchant/as_of. PSP фильтрую occurred<=as_of и receipt observed<=knowledge;
OMS effective<=as_of и observed<=knowledge. Published marker ограничивает пакеты.
Result v2 хранит knowledge/mode/visibility, старый result v1 не обновляю.
Детальные ограничения replay/marker, кейсов и lineage описал в LATE_DATA/ADR-25.
