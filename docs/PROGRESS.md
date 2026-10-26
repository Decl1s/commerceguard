# Таблица этапов CommerceGuard

Я довожу первую рабочую версию по RELEASE_PLAN и подтверждаю готовность отдельно от количества задач.

| Этап | Написано |
| --- | --- |
| S0 | 2/2 |
| S1 | 5/5 |
| S2 | 5/5 |
| S3 | 5/5 |
| S4 | 5/5 |
| S5 | 2/5 |
| S6 | 0/3 |

Сейчас **CG-502**, написано **24/30**. Следующий **CG-503**.

Я добавил согласованный DB+raw backup, проверку повреждений и восстановление в пустую БД с server receipt и finish-restore.

Я прошёл89unit и полный PG/HTTP/dbt runner: реальный restore в другой кластер/owner, old SHA/Case/audit comparison, session revocation, tampering/nonempty denial и остановка после DB COMMIT.

Подробности: [BACKUP](BACKUP.md). Публикацию фиксирую в WORKLOG.
