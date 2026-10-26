# Как я сохраняю и восстанавливаю рабочий экземпляр

Я храню комплект DB+raw в новом закрытом каталоге, отдельно от Git и публичного
source archive. В нём есть данные, хеши паролей и финансовая история: это приватная
резервная копия. Шифрование диска/внешнего хранения и ротацию ключей задаю на уровне
своей инфраструктуры; plaintext backup не публикую. SHA обнаруживает повреждение,
не удостоверяет неизвестного отправителя. Восстанавливаю только свои доверенные
комплекты: SQL dump содержит исполняемые функции.

```bash
.venv/bin/python -m commerceguard.backup create --raw-root workspace/raw --bundle workspace/backups/new-copy
.venv/bin/python -m commerceguard.backup verify --bundle workspace/backups/new-copy
```

Команды требуют PostgreSQL16 tools (`--pg-bin`) и явный single-host DSN отдельной
БД commerceguard через `--dsn-env`. Пароль не передаю в аргументе: для дочернего
процесса создаю временный pgpass0600, очищаю унаследованные PG* параметры. Service,
несколько hosts и произвольные connection options здесь не поддерживаю.

Во время create я беру shared schema lock и exclusive maintenance lock. Все
кооперативные записи приложения сначала получают shared maintenance lock; активная
запись означает BACKUP_BUSY, новая запись во время копии отказывает. Прямой DBA
вне этой координации: при административных загрузках сначала останавливаю writers.
Raw first может оставить orphan, но не новый опубликованный факт в snapshot БД.
Копирую только завершённые immutable объекты, проверяю ссылочную полноту published
пакетов/advice, hash каждого объекта, запрет symlink и лимиты100000файлов/10GiB.
Pg_dump custom archive и raw входят в один manifest, публикация каталога атомарна.
Данные/каталоги синхронизирую fsync; реальное отключение питания я не моделировал.

Для восстановления сначала останавливаю web и ingestion, создаю **отдельную пустую**
БД commerceguard и выбираю **новый** raw root. Существующую БД команда не очищает.

```bash
.venv/bin/python -m commerceguard.backup restore --bundle workspace/backups/new-copy --raw-root workspace/restored-raw --dsn-env COMMERCEGUARD_RESTORE_URL
```

Я проверяю весь manifest до SQL, готовлю raw staging и restore intent. Pg_restore
создаёт SQL без старых owner/ACL, psql выполняет его, отзыв всех web sessions и
INSERT restore receipt **одной транзакцией**. Identity пользователей/аудит сохраняю,
живые session cookies после восстановления не действуют. Новый owner — роль,
выполнившая восстановление; runtime grants настраиваю отдельно при поставке.

DB и filesystem не имеют общего COMMIT. После DB receipt я переименовываю готовый
raw staging. Если процесс остановился после DB COMMIT, intent остаётся рядом с
целевым root. Вызываю `backup finish-restore` с теми же bundle/raw-root/DSN: серверный
receipt подтверждает нужный комплект, файлы сверяются снова, root публикуется.
Существующий чужой root не затираю. Если receipt нет, восстановление не подтверждено:
сохраняю intent/staging, проверяю пустоту целевой БД и разбираю отказ; DROP/reset
не выполняю автоматически. Доверенный исходный bundle остаётся нетронутым.

Я фактически восстановил комплект в другом временном PostgreSQL с другим owner,
сравнил run SHA, Case workflow/revisions и human command SHA. Проверил отзыв sessions,
отказ повреждённого dump и непустой БД, а также finish после внедрённой остановки
между DB COMMIT и raw publication. Оба своих кластера остановил. PITR, распределённое
хранилище и восстановление после потери всех копий не заявляю. Для эксплуатации
держу минимум одну отдельную защищённую копию и регулярно повторяю restore drill.
