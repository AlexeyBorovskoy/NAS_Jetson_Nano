# 13. Monitoring / Runbook

> 🇷🇺 Состояние на 2026-06-27: **мониторинг-стек развёрнут и работает**.
> 🇬🇧 Status 2026-06-27: **monitoring stack is deployed and operational**.
>
> Подробный анализ инструментов: `docs/17_MONITORING_OBSERVABILITY.md`.  
> Логирование и API: `docs/21_LOGGING_API.md`.  
> Аудит надёжности: `docs/22_AUDIT_RESILIENCE.md`.

---

## 1. Быстрая проверка состояния кластера / Quick Cluster Health Check

```bash
# Все контейнеры с healthcheck-статусом:
docker ps --format "{{.Names}}\t{{.Status}}"

# goss — 34 теста (порты, сервисы, файлы, HTTP):
goss -g tests/goss/goss.yaml validate --format tap

# API-статус через nas_jetson_nano-api:
curl -sf http://localhost:8099/v1/containers | python3 -m json.tool

# Storage preflight перед запуском Nextcloud/Immich/backup:
cd ~/nas_jetson_nano
sudo bash scripts/storage/storage_preflight.sh
```

## 2. Ежедневные проверки / Daily Checks

```bash
df -h /mnt/storage          # место на диске данных
mountpoint /mnt/storage     # /mnt/storage обязан быть отдельным mountpoint
free -h                     # RAM (предупреждение < 300 MB)
docker ps --format "{{.Names}}\t{{.Status}}"  # healthcheck-статусы
sudo dmesg | grep -i -E "error|reset|fail|i/o" | tail -20
```

## 3. Проверка дисков / Disk Check

### 3.1. 🔴 SMART недоступен — и это не чинится конфигом

🇷🇺 `smartd.service` **отключён намеренно** (`systemctl disable smartd`, 2026-08-09). Причина
структурная: kernel-quirk `152d:a583:u`, нужный для стабильности SSD, переводит мост JMS583 в
режим **usb-storage BOT**, а BOT не пропускает ATA/SCSI passthrough, на котором держится SMART.

🇬🇧 `smartd` is disabled **by design**: the UAS quirk that keeps the SSD stable forces
usb-storage BOT mode, which blocks the ATA/SCSI passthrough SMART depends on.

Перебрано 2026-08-09 — не работает **ничего**:

| Режим | Результат |
|---|---|
| `-d sat`, `-d sat,12`, `-d sat,16` | `unsupported scsi opcode` / `unsupported field in scsi command` |
| `-d usbjmicron`, `,0`, `,x` | `unsupported field in scsi command` |
| `-d sat -T permissive -A` | `Read Device Identity failed`, атрибутов нет |
| `-d scsi -i` | ✅ только паспорт: `JMicron Tech`, S/N, 250 GB |
| `-d scsi -H` | ✅ `SMART Health Status: OK` (разово) |
| `-d scsi -s on` | ❌ `unable to fetch IEC (SMART) mode page` |

Последнее и убивает идею: `smartd` требует включённой IEC mode page, а мост её не отдаёт →
`IE (SMART) not enabled, skip device`. Разовый `-H` проходит, непрерывный мониторинг — нет.

**Quirk снимать нельзя** — без него сыпались USB-ошибки и диск отваливался с шины.
Пересмотреть только при обновлении `smartmontools` (сейчас 6.6 от 2016 года).

### 3.2. Чем закрыт мониторинг здоровья вместо SMART

| Механизм | Период | Что проверяет |
|---|---|---|
| `nasa-jms583-health.timer` | ежечасно | драйвер, активность quirk, USB-ошибки; пишет `errors=N warnings=N` |
| `nasa-usb-monitor.service` | реальное время | следит за dmesg (`error -71`, stream errors) → Telegram |
| `jetson-nas-health.timer` | каждые 6 ч | storage/mountpoint |

