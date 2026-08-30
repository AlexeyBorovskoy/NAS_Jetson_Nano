# Тесты Backup/Restore / Backup and Restore Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

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
