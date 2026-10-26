# Журнал архитектурных решений

Формат ADR: контекст → решение → цена → когда пересматривать.
Принято 24.10.2026 для текущего этапа; будущие компоненты не объявляются реализованными.

## ADR-01: модульная ИС с одним PostgreSQL

Нужны согласованные факты, кейсы и аудит, но нагрузка ещё не подтверждена.
Выбираю один сервис с предметными/application/adapter слоями и одну БД.
PostgreSQL вместо SQLite нужен для нескольких операторов и транзакционной модели
приёма/расчёта; вместо отдельного lakehouse — меньше движущихся частей.
Цена: один узел и дисциплина разделения схем. Пересмотр — при измеренной конкуренции,
объёме истории или независимых командах; появление Kafka не самоцель.

## ADR-02: Python 3.12 и предметное ядро без внешних зависимостей

Python связывает загрузку, правила, оркестрацию и API. Первые правила — dataclasses
и чистые функции; их не нужно переносить из ORM/FastAPI, когда добавится другой адаптер.
Цена: runtime-инварианты пишутся явно, dataclasses сами не обеспечивают validation.
Пересмотр — на границе внешнего API можно добавить Pydantic, сохранив независимость ядра.

## ADR-03: два денежных плеча и целые minor units

Одинаковая net-сумма не доказывает совпадение оплат и возвратов. Сверяю capture
и refund отдельно; знак delta всегда actual−expected. Суммы int, не float;
нет скрытого допуска и конвертации валют. Цена: больше объяснений в UI,
ограниченный список валют v1. Для JPY/KWD нужны метаданные exponent и версия контракта,
а не предположение «во всех валютах копейки».

## ADR-04: два времени, immutable snapshot и явный cutoff

Исторический отчёт должен отвечать на вопрос «что тогда было известно».
occurrence не заменяет observed_at; OMS также требует effective/observed времена.
Run хранит cutoff и входные immutable IDs. Цена: история занимает место, backfill
имеет два режима. Пересмотр — потребность полноценного temporal API, но не удаление
старых данных ради удобного UPDATE. Начальный kernel получает уже выбранный OMS-снимок.

## ADR-05: повтор — семантическая идентичность, конфликт — отказ

Источник может переслать запись с новым транспортным временем. fingerprint
не включает observed_at, но включает ссылку, сумму, kind, currency и occurred_at.
Одинаковый business event дедуплицируется; другой смысл под старым ID не исправляется
молча. Цена: корректировки потребуют отдельного контракта. Второй PSP потребует
provider_id, иначе возможна коллизия пространств имён.

## ADR-06: файл и БД не образуют одну транзакцию

Raw нужен для происхождения и восстановления, но файловая система не участвует
в PostgreSQL COMMIT. Пишу immutable файл, затем manifest; учитываем orphan raw.
Core публикуется отдельной атомарной транзакцией после staging. Цена: recovery
должен сопоставлять два носителя. Пересмотр — объектное хранилище с тем же manifest,
не недостоверное обещание exactly-once между всеми сервисами.

## ADR-07: Finding и Case — разные сущности

Finding — вычисление на один run. Case — работа людей во времени. Их объединение
удалило бы комментарии при новом расчёте. Стабильный case_key не включает сумму;
новые значения — revisions, человеческие действия — append-only events.
Цена: приходится явно описать resolved/reopen и канонический run. Изменение смысла
кода правила требует нового кода/миграции; ruleset_version хранится в run.

## ADR-08: dbt и Prefect после появления корректного core

dbt удобен для SQL-моделей/lineage, Prefect — для параметров и повтора шагов.
Они не должны стать местом произвольной перезаписи кейсов и бизнес-аудита.
Ввожу их в S3, когда шаги уже имеют контракты. Цена: сначала ручной CLI,
затем orchestration adapter. Успех Prefect не равен published в доменной БД.

## ADR-09: серверный HTML для рабочего места

Нужны фильтры, карточка и формы, а не сложное клиентское приложение.
FastAPI/Jinja2 сохраняют один основной язык и простую передачу модели.
Цена: меньше интерактивности, обязательные сессии/CSRF/escaping и role checks
нельзя «оставить фронтенду». React/SPA добавляется только при конкретном UX-требовании.

## ADR-10: последовательные срезы, исполнение запрещено

