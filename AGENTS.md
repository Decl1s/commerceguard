# Продолжение CommerceGuard

Я веду отдельный флагманский учебный проект с 24.10.2026. Актуальные решения
из разговора имеют приоритет. Ежедневные мини-проекты и их автоматизация отдельно.

## Мои обязательные границы

- Все объяснения, комментарии, документацию и PR я пишу по-русски от первого лица
  единственного числа. Не использую «по запросу пользователя» и пересказ поручений.
  Технические определения, поля и роли продукта называю прямо. Не выдумываю
  коммерческий опыт, клиента, результаты запусков или внешнюю приёмку.
- Я выбрал режим без исполнения: не запускать приложение, импорт, demo/generator,
  SQL/миграции, compile/lint/typecheck, тесты, сборку, контейнеры или CI. Не создавать
  скрытых workflow. Меняю режим только отдельным явным решением о запуске.
- Исходники unverified. Наличие кода/Draft PR не означает «работает», Accepted или
  производственный релиз. Административные Git/публикация/чтение допустимы.
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
docs/sprints/S2, DATA_CONTRACTS и соответствующие ADR в DECISIONS.
PROGRESS — постоянная таблица этапов; BACKLOG — критерии; WORKLOG — факты.
Исторические разделы ранних контрактов сохраняю, актуальные расширения описаны
в CASES/LATE_DATA и ADR-24/25. Не считать planned dbt/Prefect/HTTP написанными.

## Моя актуальная точка

25.10.2026, версия 0.1.0.dev9, schema 7, 20 persistent tables.
S1/CG-101…105 и S2/CG-201…204 написаны в Review/unverified, без исполнения.
Текущая ветка codex/s2-cg204-late-data, Draft PR #22 поверх #20.
Следующую ветку строю от актуального удалённого CG-204, не от локального remote SHA.
Следующий Ready — CG-205, issue #23: OMS v2 и отдельные deadlines capture/refund,
с совместимостью immutable прежних inputs/results и явным ruleset смыслом.
Главная ветка остаётся навигацией, не принятым приложением. Ранние Draft PR:
#1 → #10 → #11 → #12 → #13 → #14 → #16 → #18 → #20 → #22.

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
- В новом manifest/result v2 knowledge_at отделён от as_of. As-was: равные границы.
  As-known-now: явный knowledge и published baseline того же merchant/as_of с
  меньшей knowledge boundary, reason enum. PSP occurred<=as_of, receipt observed
  <=knowledge; OMS effective<=as_of, observed<=knowledge. Timestamps не клипую.
- Published_at — marker до COMMIT, не исторический commit timestamp. Exact replay
  относится к сохранённым input IDs, не реконструкции старого MVCC snapshot.
- Run changes только читает результаты/lineage, отмечает изменение engine/visibility.
  Не утверждаю, что любая разница вызвана только late data.
- Case presence отдельно от workflow=open. Application/stream/head/revision/event
  публикую одним COMMIT. Уже применённый run noop даже после продвижения; новый
  as-was строго позже по as_of, knowledge не уменьшается; tie разных run — отказ.
  As-known-now report-only для Case. Absence не закрывает человеческое решение.
- Лимиты: execution 10000 orders/50000 receipts/16 MiB result; projection 10000
  исторических cases на merchant и 64 KiB на finding; read pages bounded.
- Все 0001…0007 после публикации неизменяемы. Новые изменения — additive migration,
  точные версии/границы/ограничения фиксирую в TECHNOLOGIES/VALIDATION/ADR.

## Что я ещё не написал

Раздельные capture/refund deadlines и OMS v2 — CG-205. Settlement/dbt/Prefect/mart —
S3. HTTP/UI, роли, назначения, комментарии, ручное закрытие и human audit — S4.
Метрики/полная эксплуатация/итоговая демонстрация — S5/S6. Не изображаю эти планы
реализованными возможностями и не меняю автоматизацию мини-проектов на флагман.
