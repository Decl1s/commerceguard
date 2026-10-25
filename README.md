# CommerceGuard

**Информационная система контроля заказов, оплат и возвратов интернет-магазина.**

Я разрабатываю этот флагманский учебный проект дата-инженера на основе реалистичного бизнес-сценария.
Система должна объяснять расхождения между OMS и платёжным провайдером, сохранять
происхождение цифр и помогать финансовому специалисту довести разбор до решения.
Это не коммерческий заказ и не опыт работы у реального клиента.

> **Состояние 25.10.2026: Sprint 2, срез CG-204, 0.1.0.dev9, исходники не запускались.**
> Я пока не запускал приложение, тесты, сборку, линтер, анализатор типов,
> миграции, контейнеры и CI. Наличие кода
> не означает доказанную работоспособность. Производственный релиз не объявлен.

[Публичный репозиторий](https://github.com/Decl1s/commerceguard) ·
[Draft PR первого этапа](https://github.com/Decl1s/commerceguard/pull/1) ·
[CG-101: Draft PR #10](https://github.com/Decl1s/commerceguard/pull/10) ·
[CG-102: Draft PR #11](https://github.com/Decl1s/commerceguard/pull/11) ·
[CG-103: Draft PR #12](https://github.com/Decl1s/commerceguard/pull/12) ·
[CG-104: Draft PR #13](https://github.com/Decl1s/commerceguard/pull/13) ·
[CG-105: Draft PR #14](https://github.com/Decl1s/commerceguard/pull/14) ·
[CG-201: Draft PR #16](https://github.com/Decl1s/commerceguard/pull/16) ·
[CG-202: Draft PR #18](https://github.com/Decl1s/commerceguard/pull/18) ·
[CG-203: Draft PR #20](https://github.com/Decl1s/commerceguard/pull/20) ·
[CG-204: Draft PR #22](https://github.com/Decl1s/commerceguard/pull/22) ·
[Истории в GitHub](https://github.com/Decl1s/commerceguard/issues).

**[Таблица этапов: где я сейчас и что сделал](docs/PROGRESS.md).**

## Бизнес-проблема

Заказ на 120 рублей виден в OMS, но провайдер подтвердил только 110 рублей.
Другой заказ получил одобренный возврат 30 рублей, а фактически вернулось 10.
В net-выручке две независимые ошибки иногда компенсируются. Таблица с одним
итоговым числом их скроет. CommerceGuard сопоставляет поступления и возвраты
по отдельности, привязывает расхождение к исходным фактам и хранит историю разбора.

## Что уже написано, а что впереди

| Слой | Написано сейчас | Запланировано |
| --- | --- | --- |
| Предметная модель | Неизменяемые ожидания OMS и события PSP, валюты, суммы, UTC | Дальнейшие версии контрактов |
| Сверка | Я написал kernel, manifest/result, raw evidence, два времени и сравнение corrections | Раздельные сроки и следующие версии правил |
| Демонстрация | Команда demo, синтетические константы, JSON-вывод | Полный пользовательский сценарий |
| Хранение | Я написал 20 SQL-таблиц, миграции 0001…0007, приём, run и case history; SQL не применял | Витрины и дальнейшие контракты |
| Входные файлы | Строгий manifest, ограниченный OMS CSV / PSP JSONL parser, raw/semantic SHA и input inspect; без исполнения | Дальнейшие версии файлового контракта |
| Контур данных | Архитектура raw/core/mart/ops | dbt, Prefect, backfill |
| Работа с кейсами | Я написал canonical apply, heads/revisions/events, CLI list/show | Интерфейс, роли, назначение, комментарии и ручное закрытие |
| Эксплуатация | Ограничения, риски, план восстановления | Метрики, журнал, резервирование, контейнерный запуск |

Текущий срез содержит код приёма файлов, постоянного raw и публикации в БД.
Он не инициирует финансовые операции. Я пока не запускал команды приложения.
PSP означает payment service provider; OMS — order management system.

## Как читать проект

1. [START_HERE.md](START_HERE.md) — маршрут на 10 минут; [PROJECT_MAP](docs/PROJECT_MAP.md) — все модули и места расширения.
2. [PRD](docs/PRD.md) — пользователи, сценарии, бизнес-правила и границы продукта.
3. [PROGRESS](docs/PROGRESS.md) — таблица фактов; [ROADMAP](docs/ROADMAP.md) — цели спринтов.
4. [KANBAN](docs/KANBAN.md) и [BACKLOG](docs/BACKLOG.md) — текущее состояние и очередь.
5. [ARCHITECTURE](docs/ARCHITECTURE.md), [DATA_CONTRACTS](docs/DATA_CONTRACTS.md),
   [DECISIONS](DECISIONS.md) — движение данных, формулы и причины выбора.
6. [NOTES](NOTES.md), [EXERCISES](EXERCISES.md) — подробный разбор и задания.
7. [VALIDATION](VALIDATION.md) — честный статус исполнения; [TECHNOLOGIES](TECHNOLOGIES.md) — зависимости.

## Команды для самостоятельного просмотра

Я подготовил эти команды, но **пока не выполнял их**. Python 3.12,
целевой patch 3.12.15. Для demo сторонние пакеты не нужны.
Рабочий каталог — корень commerceguard.

Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m commerceguard demo
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m commerceguard demo
```

Для demo и input inspect не требуется pip install. Demo читает константы demo.py
и печатает JSON. [INPUTS](docs/INPUTS.md) описывает формат внешних файлов и команду
`input inspect --manifest PATH --data PATH`: полный разбор с выводом только метаданных,
без постоянного raw/БД. Обе команды не запускались.
Опциональные команды db описаны в [STORAGE](docs/STORAGE.md): для них нужны
закреплённый driver-набор и отдельная уже созданная PostgreSQL 16 БД commerceguard.
SQL написан, но не применялся. Новый [CG-103](docs/INGESTION.md) описывает
`ingest publish`, повторы и границы raw/БД. HTTP-сервера пока нет.
Вычисленный вручную ориентир demo:
5 балансов заказов, 4 finding; matched=1, discrepancy=2, pending=1, blocked=1;
unique_visible_events=6, duplicates_removed=1, not_yet_visible_events=1.
Это **ожидаемые значения по модели, а не результат запуска**.

## Как ведётся работа

Один заход — один небольшой срез, связанный с целью спринта. Sprint 0 подготовил
бизнес-запрос, план и начальное ядро. В S1 написаны CG-101 (хранение)
и CG-102 (файловый контракт/parser), CG-103 (raw/COPY/публикация).
CG-104 добавил журнал попыток и recovery, CG-105 — status и генератор.
CG-201 закрепляет immutable run manifest, CG-202 сохраняет результат/evidence.
Дальше — CG-203 (кейсы и ревизии),
затем сохранённая сверка, витрины, оркестрация, рабочее место и эксплуатация.
Порядок и критерии переходов описаны в [PROCESS](docs/PROCESS.md).
Задачи не закрываются автоматически по факту написания файла. У непроверенного
кода состояние Authored, а не принятый рабочий Increment.

Все исходники и примеры создаются для проекта. Контакты, выгрузки и секреты пользователя
не нужны. В публичную историю входят только файлы из [PUBLIC_FILES.txt](PUBLIC_FILES.txt).
Официальные материалы и даты обращения собраны в [SOURCES](docs/SOURCES.md).

## CG-104: диагноз и восстановление

Я добавил независимый журнал попыток, карантин целого пакета, безопасные error codes,
ограниченный обзор raw и повтор приёма по manifest hash. Полный маршрут, состояния,
команды и ограничения описал в [RECOVERY](docs/RECOVERY.md). Обрыв COMMIT отмечаю
как неизвестный исход; не перезаписываю опубликованный успех сообщением об ошибке.
Код, журнал и SQL пока не запускал. Текущая история остаётся unverified.

## Полный учебный маршрут S1

Я добавил [WORKBENCH](docs/WORKBENCH.md): `input generate`, `input inspect`,
`ingest publish/status`, точный replay и варианты JSON/semantic/temporal отказа.
Генератор не использует реальные данные и не заменяет существующий каталог.
Status читает только metadata; поздний PSP храню отдельным пакетом. Весь S1
написан без исполнения, а не принят как проверенный Increment. Начну S2 с CG-201.

## Начало S2: входы будущего расчёта

Я написал [CG-201](docs/RUN_MANIFEST.md): `run prepare/show`, выбор опубликованного
OMS/PSP, immutable input IDs/hashes, cutoff, balance-v1 и fingerprint своих исходников.
Пока сохраняю только manifest с state=prepared, без вычисления findings. Точные
исторические повторы относятся к сохранённому run ID; ограничение published_at
marker явно описал. as-known-now и поздние коррекции оставляю CG-204.

## CG-202: результат с происхождением

Я написал [RESULTS](docs/RESULTS.md): run execute/result/evidence, независимые
попытки вычисления, immutable JSON snapshot балансов/findings и raw-ссылки.
Выбираю только inputs сохранённого manifest; новый batch не меняет прежний отчёт.
Ограничил v1 10000 orders / 50000 receipts / 16 MiB result. Всё пока без исполнения.

## CG-203: одна карточка и история изменений

Я написал [кейсы и ревизии](docs/CASES.md): явное case apply по опубликованному run,
монотонный поток магазина, immutable revisions/events и read-only case list/show.
Старый retry не меняет текущий head. Absence не закрывает человеческую работу.
Миграция 0006 добавляет пять таблиц (всего 20), новых библиотек нет.
Подробная карта кода, аргументы, решения и пять упражнений — в CASES.
Следующий срез — CG-204: поздние факты и режимы пересчёта. Всё unverified.

CG-203 я сохранил в [Draft PR #20](https://github.com/Decl1s/commerceguard/pull/20); следующий [CG-204 #21](https://github.com/Decl1s/commerceguard/issues/21).

## CG-204: поздние данные и два времени

Я написал [режимы исторического пересчёта](docs/LATE_DATA.md): as-was/as-known-now,
явный knowledge_at, baseline/reason в manifest v2, result v2 и run changes.
Старые reports сохраняю; evidence показывает видимость receipt. Корректировка
исторической даты не продвигает текущие Case. В LATE_DATA объясняю каждое решение,
аргументы, карту файлов и пять упражнений. Схема 7, таблиц по-прежнему 20.
Я изменил kernel fingerprint; old manifests читаю, повтор вычисления требует
соответствующей реализации. Ничего не запускал. Следующий CG-205 — сроки/ожидания.

CG-204 я сохранил в [Draft PR #22](https://github.com/Decl1s/commerceguard/pull/22).
Следующий [CG-205 #23](https://github.com/Decl1s/commerceguard/issues/23) — сроки и версии ожиданий.
