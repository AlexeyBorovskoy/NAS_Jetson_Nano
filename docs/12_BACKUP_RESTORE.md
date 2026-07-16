# 12. Backup / Restore

## 1. Правило / Rule

🇷🇺 Хранение фото на одном USB HDD не является резервным копированием. Минимально нужен второй носитель или удалённая копия. На 2026-06-27 backup работает в fail-closed режиме: если `/mnt/storage` не является отдельным mountpoint или указывает на microSD, дампы БД не создаются.

🇬🇧 Storing photos on a single USB HDD is not a backup. At minimum, a second medium or remote copy is required. As of 2026-06-27, backup runs in fail-closed mode: if `/mnt/storage` is not a separate mountpoint or points to microSD, DB dumps are not created.

## 2. Объекты backup / What is backed up

| Объект / Object | Метод / Method |
|---|---|
| Nextcloud data | restic/borg |
| Nextcloud DB | pg_dump |
| Immich library | restic/borg |
| Immich DB | pg_dump |
| Docker compose/config | git + restic |
| `.env` | зашифрованный backup / encrypted backup, outside public Git |

## 3. Пример restic / restic example

🇷🇺 Перед любым backup запустить preflight:
🇬🇧 Run preflight before any backup:

```bash
cd ~/nas_jetson_nano
sudo bash scripts/storage/storage_preflight.sh
```

```bash
export RESTIC_REPOSITORY=/mnt/storage/backups/restic-repo
export RESTIC_PASSWORD_FILE=/root/.config/homecloud/restic-password
restic init
restic backup /mnt/storage/nextcloud /mnt/storage/immich /mnt/storage/backups/database-dumps
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
```

## 4. Проверка восстановления / Restore verification

🇷🇺 Минимум раз в месяц:
🇬🇧 At least once a month:

```bash
restic snapshots
restic restore latest --target /tmp/homecloud-restore-test
ls -la /tmp/homecloud-restore-test
```

## 5. RPO/RTO

| Параметр / Parameter | Цель Stage 1 / Stage 1 target |
|---|---:|
| RPO | 24 часа / 24 hours |
| RTO | 2–4 часа вручную / 2–4 hours manual |
| Проверка restore / Restore check | ежемесячно / monthly |

## 6. USB Storage Incident 2026-06-23

🇷🇺 Если preflight падает из-за отсутствующего `/mnt/storage`, `error -71` или read-only remount, backup/restore работы останавливаются до стабилизации накопителя. Порядок восстановления: [docs/plans/STORAGE_INCIDENT_2026-06-23.md](plans/STORAGE_INCIDENT_2026-06-23.md).

🇬🇧 If preflight fails due to missing `/mnt/storage`, `error -71`, or read-only remount, backup/restore operations stop until the storage is stable. Recovery procedure: [docs/plans/STORAGE_INCIDENT_2026-06-23.md](plans/STORAGE_INCIDENT_2026-06-23.md).
