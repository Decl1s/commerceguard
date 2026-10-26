# CG-304: я наблюдаю свежесть и полноту источников

26.10.2026, `0.1.0.dev14`. Я добавил read-only команду source health для OMS,
PSP и выписок перечислений. Я показываю происхождение временных показателей,
последнюю публикацию и попытки, не меняю сохранённые финансовые отчёты и Case.
Это учебный операционный инструмент, а не подтверждение полноты внешнего провайдера.

## Какую проблему я решаю

Успешный pipeline ещё не означает, что данные свежие: можно повторно загрузить
вчерашний файл или принять поздний backfill. И наоборот, ошибка новой попытки
не должна стирать последнее успешное поступление. Я хочу различать эти ситуации,
показывая данные по источнику и merchant с явной границей времени.

Я разделил три вопроса. Свежесть отвечает, насколько давно источник наблюдался.
Полнота относится к последнему опубликованному пакету и его контракту. Журнал
попыток сообщает об исполнении доставки. Одним зелёным статусом я их не заменяю:
свежая выписка может быть неполной, а успешный duplicate — оставаться устаревшим.

## Мой контракт чтения

Я принимаю merchant, as_of, business_timezone, max_age_seconds и late_after_seconds.
Граница as_of задаётся RFC3339 с offset либо словом now; во втором случае я один
раз использую часы PostgreSQL. Будущий cutoff отвергаю. Порог свежести обязателен,
от1до2678400секунд; порог поздней доставки — от0до2678400. Я не закладываю скрытый
SLA: выбранный общий порог явно возвращаю в каждой строке источника.

В ответе одна строка на OMS, PSP и settlement. Отсутствующий merchant получает
три no_data строки, а не ошибку «нулевой оборот». Я также возвращаю as_of UTC,
evaluated_at — фактическое время чтения, business date/local timestamp/fold,
версию timezone базы, параметры и лимиты. Exitcode0 означает успешное чтение,
а не отсутствие устаревших источников. Ошибка аргументов/БД/предела даёт отказ.

| Измерение | Значения | Как я их понимаю |
| --- | --- | --- |
| freshness | no_data / fresh / stale | Нет видимой публикации либо возраст observed watermark внутри/вне порога |
| completeness | unknown / incomplete / declared_complete | Заявление и состав последнего опубликованного пакета |
| volume | no_data / rows_present / empty_unproven / complete_zero | Отсутствие пакета, непустой пакет, недоказанная пустота, явный полный ноль |
| last_attempt | terminal state либо started_at_boundary | Состояние известной попытки к выбранному cutoff |
| last_successful_attempt | published / duplicate | Последняя завершённая успешная попытка, независимо от более позднего отказа |

Я не добавляю общий healthy флаг: consumer должен видеть, какое измерение вызывает
вопрос. Полнота имеет completeness_scope=last_published_package, не «весь магазин
за день». Количество published_package_count включает revisions выписки и пакеты
доставки; это не число финансовых операций или уникальных перечислений.

## Какие времена я различаю

Observed watermark — максимальное observed_at среди видимых опубликованных пакетов.
Возраст считаю как as_of минус этот максимум. Last publication выбираю отдельно
по published_at и package ID. Поэтому вчерашний backfill, доставленный сегодня,
меняет последнюю публикацию, но не двигает максимум наблюдений вперёд. Duplicate
того же manifest создаёт новую успешную попытку, а не новый пакет или watermark.

Я считаю длительности целыми микросекундами в UTC. На точной границе60секунд
источник ещё fresh; через одну микросекунду — stale. Число секунд не округляю
до сравнения. Бизнес-часовой пояс влияет на календарное представление, а не на
физическую длительность часа. Это важно при переходе летнего времени.

Business watermark имеет разный смысл: effective_at для OMS, occurred_at для
видимых PSP events, period_end для выписок. Будущий business timestamp не выдаю
за достигнутую границу. Эти максимумы описывают увиденные данные, не доказывают,
что все предыдущие часы, события или перечисления поступили без пропусков.
Для PSP event_watermark совпадает с business watermark, но не с watermark доставки.

Delivery lag — published_at минус observed_at последнего пакета. Если он больше
late_after_seconds, late_delivery=true. Для PSP отдельно показываю максимальный
receipt observed_at минус occurred_at события: late_events_observed. Старое
событие, обнаруженное сегодня, может иметь большую задержку наблюдения при
быстрой доставке файла; это два разных диагноза.

