# Как я обосновываю индексы и ограничения

Я сохранил настоящий EXPLAIN ANALYZE в evidence/query-plan.json. Сценарий публикует
полный OMS snapshot2000заказов PERF1 и явный пустой PSP пакет, рассчитывает и
применяет2000расхождений, выполняет ANALYZE и читает страницу50строк по case_key
после1000-йкарточки. Я не отключаю Seq Scan и не заставляю планировщик выбирать
нужное мне имя индекса. Первый fixture без PSP закономерно отказал: отсутствие
источника не равно известному нулю; я добавил явный пустой manifest.

На временном PostgreSQL16.15 я получил Limit→Nested Loop→Index Scan/Memoize→Index
Only Scan. Планировщик выбрал ops_case_pkey и индекс application identity, а не
новый queue composite index: на этой выборке это допустимый результат. Planning
0.211мс, execution0.056мс, actual rows50. Данные помещаются в cache, это один
синтетический прогон, не SLO и не доказательство такой скорости на любой БД.

Миграция15 добавляет merchant/source/time indexes для published batches и last
attempt/success, settlement publication и last close audit. Существующий queue
индекс merchant/status/currency/key соответствует реальным filters. OFFSET не
использую для рабочего списка; количество отсканированных строк всё равно зависит
от селективности filters и age/application JOIN. Индексы стоят места и замедляют
INSERT, поэтому не добавляю индекс на каждый столбец без сценария.

Я также убрал рост Python memory health по всей истории. PostgreSQL считает полный
count и возвращает максимум3настоящих package rows (latest/max observed/max business),
2attempt rows (last/last success) и event MAX/lag aggregate. Деньги не пересчитываю.
Pure evaluator сохранил прежний смысл, published count беру по полному snapshot.
Health view_version теперь source-health-v2: limits честно описывают representative
rows/SQL timeout, прежний отказ после10000packages/50000историческихreceipts больше
не используется. Все прежние freshness/completeness/future-diagnosis сценарии прошли.

В контейнерной проверке я получил40успешныхHTTPзапросов с4клиентами за0.393с. Это
маленький smoke test, без percentile/soak/пикового трафика. Первую версию ограничиваю
исходными безопасными bounds:10000orders/50000receipts и16MiB result наrun,
10000историческихCase наmerchant,10000строкCSV,31деньbackfill. Превышение означает
явный отказ, а не тихую потерю строк. Capacity и retention планирую до реальной
загрузки: произвольный многолетний поток в эти лимиты не обещаю.

Упражнение: изменить число PERF1заказов и фильтр валюты, снять новый EXPLAIN, сравнить
actual rows/buffers и выбор индексов. Я не сравниваю только одну цифру execution_ms
без размера данных/cache/версии PostgreSQL и не выдаю синтетику за коммерческий benchmark.