Я выбрал последовательную разработку небольшими срезами без запуска и тестирования.
Не запускаю код/линтер/CI; документы указывают unverified. Не моделирую результат
инструментом и не называем его «не тестом». Цена: нет доказанной работоспособности,
не выдаю stable release или production readiness. Пересмотр только по новому
моему явному решению о смене режима работы этого проекта.

## ADR-11: Scrum-цели и Kanban-поток

Проект большой для одного захода. Цель спринта удерживает бизнес-результат;
WIP=1 удерживает последовательность. Документы/истории публикуются в Git,
без фиктивных сотрудников и встреч. Цена: velocity пока неизвестна, прогноз
спринтов качественный. Решения фиксирую в ADR. Если появляется новый факт, добавляю отдельную запись
с причиной изменения.

## ADR-12: разработка в публичном репозитории, без личных данных

Флагман должен быть виден и объясним, а не возникнуть финальным архивом без истории.
Публикую небольшие коммиты и Draft PR, только manifest исходников. Текст создаётся
здесь, данные вымышленные; не нужны реальные API-ключи, файлы или контакты.
Цена: ранний читатель видит неполный проект — это явно описано в README.
История вклада датируется фактической работой; активность не подделывается.

## ADR-13: одна физическая схема и явная идентичность хранилища

24.10.2026, CG-101. Слои ingest/core/ops/mart остаются логическими, но в первом
storage-срезе таблицы имеют префиксы внутри одной схемы commerceguard. Это уточняет
первоначальный план нескольких схем и упрощает проверку владения/отзыв PUBLIC ACL.
Мигратор требует отдельную БД commerceguard, PostgreSQL 16, owner текущей роли,
маркер схемы и app_identity v1. Чужую схему не присваивает. Цена: фиксированное
имя БД и работа мигратора под владельцем; раздельные runtime-роли появятся позже.
Это защита от случайного смешивания приложений, не от доверенного DBA.

## ADR-14: небольшой собственный migration runner для одного начального DDL

24.10.2026. Нужны checksum-история, одна транзакция и отказ при неизвестной схеме.
Использую Psycopg 3.3.6, пакетные SQL, transaction advisory lock, отдельные bootstrap
и монотонные файлы 0001..N. Весь pending-набор и журнал получают один COMMIT.
Нет down/reset и SQL из произвольного файла. Цена: свой код не заменяет зрелый
framework миграций и пока не проверен. Перед параллельными релизными линиями или
сложными online migrations нужен пересмотр в пользу специализированного инструмента.
Driver — отдельный опциональный набор; demo остаётся без сторонних зависимостей.

## ADR-15: фиксированный временный снимок и полный проход

24.10.2026, CG-102. Hash файла и последующий повторный open могли относиться
к разным байтам после внешнего изменения. Вход копируется блоками в TemporaryFile
с проверкой размера/hash, затем разбирается эта же копия. Цена — до 100000000 байт
временного диска и второй проход чтения. Это не постоянный raw, не backup и
не атомарность файловой системы/PostgreSQL. Нормальный выход из open_input
с недочитанным потоком запрещён: будущая публикация не должна принять prefix.
Память ключей ограничена row_count, но растёт с уникальными ID; обещания O(1) нет.

## ADR-16: фиксированные форматы и отдельный hash смысла

24.10.2026. Один пакет — один source/merchant. OMS имеет точный CSV header,
PSP — JSONL с точным набором полей, без duplicate keys, дробей и non-finite.
Пути передаются отдельно, не из manifest. Semantic hash v1 — компактный JSON array
с фиксированным порядком и UTC microseconds; transport layout и PSP observed_at
не входят. Raw/file hashes остаются отдельными идентификаторами доказательств.
Цена — строгий контракт отвергает «почти подходящие» выгрузки, для другого формата
понадобится адаптер/новая версия. Hash не доказывает подлинность или полноту источника.
Глобальный replay/temporal dedup относительно опубликованного core решает CG-103.

## ADR-17: identity всего envelope и raw без overwrite