Published marker иногда может оказаться раньше заявленного observed_at из-за
часов источника или будущей метки envelope. После достижения observed cutoff
я показываю publication_before_observed=true, а lag/late_delivery оставляю NULL.
Не обрезаю отрицательную длительность до правдоподобного нуля.

## Почему пустой PSP я не называю полным нулём

OMS v1/v2 допускает только manifest is_complete=true. Пустой успешно принятый
снимок с нулём строк означает complete_zero именно этого snapshot. Попытку
принять incomplete OMS parser отвергает ещё до регистрации ingest_attempt.
Если такой отказ не попал в журнал, я не выдумываю запись для source health.
Это ограничение существующей границы journaling, а не отсутствие ошибки.

У PSP v1 нет признака полноты envelope. Даже успешно принятый пустой JSONL
показывает unknown/empty_unproven. Я не делаю вывод, что провайдер не совершал
операций. Непустой PSP означает rows_present; число строк включает исходные
дубли, его нельзя использовать как количество уникальных оплат.

У settlement advice полнота явная. is_complete=false либо member_count меньше
expected_event_count даёт incomplete. Для полного пустого списка с ожидаемым
количеством0 возвращаю complete_zero. Это заявление и membership выписки:
существование каждого PSP факта и правильность четырёх сумм проверяет отдельный
settlement run. Даже declared_complete не заменяет его финансовую сверку.

Последняя публикация может оказаться старой revision, загруженной после новой.
Я честно показываю именно последний доставленный объект, не выбираю каноническую
business revision за потребителя. Source health не распределяет деньги и не
перезаписывает canonical Case stream.

## Как я читаю попытки без диагноза из будущего

Для OMS/PSP я беру только attempts со started_at<=as_of. Если finished_at ещё
не наступил к этой границе, возвращаю started_at_boundary, finished_at=NULL и
error_code=NULL, даже если сейчас терминальная ошибка уже записана в БД. Это
состояние известности на границе, не утверждение, что процесс до сих пор работает.

Last successful attempt выбираю по finished_at среди published/duplicate,
last attempt — по started_at. Последующая failed/quarantined/unknown попытка
не удаляет ссылку на прежний успех. В ответ не включаю str(driver error), raw
строки, DSN или абсолютные пути. Показываю только ID и безопасный код журнала.

У standalone settlement advice отдельного attempt journal пока нет. Поэтому
attempt_journal_supported=false и обе ссылки на попытки NULL. Я не изображаю
его отсутствие успешной доставкой и не приписываю выписке ingest_attempt PSP.
Ошибки preflight Prefect до вызова ingest также не появляются здесь автоматически.

## Что гарантирует снимок чтения

Я открываю REPEATABLE READ READ ONLY, устанавливаю UTC и проверяю schema. Все
три источника и attempts читаю одним согласованным снимком текущей БД. Фильтры
observed/published/occurred/started по as_of применяю явно; терминальные сведения
из будущего маскирую. Я не вызываю migrate, recovery, execute или Case apply.

Это всё же не восстановление исторического MVCC snapshot. Published_at — marker
до COMMIT; транзакция могла стать видимой позже метки. Я возвращаю
historical_snapshot_reconstructed=false и evaluated_at, чтобы не обещать точное
воспроизведение того, что реальный оператор видел в прошлом. Для immutable
финансового воспроизведения уже существуют сохранённые run IDs и evidence.

Я ограничиваю объём10000пакетами и10000попытками на источник,50000PSP receipts.
При превышении возвращаю SOURCE_HISTORY_LIMIT, не усечённый «здоровый» ответ.
SQL может сканировать/сортировать больше строк до LIMIT; statement timeout30секунд
ограничивает ожидание, не доказывает хорошую производительность. Нагрузку и
EXPLAIN/индексы оставляю S5. Новых таблиц, миграций и dbt views я не добавил.

## Почему я закрепил timezone данные отдельно от ОС

Я читаю ZoneInfo.from_file непосредственно из Python пакета tzdata2026.5 с
IANA2026e. Системный TZPATH не определяет результат. В analytics lock добавился
один пакет: теперь62distributions; в orchestration он уже был,107версий сохранились.
Я также объявил его прямой зависимостью health маршрута. Минимальный прежний
postgres-only lock оставил прежним; для нового CLI использую analytics lock.

