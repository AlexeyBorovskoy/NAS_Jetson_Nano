# Тесты Backup/Restore / Backup and Restore Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Backup Architecture

| Component | Backup method | Location | Schedule |
|---|---|---|---|
| Nextcloud DB (PostgreSQL) | pg_dump via docker exec | /mnt/storage/backups/database-dumps/ | Daily (nas_jetson_nano-backup.timer) |
| Immich DB (PostgreSQL) | pg_dump via docker exec | /mnt/storage/backups/database-dumps/ | Daily (nas_jetson_nano-backup.timer) |
| Media files | rsync (planned) | /mnt/storage/backups/ | Manual |
| Off-site (restic) | NOT YET CONFIGURED | VPS /opt/nas_jetson_nano/backups | Planned |

---

## Test Scripts

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

## Manual Test Procedures

### T5.1: Check DB Dump Exists

```bash
ls -lh /mnt/storage/backups/database-dumps/nextcloud_*.sql.gz | tail -3
ls -lh /mnt/storage/backups/database-dumps/immich_*.sql.gz | tail -3
```

Expected: Files exist, dated within last 7 days.

### T5.2: Check Dump Non-Empty

```bash
DUMP=$(ls -t /mnt/storage/backups/database-dumps/nextcloud_*.sql.gz | head -1)
ls -lh "$DUMP"
gzip -t "$DUMP" && echo "GZIP OK"
```

Expected: File > 10KB, gzip integrity check passes.

### T5.3: rsync Dry-Run

```bash
rsync -avz --dry-run \
  /mnt/storage/backups/database-dumps/ \
  /tmp/nas_jetson_nano-restore-dry-run/
```

Expected: rsync lists files to copy, exit code 0.

### T5.4: Restore and Diff

```bash
RESTORE_DIR=$(mktemp -d /tmp/nas_jetson_nano-restore-XXXX)
rsync -avz /mnt/storage/backups/database-dumps/ "$RESTORE_DIR/"
diff <(ls -1 /mnt/storage/backups/database-dumps/) <(ls -1 "$RESTORE_DIR/")
echo "Restore check: $?"
rm -rf "$RESTORE_DIR"
```

Expected: diff returns 0 (identical file lists).

### T5.5: DB Dump Manual Trigger

```bash
# Run backup manually to verify it works
sudo bash scripts/backup/backup_databases.sh
```

Expected: Exit 0, "Database backup finished -- errors: 0"

---

## Expected Results

| Check | Expected | Actual | Pass? |
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

## Known Limitations

- No off-site backup (restic to VPS is planned but not configured)
- Media files (photos, documents) are NOT backed up yet -- only DB dumps
- Backup rotation keeps last 7 days (BACKUP_KEEP_LAST=7)
- If SSD fails between backups, all data since last dump is at risk

---

## Recovery Procedure (abbreviated)

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