```bash
# Ежечасный отчёт о здоровье моста
tail -20 /var/log/nasa-monitor/jms583-health.log

# Разовый паспорт диска (работает даже в BOT-режиме)
sudo smartctl -d scsi -i /dev/sda
sudo smartctl -d scsi -H /dev/sda

# USB-ошибки с момента загрузки — здоровая система даёт 0
dmesg -T | grep -Eic "error -71|uas_eh|I/O error|usb disconnect"
```

## 4. Веб-интерфейсы мониторинга / Monitoring Web UIs

| Инструмент / Tool | URL | Назначение / Purpose |
|---|---|---|
| nas_jetson_nano-api Swagger | `http://192.168.0.50:8099/docs` | Метрики, логи, контейнеры, report/now |
| Netdata | `http://192.168.0.50:19999` | CPU, RAM, Disk, Docker, темп Jetson |
| Uptime Kuma | `http://192.168.0.50:3001` | HTTP uptime, Telegram-уведомления |
| Portainer | `http://192.168.0.50:9000` | Docker management UI |

## 5. Управление сервисами / Service Management

```bash
# Запуск стека (если контейнер упал и не поднялся сам):
cd ~/nas_jetson_nano
sudo bash scripts/storage/storage_preflight.sh
docker compose -f docker/compose/docker-compose.nextcloud.yml  --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.immich.yml     --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.llm-gateway.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.monitoring.yml  --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml    --env-file config/.env up -d

# Остановить один стек:
docker compose -f docker/compose/docker-compose.monitoring.yml --env-file config/.env down
```

## 6. Если Nextcloud не открывается / If Nextcloud is unreachable

1. Проверить healthcheck-статус:

```bash
docker inspect homecloud_nextcloud --format "{{.State.Health.Status}}"
```

2. Проверить зависимости (DB + Redis должны быть `healthy`):

```bash
docker ps --format "{{.Names}}\t{{.Status}}" | grep -E "nextcloud"
```

3. Проверить логи:

```bash
docker logs homecloud_nextcloud --tail=50
docker logs homecloud_nextcloud_db --tail=20
```

4. Проверить диск и preflight:

```bash
df -h /mnt/storage
mountpoint /mnt/storage
cd ~/nas_jetson_nano && sudo bash scripts/storage/storage_preflight.sh
```

## 7. Если Immich тормозит / If Immich is slow

1. Проверить RAM и CPU:

```bash
docker stats --no-stream | grep immich
```

2. Убедиться, что ML отключён (`IMMICH_DISABLE_MACHINE_LEARNING=true` в compose).
3. Остановить массовый импорт фото.
4. Проверить PostgreSQL:

```bash
docker logs homecloud_immich_db --tail=30
```

## 8. Если USB storage отваливается / If USB storage drops

Симптомы: `/mnt/storage` не является mountpoint, `lsblk` не показывает диск,
Nextcloud отдаёт `503` / `data directory is invalid`, в `journalctl -k`
видны `error -71`, `unable to enumerate USB device`, `EXT4-fs error`,
`Aborting journal` или `Remounting filesystem read-only`.

**Сначала только read-only диагностика:**

```bash
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,RO
blkid
mountpoint /mnt/storage || echo "/mnt/storage is not mounted"
findmnt -T /mnt/storage -o TARGET,SOURCE,FSTYPE,OPTIONS
journalctl -k -n 120 --no-pager | grep -i -E "usb|sda|sdb|ext4|I/O error|error -71|enumerate|read-only"
cd ~/nas_jetson_nano && sudo bash scripts/storage/storage_preflight.sh
```

**Нельзя делать до стабилизации USB:**

- не запускать `docker compose up -d` для Nextcloud/Immich;
- не создавать `.ncdata` вручную в ложном `/mnt/storage` на microSD;
- не запускать `fsck` на смонтированном разделе;
- не использовать `docker compose down -v`;
- не писать backup в `/mnt/storage`, если preflight не прошёл.

**Физический порядок восстановления:**

