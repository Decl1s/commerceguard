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
в CASES/LATE_DATA/DEADLINES/SETTLEMENT и ADR-24…30. Не считать planned Prefect/HTTP написанными; dbt уже написан в CG-301.

## Моя актуальная точка

26.10.2026, версия0.1.0.dev12, schema9/24tables +9dbt views,106allowlisted файлов.
Я написал S0(2), S1(5), S2(5), S3/CG-301/302(2) =14из30 историй; остаются16.
Проверки включены: unit27 OK, PostgreSQL16.15 integration/migrations1…9,
upgrade заполненной schema8→9 с сохранением old results, dbt9models/19tests PASS28.
Settlement:9advice revisions/11reports; matched36000/1000/720/34280, fee+80,
unknown/NULL/late/new cutoff, completezero, signednet, conflicts и immutable UPDATE.
Текущая ветка codex/s3-cg302-settlement поверх CG-301 Draft PR#26.
CG-302 issue#27, проверенный срез сохраняю; фактическую публикацию пишу в WORKLOG.
Следующий Ready — CG-303: local Prefect ingest→reconcile→marts, bounded retry только
идемпотентных шагов, DB source of truth, без daemon/cloud. Prefect ещё не установлен.
HTTP/UI/freshness/catalog/эксплуатация ещё не написаны. Daily мини-проекты отдельно.
Перед новой веткой читаю свежий remote head; локальная и API история различаются.
CI отсутствует, локальный успех не CI. PR не сливаю автоматически, main — навигация.

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
- Settlement advice v1 отдельно от FileManifest: immutable revision, exact members,
  assignment merchant/event→settlement, currency/period family fixed. Пропущенный
  PSP fact разрешён в membership, даёт unknown. Reassign/void ещё нет. Canonical
  identity отдельно от raw SHA, raw-first orphan допустим; ingest scan/recover
  standalone advice не обнаруживает, отдельного attempt journal пока нет.
- Settlement tariff обязателен отдельно (0…10000bps), fee с gross half-up один раз,
  refund fee не возвращает, net signed. Unknown все expected/delta NULL, complete
  empty — knownzero. Request identity =advice/cutoff/tariff/visibility/engine,
  exact retry читает сохранённый result; late требует нового cutoff. Один visible
  receipt/member, reported−expected delta; не меняю OMS Case. Mart grain report_id.
- Все 0001…0009 после публикации неизменяемы. Новые изменения — additive migration,
  точные версии/границы/ограничения фиксирую в TECHNOLOGIES/VALIDATION/ADR.

## Что я ещё не написал

Prefect/freshness/catalog — остаток S3; следующий CG-303. HTTP/UI, роли, назначения, комментарии, ручное закрытие и human audit — S4.
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
