# Как я готовлю CommerceGuard к будущему серверу

27.10.2026. Сейчас я использую localhost. Отдельный сервер и домен ещё не выбрал,
поэтому DNS, публичный сертификат и внешнюю установку не выдаю за состоявшиеся.
Я подготовил второй Compose профиль и проверил HTTPS на временном локальном стенде.
Стабильный tag1.0.0 сохраняю; эти изменения веду отдельно в1.1.0.dev1.

## Как я пробую приложение сейчас

Из корня checkout я создаю настройки один раз и запускаю локальный профиль:

```bash
python3 deploy/configure.py
python3 deploy/manage.py up -d --build --wait
python3 deploy/manage.py run --rm --build tools demo
```

Если настройки уже есть, первый шаг пропускаю: configure не меняет существующие
секреты. Открываю http://127.0.0.1:8765/login под manager. Случайный пароль читаю
локально из workspace/deployment/operator_password. Demo явно создаёт только
синтетические данные M01; будущая рабочая установка стартует пустой.

```bash
python3 deploy/manage.py ps
python3 deploy/manage.py logs --tail 40 web
python3 deploy/manage.py stop
python3 deploy/manage.py up -d --wait
```

Stop сохраняет контейнеры и данные; down также сохраняет volumes. Для обычной
остановки не использую down --volumes. Я оставляю project name commerceguard:
другое имя создаст другой набор volumes. После изменения кода пересобираю image
через up --build: редактор не меняет уже работающий контейнер автоматически.

## Что я переношу на будущий сервер

Я выбираю отдельный Linux x86_64 сервер с Docker Engine, Compose2.24.4+ и Python3.12
для управляющих команд. Выделяю место для images, PostgreSQL, raw и независимых
backup;4GiB свободной памяти считаю стартовым ориентиром, не доказанной capacity.
Я использую отдельный домен, например cg.example.org; example.org — только пример.

На новом сервере я назначаю A на его публичный IPv4. AAAA добавляю только при
работающем IPv6. Открываю входящие TCP80/443 к серверу и оставляю SSH доступным
для администрирования. Порты5432/8080/8081/8765 не публикую. Я проверяю правила
провайдера и Docker firewall, поскольку публикация Docker портов может обходить
обычные ufw INPUT правила. Настройки хоста/аккаунта самовольно не меняю.

На новом сервере с пустыми volumes:

```bash
python3 deploy/configure.py --directory workspace/server --domain cg.example.org
python3 deploy/manage.py --settings workspace/server/.env up -d --build --wait
python3 deploy/manage.py --settings workspace/server/.env ps
```

Я заменяю пример своим доменом без https, порта и пути. Configure приводит DNS имя
к нижнему регистру и отклоняет URL, IP, wildcard, пробелы и Caddy directives.
В .env сохраняю mode=internet, точный https origin и домен; пароли остаются отдельными
secret files в закрытом каталоге. Email в исходники и настройки не добавляю.

Manage читает этот .env и сам выбирает compose.yml+compose.internet.yml. Он убирает
ambient COMPOSE_/COMMERCEGUARD_ overrides, проверяет mode/origin и передаёт команды
без shell. Установка1.0.0 без поля mode по-прежнему считается local. Import_input
использует тот же выбор профиля, поэтому загрузка файлов не теряет конфигурацию.

## Почему я выбрал такую TLS схему

Интернет overlay полностью заменяет ports с помощью !override: наружу идут только
80→8080 и443→8443. Local8765 не остаётся вторым входом после merge. Поэтому мне
нужен Compose не ниже2.24.4. Web и PostgreSQL остаются во внутренней сети; web не
получает owner secret/raw. Proxy работает non-root, с read-only rootfs и cap_drop.

Я использую прежний закреплённый Caddy2.11.7 image. Для реального домена Caddy
получает/обновляет сертификат через Let's Encrypt; HTTP перенаправляет на HTTPS.
Должны работать DNS и доступность80/443 снаружи. TLS использует публичные80/443,
хотя внутри контейнера Caddy слушает непривилегированные8080/8443. Я ограничил
протоколы h1/h2, поэтому отдельный UDP443 не требуется. HSTS действует только
на этот hostname, без preload/includeSubDomains. Случайный Host/SNI не становится
новым обслуживаемым доменом; on-demand certificate issuance я не включаю.

ACME account и certificates сохраняю в tls_data/tls_config с правами proxy UID10001.
Обычный restart/down/up их не уничтожает. Readiness на неопубликованном8081
проверяет backend и не доказывает уже полученный публичный сертификат. Поэтому
после установки отдельно открываю https://СВОЙ_ДОМЕН/login с нормальной проверкой
сертификата; подтверждаю login, CSV,403 неправильного Origin и сохранность сессии.
Не использую curl -k или игнорирование TLS ошибок как критерий готовности.

## Как я переношу данные и сопровождаю установку

Для новой пустой рабочей базы demo не запускаю. Аккаунты создаю owner tools через
manage run --rm tools account create; пароли ввожу getpass. Файлы принимаю через
deploy/import_input.py --settings workspace/server/.env, затем явно выполняю
prepare/execute/case apply по HANDBOOK. Публичной саморегистрации нет.

При переносе существующих данных сначала создаю и проверяю DB+raw backup по BACKUP,
восстанавливаю в отдельную пустую БД до init/web и заново выдаю runtime grants.
Существующий manager в восстановленной базе сохраняет свой пароль; новый
operator_password не меняет его. При необходимости выполняю owner account reset,
затем вхожу заново: restore отзывает sessions. Секреты нового подключения и raw
переношу только закрытым административным каналом. Не запускаю новую server .env
поверх localhost volumes с другими DB passwords.

Финансовый backup не включает .env, Docker secrets и TLS volumes. Я сохраняю их
отдельно в защищённом месте вместе с tag/планом восстановления. Сами сертификаты
могу перевыпустить при потере; старую БД ради этого не удаляю. Для обновления
сохраняю точный tag/commit, backup и project name; порядок отката — HANDBOOK.

## Что я фактически проверяю

Scripts/check_internet создаёт собственный project cg-https-… с двумя случайными
loopback портами. Рабочий ACME Caddyfile отдельно разбираю через caddy adapt.
Только во временном fixture заменяю issuer на private CA. Клиент проверяет цепочку
и hostname через SSLContext с явным root certificate; недоверенная CA отвергается.
Системное хранилище доверия и браузерные настройки не меняю.

Я проверяю308на https origin, HSTS, Secure/HttpOnly/SameSite cookies, успешный
login/comment/CSV, отказ неправильным CSRF/Origin/Host, отсутствие лишних published
ports. Затем удаляю контейнеры без volumes, пересоздаю их и подтверждаю прежний
CA root и сессию. В finally удаляю только тестовый project и его volumes.
Публичный ACME challenge и внешний firewall этим локальным прогоном не проверены.
Отдельно scripts/check_browser повторяет прежний localhost путь в Chrome.

Официальные опоры: [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https),
[internal port mapping](https://caddyserver.com/docs/caddyfile/options#http-port),
[Compose merge/override](https://docs.docker.com/reference/compose-file/merge/),
[Docker/firewall](https://docs.docker.com/engine/network/packet-filtering-firewalls/).
