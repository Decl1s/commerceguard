# Я разбираю расхождение в локальном рабочем месте

Я связываю существующий расчёт с работой финансового аналитика: выбрать очередь,
увидеть свежесть, открыть карточку, проверить конкретный источник суммы и сохранить
человеческое решение отдельно от финансового факта. Сначала я ввёл только чтение
CG-401. Дальнейшие защищённые операции описываю ниже по фактически готовым срезам.

```bash
.venv/bin/python -m commerceguard.workbench serve --port 8765 --dsn-env COMMERCEGUARD_DATABASE_URL
```

Я заранее задаю DSN своей БД и применяю миграции штатным `db apply`; сервер сам
не мигрирует. Открываю `http://127.0.0.1:8765`, выбираю merchant. Ctrl+C останавливает
сервер. `--port` выбирает локальный порт, `--dsn-env` обозначает имя переменной,
а не сам DSN. В URL и аргументы пароль БД не передаю. `0.0.0.0` и внешний bind
не предусмотрены. Никаких постоянных служб и файловых download routes не создаю.

## Где что находится и почему

| Файл | Для чего я его отделил |
| --- | --- |
| `workbench_store.py` | Я проверяю фильтры и читаю один PostgreSQL snapshot очереди |
| `workbench.py` | Я маршрутизирую HTTP, экранирую HTML, показываю формы и ошибки |
| `case_store.py` | Я сохраняю исходную projection/history policy и читаю ревизии |
| `run_execution.py` | Я читаю evidence по сохранённому run, не пересчитываю деньги в UI |
| `source_health_store.py` | Я отдельно показываю состояние источников |
| `catalog.json` / `catalog.py` | Я объясняю зерно и смысл витрин без БД |
| `scripts/workbench_scenarios.py` | Я проверяю реальный HTTP и Case на одноразовой БД |