24.10.2026, CG-103. Одинаковые строки OMS в разные effective_at — разные полные
снимки. Поэтому batch identity — SHA-256 canonical manifest, включая времена;
content hash остаётся identity точных байтов. Manifest сохраняется компактным
sorted ASCII JSON с UTC microseconds и одним LF; layout исходного manifest не нужен.
UUIDv5 даёт детерминированные batch/snapshot ссылки с разными префиксами, без MAC.
0002 заменяет прежнюю уникальность content hash, не меняя checksum 0001.
Непустые legacy batches блокируют миграцию: неизвестный envelope не выдумывается.

Raw устанавливается временным файлом и эксклюзивным hard link на том же filesystem;
existing объект полностью сверяется, не перезаписывается. Цена: нужен user-owned
root с маркером и поддержкой hard links; нет переносимой гарантии power-loss/WORM.
Manifest и данные могут остаться orphan без БД. Пересмотр — иной storage adapter
или согласованный legacy migration plan, а не скрытый DELETE.

## ADR-18: temporal conflict вместо изменения известного прошлого

24.10.2026. При первом приёме PSP минимальный observed_at среди равных записей
пакета становится canonical. В следующих пакетах равный/поздний observed_at создаёт
receipt к прежнему факту. Более ранний — TEMPORAL_CONFLICT всей партии, иной смысл —
PSP_CONFLICT. Факт не UPDATE. Каждая успешно принятая raw PSP-строка получает receipt;
replay целого пакета не дублирует даже receipts. Цена: историческая коррекция требует
нового контракта. Это уточняет «earliest observed» ADR-04/05: минимум первого
принятого пакета, без автоматического сдвига опубликованного факта назад.
S2 обязан различать source observed_at и техническое знание: фиксировать batch IDs,
cutoff и происхождение run. Один source timestamp не доказывает as-was.

## ADR-19: один COPY и одна транзакция публикации

24.10.2026. TEMP stage содержит raw и typed поля: один write_row, затем разрешение
повторов и INSERT SELECT. Нет промежуточного COMMIT, нет OFFSET-страниц с частичной
публикацией. received/staged — внутри transaction; published виден после COMMIT.
Shared migration lock и exclusive merchant try-lock сериализуют сотрудничающих
писателей. READ COMMITTED видит завершённого предшественника после lock.
Потеря ответа COMMIT — неизвестный исход; повтор с тем же manifest разрешён.
Цена: весь пакет занимает одну транзакцию, TEMP/индексы/WAL и память parser; предел
файла не означает доказанную скорость. Нет ON CONFLICT DO NOTHING, скрывающего иной
payload при записи в обход lock. При больших измеренных объёмах пересмотреть
stage-процесс, сохранив атомарную границу видимости snapshot. Исполнение запрещено.

## ADR-20: независимые попытки и карантин целого пакета

24.10.2026, CG-104. Я хочу сохранять диагноз после отката COPY, поэтому ввожу
отдельный ingest_attempt: started отдельным COMMIT, success в транзакции core,
rejection отдельным соединением и только из started. Терминальный trigger не даёт
переписать успех после потери ответа COMMIT. DatabaseError консервативно даёт unknown;
ошибку записи журнала показываю явно. Карантиню весь пакет без частичного core,
не создавая фиктивную raw record ради FK старой ingest_quarantine.

Цена: preflight до подтверждённого raw/manifest может остаться без attempt;
БД недоступна — диагноз best effort, raw может быть orphan. Ограниченный scan не
доказывает полного отсутствия orphan и не читает полный data hash. Recover по
manifest SHA сверяет все байты и повторяет тот же протокол с новой попыткой.
Cleanup/retention и offline audit spool оставляю эксплуатации. Исправление семантики
источника не маскирую под recovery. Код, миграцию и concurrency пока не запускал.

## ADR-21: отдельные синтетические файлы и metadata status

24.10.2026, CG-105. Я хочу показать полный путь приёма без настоящей выгрузки,
поэтому формирую фиксированные CSV/JSONL и manifest стандартной библиотекой.
Основной и поздний PSP разделяю по моменту наблюдения: это сохраняет ясный набор
входов исторического run. Не заменяю output-каталог; при частичном сбое не удаляю
чужие файлы. Ошибочные сценарии имеют правильный file hash, чтобы достигать parser/
semantic/temporal границы, а не останавливаться на транспортной сверке SHA.
Status читает явные metadata columns одним read-only snapshot и ограничивает
историю. Цена: ручная подготовка PostgreSQL, нет UI и неограниченной пагинации;
сама генерация не является проверкой работоспособности. Код пока не запускал.

