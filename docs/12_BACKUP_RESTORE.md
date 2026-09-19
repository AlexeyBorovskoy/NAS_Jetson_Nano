# 12. Backup / Restore

> 🇷🇺 **Статус 2026-09-07 (ADR-0009):**  
> - L0 live: SSD.  
> - L1 on-site Immich→HDD: скрипт + timer **в git** (`scripts/backup/immich_hdd_second_copy.sh`,  
>   `systemd/nas_jetson_nano-immich-hdd-copy.*`) — **на устройство не выкатано** до «деплой».  
> - L2 off-site: канон → Cloud.ru S3 (позже). Vostro restic DB (2026-08-24) = **legacy**, не обязателен.  
> Канон: [`plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md).
>
> 🇬🇧 **Status 2026-09-07:** L1 Immich→HDD units in git, not installed on device until deploy.  
> L2 off-site target is Cloud.ru S3; Vostro is legacy.

## 0. 🔴 Главное правило проверки / The one check that matters

🇷🇺 **Не верить статусу systemd-юнита. Проверять свежесть файлов.**

🇬🇧 **Never trust the systemd unit status. Check file freshness.**

```bash
ls -lt /mnt/storage/backups/database-dumps/ | head -5
```

**Почему.** С 2026-07-24 по 2026-08-09 бэкапы не создавались **16 дней**, при том что
`systemctl status nasa-backup` показывал `Result=success` каждую ночь. Причина: в
`config/.env` строка `TALK_BOT_DISPLAY_NAME=NAS Bot` **без кавычек**. Шелл прочитал её как
`VAR=NAS` + команду `Bot` → `Bot: command not found` (код 127) → `set -euo pipefail` в
`scripts/backup/backup_databases.sh` убил скрипт до первого `pg_dump`.

**Радиус поражения был шире бэкапов.** Тот же `source config/.env` под `set -e` делают:

| Скрипт / юнит | Что перестало работать |
|---|---|
| `nasa-backup.service` | ночные дампы БД |
| `scripts/storage/storage_preflight.sh` | защитный барьер перед стартом Nextcloud/Immich/бэкапа |
| `nasa-ssd-recovery.service` | **автовосстановление при hotplug SSD** |
| `jetson-nas-health.service` | проверка storage/SMART |

То есть страховочная сетка «переткни кабель — система поднимется сама» была мертва 16 дней
и при реальном отвале SSD не сработала бы.

**Правило на будущее:** любое значение с пробелом в `config/.env` — обязательно в кавычках.
Быстрая проверка целостности файла:

```bash
( set -euo pipefail; source ~/nasa/config/.env >/dev/null ) && echo OK || echo BROKEN
```

⚠️ Отдельно: внутренний бэкап Immich (`/mnt/storage/immich/library/backups/`) всё это время
**работал** — он делается самим Immich и от `.env` не зависит. У Nextcloud такого дублёра нет,
его БД не бэкапилась вообще.

## 1. Правило / Rule

🇷🇺 Хранение фото на одном USB HDD не является резервным копированием. Минимально нужен второй носитель или удалённая копия. На 2026-06-27 backup работает в fail-closed режиме: если `/mnt/storage` не является отдельным mountpoint или указывает на microSD, дампы БД не создаются.

🇬🇧 Storing photos on a single USB HDD is not a backup. At minimum, a second medium or remote copy is required. As of 2026-06-27, backup runs in fail-closed mode: if `/mnt/storage` is not a separate mountpoint or points to microSD, DB dumps are not created.

## 2. Объекты backup / What is backed up

| Объект / Object | Метод / Method | Layer |
|---|---|---|
| Nextcloud DB | pg_dump (`nasa-backup.timer`) | L1b SSD |
| Immich DB | pg_dump | L1b SSD |
| Immich library | `immich_hdd_second_copy.sh` → `/mnt/hdd2tb/backups/immich` | L1 on-site |
| **`.env`, `config.php` Nextcloud, файлы Nextcloud, пользователи Samba, конфиги мониторинга, дампы** | `config_backup.sh` → restic (шифр.) `/mnt/hdd2tb/backups/restic-config`, ежедневно 03:40, хранение 7д/4н/6м | **L1c on-site** (этап B1, 2026-09-19) |
| то же (набор L1c) | тот же скрипт, цель `s3.env` → Cloud.ru S3 | L2 off-site (B3, ждёт tenant_id) |
| Immich library off-site | решение владельца D2 | L2 — нет |
| Docker compose/config | git (+ GitVerse mirror) | L3 |

> 🔴 **Пароль restic-репозитория** (`/root/.config/nas-backup/hdd.pass`) обязан храниться **и вне
> устройства** (менеджер паролей). Без него снапшоты не расшифровать — бэкап `.env` бесполезен
> ровно в день смерти SD-карты. 🇬🇧 Keep the repository password off-device too.

### 2b. Конфигурация и файлы Nextcloud (restic) / Config and Nextcloud files

```bash
sudo bash scripts/backup/install_restic.sh            # restic 0.19.1, SHA-256 закреплён
sudo bash scripts/backup/setup_config_backup.sh       # пароль, цель hdd, init, таймеры
bash scripts/backup/config_backup.sh --plan           # что именно копируется (из раскладки хоста)
sudo systemctl start nas_jetson_nano-config-backup    # прогон; штамп $NAS_STATE_DIR/config-backup-hdd.stamp
sudo systemctl start nas_jetson_nano-restore-drill    # учения: распаковка на SSD и проверка содержимого
```

Отказ **до** restic, если не смонтирован SSD/HDD или нет обязательного источника (тишина ≠ успех).
Учения (`restore_drill.sh`, ежемесячно) проверяют содержимое: `.env` читается под `set -e`,
`config.php` с `instanceid`, свежий дамп проходит `gzip -t`, файлы Nextcloud не пусты.

**Восстановление вручную:**
```bash
sudo -i
set -a; source /root/.config/nas-backup/targets/hdd.env; set +a
restic snapshots --tag nas-config
restic restore latest --tag nas-config --target /mnt/storage/restore-$(date +%F) --include /home/admin/nasa/config/.env
```

**Копии на HDD — только чтение для людей (B2):** в Samba и Nextcloud `backups/` смонтирован
вложенным ro-bind поверх rw-диска. Достать файл можно, изменить или удалить — нет.

### 2a. Immich → HDD (ADR-0009)

```bash
# Dry-run on Jetson after deploy of script:
DRY_RUN=1 bash /home/admin/nasa/scripts/backup/immich_hdd_second_copy.sh

# Install timer (once):
sudo cp systemd/nas_jetson_nano-immich-hdd-copy.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nas_jetson_nano-immich-hdd-copy.timer
```

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

### 4а. Проверка дампов БД — безопасная методика (выполнена 2026-08-09)

🇷🇺 Дамп можно накатить **без риска для прода**, если лить его в **новую** БД в том же
контейнере и удалить её после. Прод не затрагивается вообще.

🇬🇧 A dump can be replayed **without touching production**: load it into a **new** database
inside the same container, verify, then drop it.

```bash
# 1. Создать временную БД
docker exec homecloud_nextcloud_db psql -U nextcloud -d postgres \
  -c "CREATE DATABASE restore_test_tmp;"

# 2. Накатить дамп
gunzip -c /mnt/storage/backups/database-dumps/nextcloud_YYYYMMDD_HHMMSS.sql.gz \
  | docker exec -i homecloud_nextcloud_db psql -U nextcloud -d restore_test_tmp

# 3. Сверить счётчики с живой БД
docker exec homecloud_nextcloud_db psql -U nextcloud -d restore_test_tmp -tAc \
  "select (select count(*) from oc_users), (select count(*) from oc_filecache);"
docker exec homecloud_nextcloud_db psql -U nextcloud -d nextcloud -tAc \
  "select (select count(*) from oc_users), (select count(*) from oc_filecache);"

# 4. Обязательно удалить
docker exec homecloud_nextcloud_db psql -U nextcloud -d postgres \
  -c "DROP DATABASE restore_test_tmp;"
```

**Результат проверки 2026-08-09:**

| БД | Таблиц | Сверка с live | Ошибок при накате |
|---|---|---|---|
| Nextcloud | 153 | `oc_users` 5 = 5, `oc_filecache` 403 = 403 | 0 |
| Immich | 61 | `asset` 7098 = 7098, `album` 23 = 23 | 0 |

Для Immich та же процедура, но контейнер `homecloud_immich_db` и пользователь `immich`.

## 5. RPO/RTO

| Параметр / Parameter | Цель Stage 1 / Stage 1 target |
|---|---:|
| RPO | 24 часа / 24 hours |
| RTO | 2–4 часа вручную / 2–4 hours manual |
| Проверка restore / Restore check | ежемесячно / monthly |

## 6. USB Storage Incident 2026-06-23

🇷🇺 Если preflight падает из-за отсутствующего `/mnt/storage`, `error -71` или read-only remount, backup/restore работы останавливаются до стабилизации накопителя. Порядок восстановления: [docs/plans/STORAGE_INCIDENT_2026-06-23.md](plans/STORAGE_INCIDENT_2026-06-23.md).

🇬🇧 If preflight fails due to missing `/mnt/storage`, `error -71`, or read-only remount, backup/restore operations stop until the storage is stable. Recovery procedure: [docs/plans/STORAGE_INCIDENT_2026-06-23.md](plans/STORAGE_INCIDENT_2026-06-23.md).
