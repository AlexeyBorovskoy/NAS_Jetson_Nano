# Тесты Backup/Restore / Backup and Restore Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

## Проверка полного аварийного восстановления — 2026-10-09 / Full DR audit

🇷🇺 **Полное аварийное восстановление пока не подтверждено.** Эта проверка
уточняет готовность; разделы версии 1.0 ниже — исторические процедуры.
При аудите не запускать автоматически импорт в рабочую БД, бэкап и удаление каталогов.

🇬🇧 **Full disaster recovery has not been demonstrated.** This audit supersedes
the historical v1.0 readiness claims below. Do not automatically execute production
database imports, backup jobs or directory deletion during an audit.

Jetson проверен через существующий reverse SSH tunnel без sudo и изменений служб,
2026-10-09 11:47–11:53 UTC. / Inspected without sudo or service changes.

| Проверка / Check | Результат / Evidence | Граница доказательства / Limit |
|---|---|---|
| Дампы Nextcloud и Immich / DB dumps | По 7 файлов; свежие дампы возрастом около 8,8 часа; оба `gzip -t` → 0 | Импорт в PostgreSQL не проверен / SQL import untested |
| Дампирование / Database backup | `nasa-backup.service`: 03:00:19–03:00:35 UTC, `Result=success`, `ExecMainStatus=0` | Не доказывает запуск приложения из дампа / Not an application restore |
| Копирование конфигураций / Configuration backup | Служба: 03:47:23–03:47:30 UTC, success, код 0 | Состав последних HDD-снапшотов не проверен / Snapshot contents unverified |
| Копия Immich на HDD / Immich HDD copy | Служба: 04:34:29–04:37:11 UTC, success, код 0; каталог доступен | Полнота библиотеки и соответствие БД не проверены / Completeness and DB consistency untested |
| Учение / Existing restore drill | Таймер активен, последний trigger 2026-10-01; у службы нет сохранённых времён запуска | `Result=success` без времени не доказывает выполнение / No dated execution proof |
| Cloud.ru: четыре согласованные конфигурации / Four approved configuration files | 9710 байт; `restic check --read-data` и restore → 0; SHA-256 и режимы 4/4 | Нет ОС, секретов, БД и пользовательских данных / No OS, secrets, databases or user data |
| Текущая платформа / Current platform | 15 контейнеров запущены, SSD и HDD смонтированы | Работающая система не доказывает восстановление / Live operation is not recovery evidence |

🇷🇺 `restore_drill.sh` распаковывает копию на том же Jetson, проверяет обязательные
пути, чтение `.env`, наличие `instanceid`, целостность **одного** новейшего gzip-дампа
и непустой каталог Nextcloud. Импорта обеих БД и запуска приложений нет.
Независимый доступ к паролю restic, восстановление ОС и фактический RTO не проверены.
Документированный импорт БД 2026-08-09 — историческое свидетельство.
S3 доступен для проверенных пробных репозиториев; это не полная off-site копия платформы.

🇬🇧 The existing drill checks restored files on the same Jetson, one newest gzip
dump and nonempty Nextcloud data. It does not import both databases or start apps.
Off-device password access, OS recovery and full RTO remain untested. August 9 SQL
import evidence is historical. Successful S3 trials are not a full off-site backup.

### Следующее полноценное учение / Next full recovery exercise

🇷🇺 Владелец подтвердил 2026-10-09: отдельного стенда пока нет. До его подготовки
выполняются только подготовка сценария и проверка предпосылок. Изолированный импорт
БД на рабочем компьютере может закрыть часть проверки, но не bare-metal DR Jetson.

🇬🇧 Owner confirmed on 2026-10-09 that no separate recovery target is available.
Prepare the procedure and check prerequisites first. Isolated database imports on
the workstation can validate part of recovery, not Jetson bare-metal DR.

1. Подготовить отдельный ARM64-стенд или запасную загрузочную карту Jetson.
   [SD bootstrap](../01A_JETSON_SD_BOOTSTRAP.md) — основа, но не доказательство DR.
   Проверить образы и пересборку локальных компонентов на выбранном стенде.
2. Получить пароль restic из независимого хранилища; проверить репозиторий и
   свежесть обоих дампов. Секреты и семейные данные не передавать внешним LLM.
3. Восстановить конфигурации, Nextcloud и библиотеку Immich в отдельные volumes;
   импортировать обе БД в отдельные экземпляры PostgreSQL.
4. Запустить изолированные приложения без внешних интеграций. Проверить вход,
   открытие документов и фото, соответствие записей БД файлам, права и автозапуск.
5. Замерить RPO восстановленных данных и RTO до доступности приложений.
   Цели 24 часа и 2–4 часа не считать достигнутыми заранее.

🇬🇧 Use an isolated ARM64 target and independently retrieved encryption keys.
Restore data into separate storage and PostgreSQL instances, validate applications,
data consistency and restart behavior, then measure RPO/RTO.

🇷🇺 Откат: рабочие тома и службы не изменяются; при ошибке остановить только стенд.
Очистка стенда — отдельный согласованный шаг. Потеря дома требует полной проверенной
копии вне дома, а не только четырёх конфигурационных файлов.

🇬🇧 Leave production untouched; stop only the test environment on failure.
Authorize cleanup separately. Whole-site loss requires a verified full off-site copy.

---

## Архитектура бэкапа / Backup Architecture

🇷🇺 Компонент, метод бэкапа, расположение и расписание — по каждой строке.

🇬🇧 Component, backup method, location, and schedule — per row.

