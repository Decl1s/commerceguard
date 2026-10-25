# Продолжение CommerceGuard

Я веду отдельный флагманский учебный проект с 24.10.2026. Актуальные решения
из разговора имеют приоритет. Ежедневные мини-проекты и их автоматизация отдельно.

## Мои обязательные границы

- Все объяснения, комментарии, документацию и PR я пишу по-русски от первого лица
  единственного числа. Не использую «по запросу пользователя» и пересказ поручений.
  Технические определения, поля и роли продукта называю прямо. Не выдумываю
  коммерческий опыт, клиента, результаты запусков или внешнюю приёмку.
- С 25.10.2026 я включил исполнение и проверки отдельным явным решением.
  Проверяю приложение, parser/generator, SQL/миграции и витрины на синтетических
  данных в локальном окружении. Временный PostgreSQL запускаю без TCP, затем
  останавливаю. Не использую чужие БД и постоянные сервисы. CI добавляю явно.
- Результаты прежних срезов остаются исторически unverified. Новые подтверждения
  фиксирую по фактически выполненным сценариям в VALIDATION; Draft PR сам по себе
  не означает приёмку и производственный релиз.
- Я беру одну активную историю, публикую ограниченный срез и лишь затем следующую.
  В длительном продолжении могу завершить несколько последовательных историй.
  Не принимать/сливать PR автоматически, не делать stable release unverified кода.
- Источники sources/ read-only. Чужие приложения и пользовательские правки сохраняю.
- У commerceguard свой Git: до add сравниваю root с каталогом приложения. Добавляю
  только явный PUBLIC_FILES.txt, никогда не использую родительский Git. Ветки codex/.
- Публикую только исходники: без workspace data/raw/БД/DSN/секретов/контактов,
  абсолютных приватных путей и посторонних файлов. Удалённая API-история отличается
  от локальной; сохраняю фактический remote parent, не делаю force push.

## Что я читаю перед продолжением

README, START_HERE, docs/PROJECT_MAP, docs/PROGRESS, docs/KANBAN, конец WORKLOG,
docs/sprints/S3, MARTS, DATA_CONTRACTS и соответствующие ADR в DECISIONS.
PROGRESS — постоянная таблица этапов; BACKLOG — критерии; WORKLOG — факты.
Исторические разделы ранних контрактов сохраняю, актуальные расширения описаны
в CASES/LATE_DATA/DEADLINES и ADR-24…26. Не считать planned Prefect/HTTP написанными; dbt уже написан в CG-301.

## Моя актуальная точка

25.10.2026, версия 0.1.0.dev11, schema8/20 tables + 8 dbt views.
Я написал S0 (2), S1 (5), S2 (5), S3/CG-301 (1) = 13 из 30 историй; остаются17.
Включил проверки: unit15 OK, PostgreSQL16.15 migrations1…8 + integration, dbt8models/
13data tests PASS21. Это основной Linux путь, не полная приёмка прежних срезов.
Текущая ветка codex/s3-cg301-verified-marts поверх CG-205 #24; PR добавлю по факту.
Следующий Ready — CG-302: settlement/commission на уровне PSP batch, completeness,
currency и явный cutoff, без произвольного распределения fee на OMS заказы.
Prefect/HTTP/UI/эксплуатация ещё не написаны. Сначала публикую CG-301, затем CG-302.
Ветку следующего среза строю от свежего remote head, локальная и API история разные.
Точную матрицу пробелов читаю в VALIDATION. CI отсутствует, локальный успех не CI.
Главная ветка — навигация, Draft PR не сливаю автоматически.

## Какие контракты я сохраняю

- Domain/kernel не импортируют UI/драйвер/оркестратор. CLI не содержит формулы.
- open_input — один frozen проход с обязательным EOF; summary только после конца.
  Raw сначала, DB потом: orphan допустим. Batch identity — canonical manifest SHA.
  Неизвестный исход COMMIT не равен rollback. 0002 отказывает на непустом legacy
  ingest_batch, не подделывает backfill.
