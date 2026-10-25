# С чего я начинаю разбор CommerceGuard

25.10.2026, S3/CG-301, `0.1.0.dev11`. Я включил проверки: 15 Python tests,
8 миграций и 8 dbt models/13 data tests прошли на Linux. CI/Windows не проверял.
Точный список подтверждений и пробелов — VALIDATION.
Мои точные этапы — [PROGRESS](docs/PROGRESS.md), решения — [DECISIONS](DECISIONS.md).

## Мой маршрут на 10 минут

| Время | Что я открываю | На какой вопрос отвечаю |
| --- | --- | --- |
| 0–2 минуты | README и [PRD](docs/PRD.md) | Какую проблему магазина решаю и чего ещё нет |
| 2–4 минуты | [PROJECT_MAP](docs/PROJECT_MAP.md) | Где лежит код, как данные проходят через систему |
| 4–6 минут | domain.py и reconcile.py | Почему я считаю capture/refund с разными сроками и различаю два времени |
| 6–8 минут | [CASES](docs/CASES.md) | Как сохраняю одну проблему через несколько отчётов |
| 8–10 минут | [DEADLINES](docs/DEADLINES.md) и PROGRESS | Как объясняю разные сроки и где продолжаю разработку |

Я могу начать с чтения контракта либо с безопасных проверок README. Unit tests
не требуют сервера; scripts/check_postgres.py создаёт и удаляет собственный
временный кластер. Для отдельного dbt по своей подготовленной БД читаю MARTS.

## Как я читаю код по одной задаче

Для первого расчёта я иду в `domain.py` → `reconcile.py` → `demo.py`.
Для приёма — в `file_contracts.py` → `file_inputs.py` → `raw_store.py` →
`ingestion.py`; COPY layout находится в `sql/stage_input.sql`.
Для сохранённой сверки — в `run_plans.py` → `run_execution.py`.
Для карточки — в `case_projection.py` → `case_store.py`.
Для корректировки — в `reconcile.py` и `run_changes.py` после LATE_DATA.
Подключение и миграции держу отдельно: `postgres.py`, `migrations.py`, `sql/`.

Я читаю документацию рядом с каждой границей: INPUTS, INGESTION, RECOVERY,
RUN_MANIFEST, RESULTS, CASES и LATE_DATA. Точные модули, причины и места
расширения собрал в PROJECT_MAP, чтобы не искать их среди исторических записей.

## Мой расчёт на бумаге

Я беру O1002 из demo: ожидаю capture 12000, C02 подтверждает 11000.
У позднего C02L ещё 1000, но observed_at позже исходного cutoff T0.
В as-was с knowledge=T0 я получаю ожидаемую недостачу -1000 после settle_after.
Ключ проблемы зависит от merchant/order/currency/rule, а не от суммы.

Если поздний C02L относится по occurred_at к дате T0 и стал известен к T1,
то в новом as-known-now с as_of=T0 и knowledge=T1 ожидаю совпадение сумм.
Я сохраняю исходный отчёт и corrective baseline lineage. Исчезновение finding
не равно ручному закрытию Case. Историю карточки уже написал в CG-203;
исторический corrective report пока не продвигает актуальный stream.
Эти числа — спецификация вручную, не результат запуска кода.

## Где я меняю проект под себя

Сначала я описываю бизнес-смысл в DATA_CONTRACTS и ADR, затем меняю один слой.
Новый формат файла начинаю с INPUTS; новое правило — с Rule/reconcile;
новое человеческое действие — с отдельного workflow, а не формулы delta.
Я не добавляю расчёты в CLI и не редактирую опубликованные миграции.
Пять упражнений с ориентиром ответа есть в CASES и ещё пять в LATE_DATA.
В PROJECT_MAP я собрал маршруты изменений и вопросы для самостоятельного разбора.

## Как я открываю исходники в редакторе

Я открываю `commerceguard.code-workspace` в VS Code или совместимом редакторе.
В workspace только этот репозиторий: родительские Git не открываются автоматически.
Конфигурация не содержит задач, запуска приложения, установки расширений или CI.
Я держу рядом START_HERE, PROJECT_MAP, PROGRESS и текущий исходник.
Наличие workspace не означает, что редактор установлен или был открыт в этой среде.

## Что я оставляю на следующий этап

CG-205 я написал: [DEADLINES](docs/DEADLINES.md) связывает бизнес-пример, файлы,
аргументы и пять задач. CG-301 я проверил в основном сценарии; следующий Ready — CG-302, settlement.
S3: dbt/Prefect/settlement/витрины; S4: веб-рабочее место, роли, назначения,
комментарии и ручное закрытие; S5/S6: эксплуатация и итоговая демонстрация.
Это планы. Существующие Draft PR я не принимал автоматически.

## Как я изучаю разные сроки

Я читаю DEADLINES → file_contracts.oms_columns/order_from_csv → domain.OrderExpectation
→ reconcile. Для O1003 я на бумаге вывожу payment_shortfall при refund pending,
затем переношу cutoff ровно на refund deadline. В run_execution вижу сохранение
обоих сроков, в case_store — явный policy upgrade. Я не начинаю с изменения CLI:
смысл срока живёт в контракте и kernel. Это маршрут чтения, не выполненный прогон.

## Как я читаю новый SQL-контур

Я открываю MARTS → analytics/models/staging → intermediate → marts, рядом держу
analytics/tests и scripts/check_postgres.py. В run_results.json локально вижу
фактические узлы dbt, но target/logs не публикую. Пять задач с ожидаемыми ответами
есть в MARTS. PROGRESS показывает остаток: 17 историй исходного объёма.
