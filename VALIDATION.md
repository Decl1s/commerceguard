# Фактические проверки CommerceGuard

## 25.10.2026 — CG-301, я включил исполнение

Я сменил прежний режим отдельным решением. Ниже — факты текущего checkout;
старый журнал в конце сохраняю как историю, а не действующий запрет.

| Проверка | Наблюдённый результат |
| --- | --- |
| Python 3.12.15, `unittest discover -s tests -v` | 15 tests, OK, без skip на Linux |
| compileall commerceguard/tests/scripts | Завершился без ошибок |
| CLI demo | 5 balances, 4 findings, дедупликация 1, невидимое событие 1; JSON сроков сериализуется |
| Установка analytics lock | uv 0.13.1: 61 пакет с проверкой hashes в собственной .venv; dbt-core-experimental-parser 2.0.8 собрался из sdist |
| Миграции PostgreSQL 16.15 | 0001…0008 применены к пустой одноразовой БД; повтор migrate — noop; 20 persistent tables |
| Полный приём | 5 OMS / 7 PSP records; повтор пакета возвращает duplicate_batch |
| Run | prepare/execute replay без второго result, result/evidence читаются |
| Поздние данные | corrective run убирает одну недоплату; один newly visible event; SHA исходного отчёта неизменен |
| Case | apply repeat noop; corrective apply отклонён report-only; old retry не откатывает head; show/history читаются |
| Whole-package ошибки | conflict, earlier-observed и invalid-json отвергнуты; количество canonical payment facts не изменилось |
| OMS v2 | Новый snapshot выбран, expectation_version=2, capture discrepancy отдельно от refund deadline |
| dbt Core 1.12.6 / dbt-postgres 1.11.0 | 8 view models + 13 data tests: PASS=21, WARN=0, ERROR=0, SKIP=0 |
| Финансовый JOIN | O1001: 3 capture events → 10500; 2 refunds → 100; повторная доставка не добавляет event |
| Валюты/неизвестность | USD finding сохранён при order_count=0; actual=NULL, blocked balance также NULL |
| Завершённость | 4 опубликованных run вошли в mart, отдельный prepared run исключён |
| Очистка | Каждый integration runner останавливает свой кластер в finally и удаляет временный каталог; исходный подготовительный кластер также остановлен |

Команды воспроизведения — README. Временный сервер я запускал только через Unix
socket внутри приватного каталога без TCP. Реальных данных/существующей БД нет.
В dbt отключил анонимную телеметрию. В target/logs остаются локальные артефакты,
в публикацию они не входят. CI не создавал и не выдаю локальный запуск за CI.

### Что я действительно исправил

При втором raw persist обнаружил TypeError: regular_file имеет keyword-only
artifact, а RawStore передавал его позиционно. Исправил оба вызова — в _verify
и resolve_manifest — и добавил регрессию raw repeat/resolve/corruption.
Первый unit-набор также выявил две ошибки самих тестов: tuple dataclass вместо
сохранённой JSON list и необработанный EOF guard контекстного менеджера. Я уточнил
fixtures/ожидание исключения; production проверки для прохождения тестов не ослаблял.
В integration runner исправил имя psp-late, прежде чем получить успешный прогон.

### Что пока не подтверждено

Я не выполнял Windows, нагрузку, конкурентных writers, аварийный COMMIT/power loss,
backup/restore, полный legacy-data upgrade, реальный v1→v2 Case stream upgrade,
выполнение исторического kernel, сетевые роли/CSRF, веб-интерфейс и CI.
Текущий integration покрывает v1/v2 INPUT в balance-v2, а не архив старых executors.
Fallback чтения result v1/v2 написан, но fixtures этого integration — result v3.
Проверки не означают production readiness или внешнюю приёмку Sprint 1/2.

## Исторический журнал до включения проверок

# Исполнение и ограничения

24.10.2026. Я веду текущий этап без запуска приложения и проверок.

| Действие | Факт |
| --- | --- |
| Написание исходников и документов | S0, S1/CG-101 (схема) CG-102 (manifest/parser) и CG-103 (raw/COPY/publish) написаны |
| input inspect / CSV / JSONL parser | Не запускались; примеры входов не прогонялись |
| Запуск python -m commerceguard | Не выполнялся |
| Импорт/compileall/py_compile | Не выполнялись |
| Unit, integration, end-to-end, нагрузочные проверки | Не выполнялись; тестовые файлы не создавались |
| Линтер, formatter check, type checker | Не запускались |
| Установка зависимостей, pip install, сборка | Не выполнялись |
| SQL и migration runner | Написаны; сервер не подключался, схема не создавалась, SQL не применялся |
| Контейнеры, веб-сервер | Ещё не реализованы и не запускались |
| CI | Workflow не создавался; автоматический запуск проверок отключён отсутствием workflow |
| Windows/Linux работоспособность программы | Не подтверждена ни на одной ОС |
| Результаты demo в документах | Расчёт по контракту вручную, не наблюдавшийся stdout |
| Производственная готовность | Не заявляется |