Я не разбираю наивное локальное «01:30» и не угадываю fold. RFC3339 задаёт точный
instant, затем я преобразую его в явный IANA timezone. Проверил America/New_York:
два разных UTC instant дают локальные01:30 с разными offset и fold0/1.
Europe/Moscow также может показывать уже следующую календарную дату относительно
UTC. Отсутствующую/другую версию tzdata и неизвестную зону отвергаю безопасным кодом.

## Где я разместил код и как я его запускаю

| Файл | Что я в нём объясняю |
| --- | --- |
| source_health.py | Я держу типы пакета/попытки, точную арифметику времени, timezone и чистые правила отдельно от SQL |
| source_health_store.py | Я читаю bounded metadata/receipts одним snapshot и собираю три строки |
| __main__.py | Я задаю явные аргументы, не считаю возраст в CLI |
| tests/test_source_health.py | Я проверяю пороги, неизвестность, ноль, поздние данные, fold и будущий диагноз |
| scripts/freshness_scenarios.py | Я проверяю read-only сценарии внутри собственной БД check_postgres |

Для самостоятельного маршрута я обновляю analytics lock по README, готовлю свою
отдельную БД по STORAGE и принимаю synthetic inputs через существующие команды.
Затем из корня checkout запускаю:

```bash
.venv/bin/python -m commerceguard source health \
  --merchant M01 --as-of now --business-timezone Europe/Moscow \
  --max-age-seconds 86400 --late-after-seconds 3600
```

--merchant задаёт область данных; --as-of — момент оценки либо now по часам БД.
--business-timezone выбирает IANA базу, --max-age-seconds задаёт учебный общий
порог свежести, --late-after-seconds — порог задержек. --dsn-env по умолчанию
COMMERCEGUARD_DATABASE_URL: значение подключения храню снаружи, в Git не записываю.
86400/3600 — параметры примера, не обещанный SLA реального магазина.

Идентификатор package_id означает batch_id для OMS/PSP и advice_id для settlement.
Content SHA у первых двух относится к raw data файлу, у выписки — к canonical
advice. Полную финансовую lineage/evidence я читаю существующими result командами;
health не выводит raw содержимое. Я могу повторить ту же оценку с другим порогом,
не создавая нового business report и не меняя baseline.

## Мои проверки и пять упражнений

Я выполнил53unit tests в обоих окружениях. Сквозной PostgreSQL runner подтвердил
read-only counts, late backfill, failed-after-success, duplicate-still-stale,
скрытие будущего terminal, OMS complete_zero/PSP empty_unproven, incomplete advice,
missing merchant и CLI round-trip. Старые run/settlement результаты сохранились;
dbt9models/19tests дал PASS28. В первом unit я исправил неверное ожидание строки
UTC без шести нулевых микросекунд; контракт canonical_time не менял. Полная
матрица и пробелы — VALIDATION. CI/Windows/power loss/concurrency не проверял.

1. Я задаю observed на60секунд раньше as_of и порог60. Ожидаю fresh, затем
   сдвигаю as_of на1микросекунду и получаю stale. Округление до секунд сломало бы ответ.
2. Я повторно публикую старый PSP файл. Ожидаю новую duplicate attempt, прежний
   observed watermark и stale при прежнем пороге. Успех доставки не омолаживает данные.
3. Я сравниваю пустой полный OMS и пустой PSP. Ожидаю complete_zero у OMS,
   unknown/empty_unproven у PSP; отсутствие пакета даёт no_data, не эти два случая.
4. Я читаю cutoff между started_at и finished_at позднее завершённой попытки.
   Ожидаю started_at_boundary и отсутствие будущего error_code; новый cutoff
   показывает диагноз, сохраняя прежнюю successful attempt.
5. Я меняю Europe/Moscow на America/New_York при одном UTC instant. Ожидаю другое
   local date/offset при тех же UTC age и freshness. Объясняю, почему timezone
   нельзя использовать для арифметики физической длительности.

Для собеседования я объясняю watermark как наблюдаемый максимум, а не гарантию
полноты; различие source freshness и successful delivery; null против knownzero;
почему latest package не означает canonical revision; что даёт repeatable read
и почему published marker не восстанавливает исторический COMMIT snapshot.
