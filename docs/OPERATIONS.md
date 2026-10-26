# Как я вижу состояние рабочего экземпляра

`GET /livez` проверяет живой процесс без БД. `GET /readyz` проверяет подключение,
идентичность/версию схемы и доступность schema lock; ответ только ok/unavailable,
без DSN, driver text и payload. Readiness не заменяет проверку данных источников.

`GET /metrics?merchant=M01` требует серверную сессию и доступ к магазину. Я показываю
число Case по валюте/presence/workflow, ingest attempts по source/state, сохранённые
результаты и source stale. HTTP counters/time относятся к одному процессу, сбрасываются
при restart и не являются финансовыми totals. Метрики источников читаются отдельно
от snapshot очереди: это наблюдение, не воспроизводимый финансовый отчёт.

JSON события содержат timestamp, event, случайный request_id, status, duration_us и
опциональный проверенный case_key. Ни URL/query, actor, текст формы, ни cookie/DSN
в них не попадают. X-Request-ID помогает связать ответ с событием. В human audit
сохраняется отдельный client request_id команды: он нужен для exact retry после
неизвестного COMMIT. Для503 разрешаю лишь чтение или повтор той же identity,
а409 требует перечитывания/осознанного нового решения. Сырые исключения не логирую.

Я оставил labels ограниченными enum, без case/run/user IDs и текста URL. Поэтому
частота запросов не создаёт бесконечную cardinality. Историю app events собираю
в stdout/stderr своей поставки; хранение/ротация логов задаются контейнером.
Длительность — wall clock monotonic процесса, не время завершения банковской операции.

Я проверил unauthenticated live/ready, authenticated scoped metrics, запрет другого
merchant и форму события. При проверке security обнаружил старый дефект bad-Host
POST: error handler обращался к ещё не установленному parsed URL. Я исправил его
и добавил настоящий HTTP сценарий403 вместо обрыва соединения.