## ADR-22: immutable manifest отдельно от выполнения

24.10.2026, CG-201. Я фиксирую input IDs/hashes, cutoff, ruleset и source fingerprint
одним COMMIT. Точный повтор canonical текста даёт тот же run ID. Manifest не должен
изменяться при retry расчёта, поэтому lifecycle started/published/failed выношу в
следующий CG-202, а не меняю immutable входы. Это уточняет первоначальный CG-201
backlog, не означает вычисленный результат. Один OMS и явный PSP, неоднозначный
последний OMS — отказ; список PSP ограничен, не обрезается молча.

Для выбора под cooperative merchant lock я использую READ COMMITTED, чтобы видеть
завершённого предшественника после lock. Для повторного расчёта читаю уже сохранённые
IDs. Пока поддерживаю только as-was v1, as-known-now/раздельные временные оси — CG-204.
Цена: published_at — marker перед COMMIT, а не точная MVCC-видимость в прошлую секунду;
ретроспективный выбор по timestamp не выдаю за точный replay прошлого отчёта.
Source fingerprint включает комментарии Python; Markdown-правки ID не меняют.
Наличие PSP-пакета не доказывает provider watermark/полноту периода. Всё unverified.

## ADR-23: bounded immutable JSON result и relational provenance

24.10.2026, CG-202. Я сохраняю полный snapshot kernel как canonical text/JSONB,
не дублируя каждую сумму второй изменяемой таблицей. Relational evidence связывает
receipt/raw с конкретными inputs run. Материализацию SQL-проекций оставляю S3.
Started attempt фиксирую отдельно; чтение input — короткий snapshot; Python считает
вне idle transaction; final result/evidence/success — один COMMIT под run lock.
Повтор сравнивает result SHA, иной результат под прежним run ID — отказ.

Цена: v1 ограничен 10000 orders, 50000 receipts и 16 MiB результата; target PRD
не называю достигнутым. Viewers читают bounded JSON целиком и ограничивают stdout,
а не дают неограниченную SQL-пагинацию. Source fingerprint предполагает trusted
checkout без редактирования во время процесса. Future case — отдельная сущность,
публикация result не закрывает его автоматически. Всё пока без исполнения.

## ADR-24: явный канонический поток и presence отдельно от workflow

25.10.2026. Я не продвигаю Case автоматически по завершению run: медленный старый
расчёт иначе мог бы затереть новый. В canonical-as-was-v1 выбираю строго растущий
as_of на merchant, неубывающий knowledge, balance-v1/as-was. Уже применённый run
всегда noop; другой run с равной границей — отказ, а не выбор по UUID. Исторические
отчёты остаются доступными. Исправления одного cutoff выделяю в CG-204.

Я храню application ledger + stream, mutable head и immutable revision/event одним
COMMIT. Case identity защищаю trigger, ссылку head → revision/presence откладываю
до COMMIT из-за circular insert. Fingerprint проектора записываю в application.
Повторная та же finding не плодит revisions; last_seen/evaluated объясняют наблюдение.
Absence — наблюдение, не человеческое resolved. Workflow пока только open, S4 отдельно.
Цена: поток до 10000 исторических карточек, finding до 64 KiB, явное продвижение,
нет case-attempt failure journal и стабильного export через несколько страниц.
Срез не запускал, корректность конкуренции и FK не подтверждал.

## ADR-25: явная граница знания и report-only исторические корректировки

25.10.2026. Я отделил business cutoff от knowledge cutoff. As-was сохраняет равные
границы; as-known-now требует явного knowledge и baseline опубликованного отчёта
того же merchant/as_of с меньшим знанием. В manifest v2 включаю reason enum,
baseline UUID и visibility_version; intent входит в canonical run identity.
Не подменяю timestamps позднего PSP. OMS выбираю по effective/knowledge, PSP
по knowledge пакета, kernel по occurred/receipt observed. Result v2 записывает оба
времени. Published_at по-прежнему marker до COMMIT, а не реконструкция MVCC истории.