Операции создания/чтения файлов, Git и публикации документов не исполняют предметный
код. Публичный состав контролируется отдельным явным списком; это защита от случайной
публикации домашней папки, а не свидетельство качества приложения.

Реальные ошибки исполнения неизвестны, потому что исполнения не было. Не придумываю
успешные прогоны, замеры, покрытие, найденные баги или сравнения производительности.
Продолжаю поэтапное написание в этом режиме до отдельного решения о запуске.
Невыполненные проверки остаются в журнале риска; они не считаются «пройденными по умолчанию».

Сохранение в GitHub отражается в локальном журнале проекта отдельно от готовности
продукта. Эта итерация — публикация разработки, не стабильный релиз.

CG-101: constraints/FK/append-only, checksum/lock/rollback, отказ при чужой схеме
и сокрытие DSN предусмотрены исходниками. Исполнением не подтверждались.
Pins requirements-postgres.lock выбраны по метаданным официального реестра;
resolver, установка и импорт драйвера не выполнялись.

CG-102: написаны ограничения manifest/байтов/строк, временный снимок, raw/semantic
SHA, строгий JSON/CSV, номера записей, внутрипакетные повторы и полный EOF.
Ни один сценарий не выполнялся: hash mismatch, malformed UTF-8, malformed CSV/JSON,
NaN/повтор ключей, конфликт ID и ранний выход описаны как намерение кода.
Новых Python-зависимостей нет. Производительность и память не измерялись.

CG-103: постоянный raw, canonical manifest identity, temp staging/COPY, одна
транзакция публикации, PSP receipts и temporal conflict написаны, не исполнялись.
0002 не применялась. Отказ на legacy batches, hard link/fsync на Linux/Windows,
параллельные загрузки, replay и обрыв COMMIT не проверялись. Драйвер не установлен.
Административная публикация исходников/Git не является проверкой этих сценариев.

CG-104: я написал миграцию 0003, журнал попыток, классификацию ошибок, scan-raw и
recover. Ни schema SQL, COPY, запись журнала, повреждённый raw, неизвестный COMMIT,
терминальный trigger, Ctrl+C, конкуренцию, обзор или replay не исполнял. Новых
успешных проверок не заявляю. Административная сверка GitHub не проверяет приложение.

CG-105: я написал генератор baseline/invalid-json/conflict/earlier-observed,
отдельный late PSP и read-only status. Не генерировал входные файлы, не выполнял
CLI, не подключал БД, не прогонял ожидаемые количества или ошибки. Команды в
WORKBENCH и примеры чисел — инструкция и ручная спецификация, не результаты запуска.

CG-201: я написал 0004, selector опубликованных входов, canonical run manifest,
engine fingerprint и CLI prepare/show. Не выполнял SQL, read/write, timestamps,
ambiguous/missing OMS, отсутствующий PSP, предел входов, locks и replay. Fingerprint
приложения не вычислял вызовом его кода. Это планирование/исходники, не результат сверки.

CG-202: я написал 0005 и run execution/result/evidence. Не исполнял kernel через
БД, JSON round-trip, FK, counts, memory caps, lost COMMIT, concurrency, repeat или
просмотр evidence. Результаты в RESULTS — ручной ориентир, не наблюдённый stdout.
ОС, скорость и память не измерял. Исходники остаются unverified.

CG-203: я написал 0006, case projection/store и apply/list/show. Не выполнял
SQL, FK/триггеры, strict finding parse, canonical ordering, replay, concurrency,
lost COMMIT, размерные границы, пагинацию или CLI. Рассуждения в CASES — спецификация,
не наблюдённый результат. Административная публикация не проверяет приложение.

CG-204: я написал 0007, temporal contract v2, baseline/reason, раздельные границы
kernel и read-only changes/evidence visibility. Не выполнял миграцию, имена checks,
baseline FK, выбор позднего OMS/PSP, kernel, SHA migration, сравнение историй,
receipt visibility, размерные/временные границы или CLI. Числа и переходы LATE_DATA —
ожидаемая спецификация. Административные Git/публикация не доказывают корректность.

CG-205: я написал 0008, OMS v2, совместимое чтение v1, per-leg deadlines/states,
manifest/result v3, версию membership, flags сравнения и явный Case policy upgrade.
Я не выполнял parser/generator/demo, импорт, SQL/constraints/FK, сериализацию,
semantic hashes вызовом приложения, migration/replay, concurrency, CLI, проверки
или CI. Реальных ошибок исполнения и подтверждённых ОС нет. Числа и переходы
DEADLINES — спецификация вручную. Административная сверка разрешённых GitHub
файлов и их SHA относится только к факту публикации, не корректности кода.
S2 остаётся Review/unverified; stable release и приёмку не объявляю.
