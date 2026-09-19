# Выкат этапа B на Jetson / Stage B device rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; при расхождении — стоп.
> 🇬🇧 Owner-triggered only. EN summary at the end.
>
> План: `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` §4, B1 (бэкап конфигурации), B2 (изоляция копий),
> B6 (учения). B3 (S3) — отдельно, когда появится tenant_id. Методика: `docs/12_BACKUP_RESTORE.md` §2b.

**Простой для семьи:** ~1 мин — пересоздаются контейнеры Nextcloud и Samba (шаг 7).

## 1. Правило №13 — ДО
Как в `DEPLOY_STAGE_A_2026-09.md` §1: StartedAt `amnezia-*`, число пиров, публичные порты.

## 2. Базовая линия
```bash
cd ~/nasa && git status --short | grep -v "\.bak"; git rev-parse --short HEAD
docker ps --format "{{.Names}} {{.Status}}" | sort
ls -lt /mnt/storage/backups/database-dumps | sed -n 2,3p
df -h /mnt/hdd2tb /mnt/storage | tail -2
```

## 3. Код
```bash
git pull --ff-only && git rev-parse --short HEAD
python3 tests/unit/test_backup_isolation.py && python3 tests/unit/test_config_backup.py
```

## 4. restic 0.19.1
```bash
curl -sI -m 10 https://github.com | head -1           # доступен ли GitHub с Jetson
sudo bash scripts/backup/install_restic.sh            # сам скачает и сверит SHA-256
# нет GitHub: скачать restic_0.19.1_linux_arm64.bz2 на станции, scp в /tmp, затем
# sudo bash scripts/backup/install_restic.sh /tmp/restic_0.19.1_linux_arm64.bz2
restic version                                          # restic 0.19.1
```

## 5. Цель, пароль, таймеры
```bash
sudo bash scripts/backup/setup_config_backup.sh
```
🔴 **Сразу:** пароль `/root/.config/nas-backup/hdd.pass` → менеджер паролей владельца
(Windows Credential Manager, как пароль restic на Vostro 24.08). **В чат и в git не выводить.**
Без него бэкап не расшифровать в день смерти SD-карты.

## 6. Первый бэкап и учения
```bash
bash scripts/backup/config_backup.sh --plan
sudo systemctl start nas_jetson_nano-config-backup.service
systemctl show -p Result nas_jetson_nano-config-backup.service     # success
journalctl -u nas_jetson_nano-config-backup -n 15 --no-pager
sudo bash -c 'set -a; . /root/.config/nas-backup/targets/hdd.env; set +a; restic snapshots --tag nas-config; restic stats latest'
sudo systemctl start nas_jetson_nano-restore-drill.service
journalctl -u nas_jetson_nano-restore-drill -n 5 --no-pager         # DRILL OK (hdd)
```

## 7. Изоляция копий (B2) — пересоздание Nextcloud и Samba
```bash
docker compose -f docker/compose/docker-compose.nextcloud.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.samba.yml     --env-file config/.env up -d
# проверка без записи на семейный диск:
for c in homecloud_nextcloud homecloud_samba; do
  docker exec $c grep -E " /mnt/hdd2tb(/backups)? " /proc/mounts | awk '{print "'$c'", $2, $4}' | cut -c1-80
done   # /mnt/hdd2tb — rw…, /mnt/hdd2tb/backups — ro…
curl -s -o /dev/null -w "nextcloud %{http_code}\n" http://127.0.0.1:8080/status.php
docker exec -u www-data homecloud_nextcloud php occ status | grep -E "installed|maintenance"
```
Smoke: с Windows открыть `\\192.168.0.50\hdd2tb\backups` — читается; попытка удалить файл — отказ.

## 8. Правило №13 — ПОСЛЕ
Повторить §1: без изменений.

## 9. Откат
| Что | Команда |
|---|---|
| таймеры | `sudo systemctl disable --now nas_jetson_nano-config-backup.timer nas_jetson_nano-restore-drill.timer` |
| изоляция | `git checkout <prev> -- docker/compose/docker-compose.{nextcloud,samba}.yml` → `up -d` обоих |
| restic | `sudo rm /usr/local/bin/restic` (репозиторий и пароль не удалять без решения владельца) |

## EN summary
Pull the code and run the on-device tests. Install pinned restic 0.19.1 with SHA-256 verification, then
run `setup_config_backup.sh`: it creates the password, the HDD target, the repository and the timers.
Move the repository password to the owner's password manager immediately and never print it. Run the
first backup and a restore drill (`DRILL OK`). Recreate Nextcloud and Samba to apply the read-only
`backups/` overlay (about 1 minute of downtime) and verify it through `/proc/mounts` without writing to
the archive disk. Check the VPS state before and after.