1. Проверить питание, кабель, USB-порт и USB-SATA/NVMe адаптер.
2. Предпочтительно подключить накопитель через powered USB hub или корпус с
   отдельным питанием.
3. Дождаться, что `lsblk` стабильно показывает диск и нужный UUID из `/etc/fstab`.
4. Только после этого монтировать `/mnt/storage` и запускать storage-backed
   контейнеры.

**После стабильного переподключения:**

```bash
cd ~/nas_jetson_nano
sudo bash scripts/storage/storage_preflight.sh

# Установить mount-unit, если он ещё не установлен.
bash scripts/storage/install_mount_service.sh

# Запуск mount-unit только после проверки lsblk/blkid.
sudo systemctl start jetson-nas-mount.service
sudo bash scripts/storage/storage_preflight.sh

# После успешного preflight можно запускать storage-backed сервисы.
docker compose -f docker/compose/docker-compose.immich.yml --env-file config/.env up -d
```

Если накопитель снова отваливается с `error -71`, это аппаратная проблема
USB-цепочки. Продолжать эксплуатацию Nextcloud/Immich на таком накопителе нельзя.

**Текущий итог инцидента 2026-06-23:** SSD снова смонтирован в `/mnt/storage`,
`e2fsck -f -n` и `storage_preflight.sh` чистые, fresh DB dumps созданы. Новых
kernel storage ошибок после controlled start Nextcloud не наблюдалось.
Nextcloud снова `running/healthy`, `/status.php` возвращает `HTTP 200`.
Reboot/autorecovery test прошёл: tunnel, storage, Docker containers, HTTP
endpoints и `jetson-nas-health.timer` восстановились автоматически.

## 9. Telegram ежедневный отчёт / Telegram Daily Report

```bash
# Статус таймера:
systemctl status nas_jetson_nano-daily-report-telegram.timer

# Отправить немедленно (тест):
sudo /usr/local/sbin/nas_jetson_nano-send-report-telegram.sh

# Логи последней отправки:
cat /var/log/nas_jetson_nano-monitor/last-report.txt
cat /var/log/nas_jetson_nano-monitor/last-telegram-send.json

# Следующий запуск:
systemctl list-timers nas_jetson_nano-daily-report-telegram.timer
```

## 10. Что смотреть в Netdata / What to watch in Netdata

- **System → CPU** — при 19%+ постоянно: возможно утечка или ML в Immich
- **System → RAM** — при < 300 MB свободно: смотреть `docker stats --no-stream`
- **Disk Space → /mnt/storage** — алерт при > 80%
- **Docker → Containers** — состояние всех контейнеров
- **Temperature** — тепловые зоны Jetson; алерт при > 85°C

## 11. Что делать при уведомлении / What to do when Uptime Kuma alerts

| Уведомление / Alert | Действие / Action |
|---|---|
| Nextcloud недоступен / unreachable | Section 6 of this runbook |
| Immich недоступен / unreachable | Section 7 of this runbook |
| LLM Gateway недоступен / unreachable | `docker logs homecloud_llm_gateway --tail=50` |
| nas_jetson_nano-api недоступен / unreachable | `docker logs homecloud_nas_jetson_nano_api --tail=50` |

## 12. Автоматический бэкап БД / Automated DB Backup — timer setup

Скрипт `scripts/backup/backup_databases.sh` уже реализован (pg_dump + gzip + ротация 7 дней).
Таймер запускает его каждый день в 03:00 (±15 мин).
Скрипт работает fail-closed: если `${STORAGE_ROOT}` не является отдельным
mountpoint или указывает на microSD, backup не создаётся, чтобы не писать дампы
в ложный `/mnt/storage`.

```bash
# Установить на Jetson (один раз, из директории проекта):
cd ~/nas_jetson_nano
bash scripts/backup/install_backup_timer.sh

# Проверить статус:
systemctl status nas_jetson_nano-backup.timer
systemctl list-timers nas_jetson_nano-backup.timer

# Запустить немедленно (тест):
sudo systemctl start nas_jetson_nano-backup.service
journalctl -u nas_jetson_nano-backup.service -n 40 --no-pager

# Убедиться, что дампы созданы:
ls -lh /mnt/storage/backups/database-dumps/
```