Я добавил read-only changes, сравнение engine SHA и впервые видимые относительно
baseline event/receipt refs. Не приписываю всю разницу late data при смене движка.
Исторический corrective report не продвигает Case; canonical-as-was-v1 не меняю
без отдельной политики. Для текущего наблюдения беру более новый as-was cutoff.
Цена: baseline обязателен, нет свободного текста причин, historical executors не
поставляются автоматически, прежний kernel fingerprint не совпадёт с новым checkout.
Старые сохранённые results читаю без переписывания. Миграция 0007 расширяет только
схему/constraints, 0001…0006 побайтно не меняю. SQL и исходники не запускал.

## ADR-26: два срока, версионированный результат и явный переход кейсов

25.10.2026. Я выбрал OMS v2 с обязательными capture_due_at/refund_due_at.
Общий срок скрыл бы просроченную оплату при позднем одобрении возврата. В v1
оставляю settle_after и точную semantic serialization; адаптирую его в памяти
к двум одинаковым срокам. В v2 общий storage settle_after=max остаётся только
совместимым сводным полем, kernel использует сроки каждого плеча.

Я ввёл balance-v2 и manifest/result v3 вместо молчаливой смены balance-v1.
Переношу input contract_version через membership/core FK; старые membership
версии не выдумываю backfill. Состояние каждого плеча считаю независимо, общее
discrepancy важнее pending. Excess, как shortfall, оцениваю при наступлении срока;
новой политики немедленного excess здесь нет. Старые results остаются immutable,
show/result читают их без исполнения. Новым executor не обещаю выполнить старый
manifest с другим engine hash; старые реализации/совместимые схемы нужны отдельно.

Я добавил явный v1→v2 Case upgrade с ожидаемым canonical predecessor под lock.
Policy/source сохраняю в application ledger вместе с проекцией. Case key и codes
не меняю; смена срока без смены finding не требует новой ревизии. Corrections
остаются report-only. Обратную миграцию правил не поддерживаю; флаг не заменяет
человеческие права и аудит S4. Run changes отдельно отмечает смену ruleset/deadline.