| Компонент / Component | Метод бэкапа / Backup method | Расположение / Location | Расписание / Schedule |
|---|---|---|---|
| Nextcloud DB (PostgreSQL) | pg_dump via docker exec | /mnt/storage/backups/database-dumps/ | Daily (nas_jetson_nano-backup.timer) |
| Immich DB (PostgreSQL) | pg_dump via docker exec | /mnt/storage/backups/database-dumps/ | Daily (nas_jetson_nano-backup.timer) |
| Media files | rsync (planned) | /mnt/storage/backups/ | Manual |
| Off-site (restic) | NOT YET CONFIGURED | VPS /opt/nas_jetson_nano/backups | Planned |

---

## Тестовые скрипты / Test Scripts

### restore_test.sh

```bash
# Full test: create test file, dry-run rsync, restore to temp, diff check
tests/backup/restore_test.sh \
  --source /mnt/storage/backups/database-dumps \
  --restore-dir /tmp/nas_jetson_nano-restore-test-$(date +%Y%m%d)

# With output report
tests/backup/restore_test.sh \
  --source /mnt/storage/backups/database-dumps \
  --restore-dir /tmp/nas_jetson_nano-restore-test \
  --output /tmp/backup-report.md
```

---

## Процедуры ручного тестирования / Manual Test Procedures

### T5.1: Проверка наличия дампа БД / Check DB Dump Exists

```bash
ls -lh /mnt/storage/backups/database-dumps/nextcloud_*.sql.gz | tail -3
ls -lh /mnt/storage/backups/database-dumps/immich_*.sql.gz | tail -3
```

🇷🇺 Ожидается: файлы существуют, датированы последними 7 днями.

🇬🇧 Expected: Files exist, dated within last 7 days.

### T5.2: Проверка, что дамп не пуст / Check Dump Non-Empty

```bash
DUMP=$(ls -t /mnt/storage/backups/database-dumps/nextcloud_*.sql.gz | head -1)
ls -lh "$DUMP"
gzip -t "$DUMP" && echo "GZIP OK"
```

🇷🇺 Ожидается: файл > 10 КБ, проверка целостности gzip проходит.

🇬🇧 Expected: File > 10KB, gzip integrity check passes.

### T5.3: Сухой прогон rsync / rsync Dry-Run

```bash
rsync -avz --dry-run \
  /mnt/storage/backups/database-dumps/ \
  /tmp/nas_jetson_nano-restore-dry-run/
```

🇷🇺 Ожидается: rsync перечисляет файлы для копирования, код выхода 0.

🇬🇧 Expected: rsync lists files to copy, exit code 0.

### T5.4: Восстановление и сравнение / Restore and Diff

```bash
RESTORE_DIR=$(mktemp -d /tmp/nas_jetson_nano-restore-XXXX)
rsync -avz /mnt/storage/backups/database-dumps/ "$RESTORE_DIR/"
diff <(ls -1 /mnt/storage/backups/database-dumps/) <(ls -1 "$RESTORE_DIR/")
echo "Restore check: $?"
rm -rf "$RESTORE_DIR"
```

🇷🇺 Ожидается: diff возвращает 0 (списки файлов идентичны).

🇬🇧 Expected: diff returns 0 (identical file lists).

### T5.5: Ручной запуск дампа БД / DB Dump Manual Trigger

```bash
# Run backup manually to verify it works
sudo bash scripts/backup/backup_databases.sh
```

🇷🇺 Ожидается: выход 0, «Database backup finished -- errors: 0»

🇬🇧 Expected: Exit 0, "Database backup finished -- errors: 0"

---

## Ожидаемые результаты / Expected Results

| Проверка / Check | Ожидается / Expected | Фактически / Actual | Прошло? / Pass? |
|---|---|---|---|
| Nextcloud dump exists | yes (< 7 days) | | |
| Nextcloud dump size | > 10KB | | |
| Immich dump exists | yes (< 7 days) | | |
| Immich dump size | > 10KB | | |
| gzip integrity | PASS | | |
| rsync dry-run | exit 0 | | |
| Restore + diff | identical | | |
| Manual dump trigger | exit 0 | | |

---

## Известные ограничения / Known Limitations

🇷🇺

- Off-site бэкапа нет (restic на VPS запланирован, но не настроен)
- Медиафайлы (фото, документы) пока НЕ бэкапятся — только дампы БД
- Ротация бэкапов хранит последние 7 дней (BACKUP_KEEP_LAST=7)
- Если SSD выйдет из строя между бэкапами, все данные с момента последнего дампа под риском

🇬🇧

- No off-site backup (restic to VPS is planned but not configured)
- Media files (photos, documents) are NOT backed up yet -- only DB dumps
- Backup rotation keeps last 7 days (BACKUP_KEEP_LAST=7)
- If SSD fails between backups, all data since last dump is at risk

---

## Процедура восстановления (сокращённо) / Recovery Procedure (abbreviated)

🇷🇺

1. Физически: переподключить SSD, запустить цикл preboot
2. Смонтировать: `sudo bash scripts/storage/storage_preflight.sh`
3. Запустить Docker: `sudo systemctl start docker`
4. Запустить контейнеры: `docker compose up -d` для каждого compose-файла
5. При необходимости восстановить БД (см. команду ниже)
6. Проверить Nextcloud: `curl -sf http://localhost:8080/status.php`

🇬🇧

1. Physical: reconnect SSD, run preboot cycle
2. Mount: `sudo bash scripts/storage/storage_preflight.sh`
3. Start Docker: `sudo systemctl start docker`
4. Start containers: `docker compose up -d` for each compose file
5. Restore DB if needed:
   ```bash
   DUMP=/mnt/storage/backups/database-dumps/nextcloud_LATEST.sql.gz
   zcat "$DUMP" | docker exec -i homecloud_nextcloud_db psql -U nextcloud nextcloud
   ```
6. Verify Nextcloud: `curl -sf http://localhost:8080/status.php`