## 13. Uptime Kuma — начальная настройка / Initial monitor setup

**Первый запуск** → открыть `http://192.168.0.50:3001` и создать admin-аккаунт.

Добавить 5 мониторов (Add New Monitor → HTTP(s)):

| Имя / Name | URL | Интервал / Interval | Expected Status |
|---|---|---|---|
| Nextcloud | `http://192.168.0.50:8080/status.php` | 60 сек | 200 |
| Immich | `http://192.168.0.50:2283/api/server/ping` | 60 сек | 200 |
| LLM Gateway | `http://192.168.0.50:8090/health` | 60 сек | 200 |
| nas_jetson_nano-api | `http://192.168.0.50:8099/healthcheck` | 60 сек | 200 |
| Netdata | `http://192.168.0.50:19999/api/v1/info` | 120 сек | 200 |

**Telegram-уведомления** (Settings → Notifications → Add Notification):
- Type: Telegram
- Bot Token: значение из `TELEGRAM_BOT_TOKEN` (см. `/etc/nas_jetson_nano-monitor/telegram.env` на Jetson)
- Chat ID: значение из `TELEGRAM_CHAT_ID`
- Включить на всех 5 мониторах

## 14. Netdata — Telegram-алерты / Telegram alerts

Конфиг живёт внутри Docker-тома `homecloud_netdata_config` → `/etc/netdata/health_alarm_notify.conf`.

```bash
# 1. Посмотреть текущие Telegram-переменные:
docker exec homecloud_netdata grep -n 'TELEGRAM\|DEFAULT_RECIPIENT' \
  /etc/netdata/health_alarm_notify.conf

# 2. Включить Telegram (поправить три строки):
BOT_TOKEN="YOUR_BOT_TOKEN"   # взять из /etc/nas_jetson_nano-monitor/telegram.env
CHAT_ID="YOUR_CHAT_ID"       # взять из /etc/nas_jetson_nano-monitor/telegram.env

docker exec homecloud_netdata sed -i \
  -e "s|^SEND_TELEGRAM=.*|SEND_TELEGRAM=\"YES\"|" \
  -e "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=\"${BOT_TOKEN}\"|" \
  -e "s|^DEFAULT_RECIPIENT_TELEGRAM=.*|DEFAULT_RECIPIENT_TELEGRAM=\"${CHAT_ID}\"|" \
  /etc/netdata/health_alarm_notify.conf

# 3. Проверить результат:
docker exec homecloud_netdata grep -E 'SEND_TELEGRAM|TELEGRAM_BOT_TOKEN|DEFAULT_RECIPIENT_TELEGRAM' \
  /etc/netdata/health_alarm_notify.conf

# 4. Перезагрузить конфиг (без перезапуска контейнера):
docker exec homecloud_netdata kill -USR2 1

# 5. Тест: отправить тестовый алерт (если поддерживается):
docker exec homecloud_netdata /usr/libexec/netdata/plugins.d/alarm-notify.sh test telegram
```

> **Какие алерты приходят:** CPU > 80%, RAM < 300 MB, Disk > 80%, температура > 85°C,
> контейнер упал. Настроить пороги можно в `/etc/netdata/health.d/` внутри контейнера.

## 15. nas_jetson_nano-api — полезные запросы / Useful API queries

```bash
# Метрики системы (RAM, CPU load, диски, температура):
curl -sf http://localhost:8099/v1/metrics | python3 -m json.tool

# Статус всех контейнеров:
curl -sf http://localhost:8099/v1/containers | python3 -m json.tool

# Последние 50 строк лога (с фильтром уровня):
curl -sf "http://localhost:8099/v1/logs?limit=50&level=ERROR" | python3 -m json.tool

# Отправить Telegram-отчёт вручную через API:
curl -X POST http://localhost:8099/v1/report/now
```