Цена: больше версий и полей, nullable legacy columns, ручной переход существующего
stream и ограниченное историческое execute. В 0008 я использую constant default=1
и nullable timestamps без UPDATE старых записей. Официальный раздел
[PostgreSQL 16 ALTER TABLE](https://www.postgresql.org/docs/16/ddl-alter.html)
объясняет constant default и проверки constraints; я не вывожу из него гарантию
совместимости написанного DDL. SQL, имена checks, parser, сериализацию и concurrency
не запускал. Новых зависимостей не добавил; подробности и задания — DEADLINES.

## ADR-27: я включил проверки и фиксирую область доказательства

25.10.2026. Я снял прежний запрет исполнения отдельным решением. Начал с денежных
инвариантов/parser/raw, затем создал временный PostgreSQL 16 без TCP и прошёл
миграции/ingest/run/case/dbt. Не подключаюсь к пользовательской БД и не поднимаю
постоянную службу. Runner останавливает свой сервер в finally и удаляет кластер.
Я исправил реальный raw keyword-only TypeError и закрепил регрессию.
Цена: базовый green path не подтверждает concurrency/power loss/Windows/legacy
upgrade; эти пробелы сохраняю явно, старые PR не принимаю автоматически.

## ADR-28: отдельное зерно и pre-aggregation в dbt v1

25.10.2026. Я выбрал dbt Core 1.12.6 + dbt-postgres 1.11.0 в локальной .venv.
Это известный SQL-first v1 контракт с отдельным adapter; новую v2 distribution
не смешиваю в том же окружении. По текущим официальным материалам v2 доступна,
поэтому не называю выбранную ветку самым новым движком. Версии v1 я закрепил,
их совместимость подтвердил реальным build. Зависимости/hashes — analytics lock.

Я выбрал 8 views в отдельной схеме, чтобы не вводить расписание refresh и второй
mutable финансовый snapshot. Читаю только published result известных версий;
as-was и corrective reports различаю по run, latest не выбираю. Events беру по
точному evidence membership, occurred/observed visibility и дедуплицирую receipt
на run/event. Capture/refund агрегирую отдельно до JOIN: M×N иначе размножит деньги.
Blocked остаётся NULL, finding-only currency не теряю в FULL JOIN. Legacy result
без per-leg context не дополняю выдуманными сроками; текущий integration проверяет v3.

Цена: views пересчитывают SQL при чтении, общий latest/canonical run не выбран
за потребителя, known_actual — частичный OMS-scope итог при blocked/orphan, не
оборот провайдера. Нагрузку/индексы пока не измерял, права mart hardened в S4/S5.
13 data tests проверяют grain/null/completeness/независимую сумму, 15 unit tests
и integration проверяют основной pipeline. Settlement, Prefect и catalog отдельны.

## ADR-29: явный settlement membership и независимый batch тариф

26.10.2026. Я отделил доставку PSP файла от business settlement. Принимаю advice v1
с merchant/settlement/revision, точными event_ids, currency/period/completeness и
четырьмя reported суммами. Canonical identity отличаю от raw byte identity.
Assignment резервирует event одному settlement_id; новая revision не переносит
событие в другой пакет. Missing fact допустим и даёт unknown, поэтому FK на PSP
факт у membership нет. Период/валюта семейства фиксированы, latest не выбираю.
Цена: без отдельной политики отмены нельзя освободить ошибочно назначенное событие.

Я считаю fee независимо по обязательному fee_bps: одна half-up операция на gross,
refund не возвращает fee, net signed. Unknown означает NULL всех expected/delta,
complete empty — известные нули. Тариф/visibility/engine/cutoff входят в request.
Immutable report сохраняет advice/raw/receipt lineage, late fact требует нового
cutoff; exact replay возвращает старый payload. Не распределяю fee по OMS заказам.

Я выбираю receipt через LEFT JOIN LATERAL, иначе INNER JOIN скрыл бы missing member,
а JOIN всех receipts размножил бы деньги. Основы: [LATERAL](https://www.postgresql.org/docs/16/queries-table-expressions.html#QUERIES-LATERAL)
и [ON CONFLICT](https://www.postgresql.org/docs/16/sql-insert.html). Business policy
задаю сам; документация PostgreSQL не доказывает корректность финансового правила.
Проверил schema8→9, 11reports, old SHA, 27unit и dbt19tests. Не подтвердил аварийный
COMMIT/concurrency/Windows. Standalone advice не входит в ingest scan/recover и
не имеет отдельного attempt journal. Подробности и пять упражнений — SETTLEMENT.

## ADR-30: отдельный лексический integer лимит для агрегата

26.10.2026. При разработке я заметил, что 10000 событий по 10^12 дают 10^16 —
17 цифр, тогда как общий JSON parser ограничивал token16. Я добавил явный аргумент
max_integer_digits с default16 для прежних OMS/PSP и18 только для settlement.
Предметные пределы всё равно проверяю после parsing, floats/bools не разрешаю.
Регрессия подтверждает aggregate17 и сохранённый отказ старого default16.
Это осознанное расширение контракта, не снятие всех ограничений JSON parser.

## ADR-31: я изолирую локальную оркестрацию и повторяю только известные transient

26.10.2026. Я выбрал Prefect3.8.8 в отдельной .venv-orchestration и analytics
Python с прежним dbt v1. Последовательные tasks вызывают существующие сервисы;
финансовую формулу/DB identity не переношу в flow. Prefect cache/persist_result
отключаю. Входы полностью проверяю и фиксирую до ingest, retry читает snapshot.
Два publish не составляют общей транзакции: partial OMS success сохраняю явно.

Now получаю один раз после ingest по часам БД; prepare обязан включить оба
ожидаемых batch IDs. Resume получает immutable run_id, не выбирает latest.
Task retries2 (всего3, delays1/3s) только для MERCHANT_BUSY/SCHEMA_BUSY/RUN_BUSY;
flow retries0. Unknown COMMIT/contract/dbt failure автоматически не повторяю.
Текущий transient allowlist узкий; это не полная классификация ошибок всей инфраструктуры.

До импорта Prefect я изолирую home/profiles/cwd/PREFECT_* в дочернем процессе,
выключаю telemetry и API log sink, проверяю отсутствие внешнего URL/key. Backend
временный loopback, stop в finally. Его SQLite удаляю, PostgreSQL остаётся source
of truth. Цена: нет durable pipeline journal, history UI/schedule/deployment,
после сбоя сохраняю JSON сводку отдельно; SIGKILL/power loss не проверял.

Dbт вызываю отдельным analytics процессом по тому же явному DSN. Поддерживаемый
connection subset проверяю до ingest, password через secret env_var. Opaque service/
multi-host/options не теряю молча. Build требует pass всех nodes, общий atomic
swap views не обещаю. Основы: [Prefect retries](https://docs.prefect.io/v3/how-to-guides/workflows/retries),
[task runners](https://docs.prefect.io/v3/concepts/task-runners), [settings](https://docs.prefect.io/v3/api-ref/settings-ref),
[dbt programmatic invocations](https://docs.getdbt.com/reference/programmatic-invocations).
Проверки normal/replay/partial failure/retry limit/marts failure/CLI resume прошли
на Linux/PG16.15,38unit в обоих окружениях. Карта и упражнения — ORCHESTRATION.

## ADR-32: я закрепил FastAPI совместимость внутреннего сервера Prefect

26.10.2026. Первый resolver выбрал FastAPI0.162.0, но импорт API Prefect упал на
Body(...,min_items=1). [Официальные release notes](https://fastapi.tiangolo.com/release-notes/#01550)
описывают удаление **extra в0.155. Я закрепил0.154.0 и пересоздал lock с hashes.
Я не исправляю установленный vendor source и не ослабляю приложение для green test.
Установка107packages и uv pip check теперь успешны; реальный ephemeral flow подтвердил
совместимость. Новую FastAPI не называю безопасно совместимой без повторной проверки.
Это внутренний HTTP стек оркестратора, бизнес-API CommerceGuard пока не написан.

## ADR-33: я разделил observed watermark, completeness и delivery attempts

26.10.2026. Source health читает OMS/PSP/settlement, явный as_of и общие пороги.
Свежесть считаю по MAX(observed_at) видимых published packages, не по started или
finished попытки. Последняя публикация выбирается отдельно. Backfill/duplicate
не должны омолаживать старые данные. Max business/event timestamp не доказывает
полное покрытие источника до этой границы.

Completeness относится к last_published_package: OMS только complete, PSPv1 unknown,
settlement false либо member_count<expected_count incomplete. Empty PSP не считаю
нулевым оборотом. Last attempt и last successful attempt выбираю отдельно; terminal
из будущего cutoff маскирую как started_at_boundary без error code. У settlement
нет attempt journal, flag unsupported явно. Pre-registration failures отсутствуют
в ingest journal, я не создаю фиктивные попытки при чтении.

Я использую REPEATABLE READ READ ONLY и bounds10000packages/10000attempts на source,
50000receipts. При превышении отказываю, не строю частичный healthy ответ. Это
текущий согласованный snapshot с marker фильтрами, не реконструкция прошлой MVCC
видимости: published_at не commit timestamp. Возвращаю evaluated_at и этот предел.
Baseline/финансовые reports/Case не изменяю. Новых dbt views не добавил, потому что
операционный запрос имеет явные параметры и другой смысл, чем сохранённые marts.
Цена: нет исторического health journal, общий threshold вместо source SLA справочника,
нет анализа пропущенных окон/внешних гарантированных high watermarks. Нагрузку не мерил.
Основа: [PostgreSQL16 Repeatable Read](https://www.postgresql.org/docs/16/transaction-iso.html).

## ADR-34: я читаю timezone из закреплённого wheel и сравниваю UTC microseconds

26.10.2026. Я выбрал tzdata2026.5/IANA2026e и ZoneInfo.from_file из package resources.
В analytics добавился1пакет, прежние pins сохранил; в orchestration версия уже была.
Системный TZPATH не меняет выбор базы. [Python zoneinfo](https://docs.python.org/3.12/library/zoneinfo.html)
описывает источники данных/fold; [tzdata](https://pypi.org/project/tzdata/2026.5/) —
поставку IANA базы. Я сам фиксирую строгий version contract и явные параметры.

Наивное локальное время не разбираю: RFC3339 определяет UTC instant, затем вывожу
local date/offset/fold. Возраст считаю целыми UTC microseconds; ровно threshold —
fresh, плюс1microsecond — stale. Отрицательный publication-observed lag отмечаю
аномалией с NULL lag, не обрезаю до0. Проверил Moscow next date, New_York fold0/1,
threshold, old duplicate/backfill, future diagnosis и обе CLI/DB цепочки. Windows,
реальные конкурентные writers и historical MVCC replay не подтверждал.