- PSP semantic equal/later observed создаёт receipt; earlier observed —
  TEMPORAL_CONFLICT whole-package. Canonical business fact не обновляю.
- Ingest/run attempts: started отдельно, success вместе с опубликованными данными,
  failure best-effort; terminal success не перезаписываю. Case-attempt failure
  journal ещё не написан, не приписываю ему run_attempt.
- Run manifest/input/result/evidence immutable. Входы читаю через сохранённые
  membership/receipts, не выбираю latest при execute. Engine SHA требует точные
  байты реализации; старый SHA не заменяю новым. Сохранённый result читаю независимо.
- В текущем manifest/result v3 knowledge_at отделён от as_of. As-was: равные границы.
  As-known-now: явный knowledge и published baseline того же merchant/as_of с
  меньшей knowledge boundary, reason enum. PSP occurred<=as_of, receipt observed
  <=knowledge; OMS effective<=as_of, observed<=knowledge. Timestamps не клипую.
- Published_at — marker до COMMIT, не исторический commit timestamp. Exact replay
  относится к сохранённым input IDs, не реконструкции старого MVCC snapshot.
- Run changes только читает результаты/lineage, отмечает изменение engine/visibility/ruleset/deadline.
  Не утверждаю, что любая разница вызвана только late data.
- Case presence отдельно от workflow=open. Application/stream/head/revision/event
  публикую одним COMMIT. Уже применённый run noop даже после продвижения; новый
  as-was строго позже по as_of, knowledge не уменьшается; tie разных run — отказ.
  As-known-now report-only для Case. Absence не закрывает человеческое решение.
- Лимиты: execution 10000 orders/50000 receipts/16 MiB result; projection 10000
  исторических cases на merchant и 64 KiB на finding; read pages bounded.
- OMS v1 сохраняет semantic payload и общий settle_after, адаптирую его к двум
  одинаковым срокам в памяти. OMS v2 требует обе due_at, core settle_after=max.
  PSP остаётся v1. New run manifest/result v3: balance-v2/per-leg-v2, input version
  закреплена в membership/FK, balances содержат оба срока и per-leg states.
  Новый executor принимает v3, исторические сохранённые результаты читает viewer.
- Общий state: discrepancy > pending > matched, оба денежных findings только
  после собственного срока. Currency mismatch blocks, не складываю валюты.
- Case v1→v2 требует --upgrade-from-run-id с точным current head, строго новым
  as_of, неубывающим knowledge. Policy/source immutable в application. Same-policy
  upgrade и обратный переход отклоняю. Новый пустой stream может начать v2.
- Все 0001…0008 после публикации неизменяемы. Новые изменения — additive migration,
  точные версии/границы/ограничения фиксирую в TECHNOLOGIES/VALIDATION/ADR.

## Что я ещё не написал

Settlement/Prefect/freshness/catalog — остаток S3; следующий CG-302. HTTP/UI, роли, назначения, комментарии, ручное закрытие и human audit — S4.
Метрики/полная эксплуатация/итоговая демонстрация — S5/S6. Не изображаю эти планы
реализованными возможностями и не меняю автоматизацию мини-проектов на флагман.

## Проверки текущего checkout

Я использую .venv Python3.12 и requirements-analytics.lock с hashes (61 пакет).
Unit: .venv/bin/python -m unittest discover -s tests -v.
Integration: .venv/bin/python scripts/check_postgres.py --pg-bin /usr/lib/postgresql/16/bin.
Runner создаёт/останавливает/удаляет собственный PostgreSQL16 без TCP; не принимает
путь к чужой БД и не трогает существующий кластер. Sandbox socket может требовать
разрешённого внешнего запуска. В models отдельные staging/preaggregate/marts,
core immutable; `known_actual` — OMS scope и NULL при blocked, не PSP turnover.
Я не публикую .venv, analytics/target/logs, raw, БД и временные отчёты.