Я использую `HTTPServer` CPython3.12.15 и HTML forms без frontend build/node_modules.
Один процесс обслуживает запросы последовательно. Для учебного loopback интерфейса
это уменьшает стоимость установки; медленный запрос блокирует интерфейс, поэтому
есть socket timeout10с и bounded SQL с statement timeout30с. Я не называю это
production HTTP server: [документация Python](https://docs.python.org/3.12/library/http.server.html)
прямо ограничивает применимость. Внешняя поставка потребует другой deployment
адаптер, TLS, процессов, проверок нагрузки и отдельной модели доверия.

## Как я читаю очередь

Я требую merchant, затем могу ограничить currency RUB/USD/EUR, rule, status
open/closed/all, presence present/absent/all, возраст в днях и limit1…100.
Неизвестное поле, повторный query key и неверный диапазон дают400. Параметры SQL
передаю bind values; имена колонок выбираю только из собственного фиксированного
набора. Возраст считаю от first Case application.applied_at, а не от даты заказа,
дедлайна или срока работы исполнителя. Верхняя граница возраста включена.

Я показываю canonical run, as_of, knowledge_at, published_at и возраст расчёта.
Он не заменяет freshness источников: для неё есть отдельная ссылка. Очередь может
быть старой даже после свежей доставки PSP, если новый run ещё не применён.

Пагинацию делаю по стабильному case_key, без OFFSET. Следующая страница несёт
run_id; если canonical head сменился, возвращаю409 QUEUE_HEAD_CHANGED и начинаю
очередь сначала. Каждый page — отдельный read-only REPEATABLE READ snapshot.
Это живая очередь, не frozen экспорт: человеческие изменения между страницами
могут поменять состав выбранного status. Exact report берётся по immutable run,
а не из live рабочего списка. Денежный total по findings не показываю: одно
расхождение может отражать разные правила одного заказа. Counts группирую по
currency, валюты и плечи не смешиваю.

## Карточка и происхождение

Я показываю presence отдельно от workflow, первую/последнюю/evaluated run identity,
текущую ревизию и историю detected/changed/absent/reappeared. Историю ограничиваю
20 записями и даю cursor предыдущих ревизий. Evidence читаю по last_seen_run_id,
чтобы исчезнувший finding всё ещё имел своё доказательство. Ссылки ведут на
batch/raw row/SHA refs, raw payload и путь файловой системы не выдаю. Receipt
список ограничен100; признак truncated виден, полный список доступен прежнему CLI.

Текст и JSON всегда проходят HTML escape, JavaScript отсутствует. Я запрещаю
чужой Host и cross-site Fetch Metadata, выставляю no-store, nosniff, no-referrer,
CSP с frame-ancestors none и form-action self. Это конкретные локальные барьеры,
не заявление об абсолютной защите. Пользователь с прямым доступом к БД остаётся
вне веб-ролевой модели.

## Что я могу изменить руками

1. Я выбираю одну currency и limit1. Проверяю, что следующая страница не повторяет
   case_key; меняю canonical run между запросами и ожидаю409, а не смешанную очередь.
2. Я ставлю merchant без данных. Ожидаю понятное пустое состояние и отсутствие
   выдуманного zero финансового отчёта.
3. Я открываю absent Case. Его workflow не должен автоматически стать closed;
   evidence относится к последнему run, где finding реально был.
4. Я меняю фильтр rule и смотрю raw SHA в evidence. Проверяю происхождение суммы,
   затем читаю тот же saved result CLI; SHA не меняется от просмотра.
5. Я добавляю фильтр исполнителя после появления workflow. Меняю validation,
   параметризованный SQL, форму, пагинацию и сценарий с двумя операторами вместе.

## CG-402 — я включил вход и разграничение доступа

```bash
.venv/bin/python -m commerceguard.access create analyst_demo --role analyst --merchant merchant_demo
.venv/bin/python -m commerceguard.access create manager_demo --role manager --merchant merchant_demo
.venv/bin/python -m commerceguard.access disable analyst_demo
```

Я создаю собственные имена и пароли, команды выше не создают готовых credentials.
Пароль ввожу скрыто дважды, длина12…256 символов; в аргументах и журнале его нет.
Дубликат аккаунта отвергаю, автоматического reset пароля не делаю. Отключение
не удаляет identity и future audit: оно деактивирует аккаунт и отзывает все сессии.
Смену пароля/scope пока выполняет будущий административный сценарий, UI для неё нет.

| Роль | Чтение своих магазинов | Назначение / комментарий | Close / reopen |
| --- | --- | --- | --- |
| observer | Да | Нет | Нет |
| engineer | Да | Нет: инженер не подтверждает финансовое решение | Нет |
| analyst | Да | Собственное назначение и комментарий в CG-403 | Нет |
| manager | Да | Назначение допустимого аналитика и комментарий в CG-403 | В CG-404 |

Я храню пользователей, merchant scopes и сессии в трёх новых таблицах schema10.
Роль не беру из cookie/формы. Cookie содержит случайный256-bit token, в БД храню
его SHA256. Для пароля использую PBKDF2-HMAC-SHA256/600000 с отдельной128-bit солью
и constant-time comparison. Это переносимый вариант стандартной библиотеки без
новой native зависимости; я не заявляю FIPS certification. Для внешнего продукта
рассмотрю Argon2id. Мотив и параметры сверил с
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

Сессия имеет фиксированные8часов, logout удаляет серверную запись. На запросе
повторно проверяю active, expiry, роль и scope. Для будущей mutation делаю проверку
в той же транзакции, удерживаю SHARE lock пользователя/сессии до COMMIT. Поэтому
отзыв не может незаметно обогнать уже авторизованную запись. Read-only экран имеет
обычную модель in-flight запроса: уже начатое чтение может закончиться до отзыва.

CSRF я реализовал как server-side synchronizer token отдельный от session token.
Форме нужен точный Origin, Host, content type, ограниченный body и совпадающий
токен. Для login создаю одноразовый10-минутный challenge в памяти процесса и cookie
cg_login: защищаю также login CSRF, а не только уже действующую сессию.
[OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
описывает этот pattern. Cookie HttpOnly/SameSite=Strict, без Domain и с Path=/.
Secure не ставлю на явном HTTP loopback; этот интерфейс нельзя публиковать наружу
через reverse proxy и считать защищённым TLS приложением без доработки.

Я ограничил login10попытками/минуту на локальный процесс и5неверными паролями на
аккаунт до5-минутной блокировки в БД. Неизвестное имя тоже проходит dummy KDF.
На аккаунт допускаю20активных сессий. Это не распределённый rate limiter и не
защита от злоумышленника с доступом к процессу или самой БД. Restart теряет только
anonymous challenges/process throttle, серверные сессии и account lock остаются.
CSRF/token/пароль в access log не записываю, сторонние fonts/scripts не подключаю.

Я проверяю: чтение без login→401; чужой merchant→403; observer/engineer mutation→403;
неверный CSRF/Origin→403; replay login challenge→403; logout/disable→старыйtoken401;
account throttle после5ошибок. Пароль, DSN, cookie и произвольный driver error в
ответе не раскрываю. Windows, браузерную матрицу и внешний deployment не проверял.
