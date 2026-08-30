# Аудит работоспособности решения — 2026-08-10 / Operational health audit — 2026-08-10

> 🇷🇺 Read-only live-аудит рабочего Jetson Nano и VPS. Метод: SSH ProxyJump через VPS
> (`root@95.163.176.103` → `admin@127.0.0.1:10022`), два скриптовых прохода + проверка VPS.
> Предыдущий отчёт: `SYSTEM_AUDIT_2026-08-01.md`.
>
> 🇬🇧 A read-only live audit of the running Jetson Nano and the VPS. Method: SSH ProxyJump
> through the VPS (`root@95.163.176.103` → `admin@127.0.0.1:10022`), two scripted passes
> plus a VPS check. Previous report: `SYSTEM_AUDIT_2026-08-01.md`.

---

## 1. Вердикт / Verdict

🇷🇺 **Система полностью работоспособна. Открытых 🔴 проблем нет.**

Обе критические находки предыдущего аудита закрыты. Все 13 контейнеров здоровы, оба диска
смонтированы, USB-ошибок ноль, бэкапы идут по расписанию и впервые проверены восстановлением,
реверс-туннель жив, сервисы уведены за VPN.

🇬🇧 **The system is fully operational. There are no open 🔴 problems.**

Both critical findings of the previous audit are closed. All 13 containers are healthy, both
disks are mounted, USB errors are zero, backups run on schedule and have been verified by a
restore for the first time, the reverse tunnel is alive, and the services have been moved
behind the VPN.

| Область / Area | Оценка / Assessment |
|---|---|
| Доступность сервисов / Service availability | ✅ все отвечают / all respond |
| Хранилище / Storage | ✅ оба диска, 0 ошибок / both disks, 0 errors |
| Бэкап и восстановление / Backup and restore | ✅ работает, restore проверен / works, restore verified |
| Сеть и удалённый доступ / Network and remote access | ✅ туннель + VPN / tunnel + VPN |
| Безопасность периметра / Perimeter security | ✅ соответствует правилу №4 / complies with rule #4 |
| Безопасность внутри LAN / Security inside the LAN | 🟠 сегментации нет / no segmentation |
| Запас по памяти / Memory headroom | 🟠 плотно / tight |
| Мониторинг здоровья диска / Disk health monitoring | 🟠 SMART недоступен структурно / SMART is structurally unavailable |

---

## 2. Что закрыто с 2026-08-01 / What has been closed since 2026-08-01

### 2.1. ✅ Сервисы уведены из интернета (было 🔴) / Services moved off the internet (was 🔴)

🇷🇺 `ufw` на VPS сейчас:

🇬🇧 `ufw` on the VPS right now:

| Порт / Port | Откуда разрешён / Allowed from |
|---|---|
| 22/tcp | Anywhere — **нужен для реверс-туннелей** / **required for the reverse tunnels** |
| 443/tcp | Anywhere — amnezia-xray (VLESS+Reality) |
| 40568/udp | Anywhere — amnezia-awg2 (AmneziaWG) |
| 8080, 8443, 2283, 2443, 8090, 9443, **8099**, 8091, 8765, 8766 | только / only `172.29.172.0/24` и / and `10.8.1.0/24` |

🇷🇺 Admin-API `:8099`, который в прошлом аудите смотрел в интернет, теперь доступен исключительно
через VPN. Правило №4 соблюдено.

🇬🇧 The admin API on `:8099`, which faced the internet at the previous audit, is now reachable
exclusively through the VPN. Rule #4 is satisfied.

### 2.2. ✅ Бэкапы починены и восстановление проверено (было 🔴) / Backups fixed and restore verified (was 🔴)

🇷🇺 Причина простоя 24.07 → 09.08 оказалась не в таймере и не в диске: в `config/.env` строка
`TALK_BOT_DISPLAY_NAME=NAS Bot` **без кавычек**. Шелл читал её как `VAR=NAS` + команду `Bot`,
`set -euo pipefail` убивал скрипт на коде 127 — до первого `pg_dump`. При этом systemd честно
рапортовал `Result=success`.

Радиус поражения был шире бэкапов — тот же `source` делают:

1. `nasa-backup.service` — ночные дампы БД;
2. `storage_preflight.sh` — защитный барьер перед стартом Nextcloud/Immich;
3. `nasa-ssd-recovery.service` — **автовосстановление при hotplug SSD**;
4. `jetson-nas-health.service` — проверка storage/SMART.

То есть страховочная сетка «переткни кабель — поднимется само» была мертва 16 дней.

**Сейчас:** `ENV_SOURCE_OK`, ночной дамп от 2026-08-10 03:02 на месте
(`immich_20260810_030214.sql.gz` 19 МБ, `nextcloud_20260810_030214.sql.gz` 2.7 МБ).

🇬🇧 The cause of the 24.07 → 09.08 outage was neither the timer nor the disk: in `config/.env`
the line `TALK_BOT_DISPLAY_NAME=NAS Bot` was **unquoted**. The shell read it as `VAR=NAS` plus a
command `Bot`, and `set -euo pipefail` killed the script with exit code 127 — before the first
`pg_dump`. systemd meanwhile honestly reported `Result=success`.

The blast radius went beyond backups — the same `source` is done by:

1. `nasa-backup.service` — the nightly database dumps;
2. `storage_preflight.sh` — the safety barrier before Nextcloud/Immich start;
3. `nasa-ssd-recovery.service` — **automatic recovery on SSD hotplug**;
4. `jetson-nas-health.service` — the storage/SMART check.

In other words, the "just replug the cable and it comes back by itself" safety net was dead for 16 days.

**Now:** `ENV_SOURCE_OK`, the nightly dump from 2026-08-10 03:02 is in place
(`immich_20260810_030214.sql.gz` 19 MB, `nextcloud_20260810_030214.sql.gz` 2.7 MB).

🇷🇺 **Restore проверен впервые** (2026-08-09) — накатом дампов во временную БД с последующим DROP:

🇬🇧 **The restore was verified for the first time** (2026-08-09) — by loading the dumps into a
temporary database and dropping it afterwards:

| БД / Database | Таблиц / Tables | Сверка с live / Cross-check against live |
|---|---|---|
| Nextcloud | 153 | `oc_users` 5 = 5, `oc_filecache` 403 = 403 |
| Immich | 61 | `asset` 7098 = 7098, `album` 23 = 23 |

🇷🇺 Приём безопасен, потому что дамп льётся в **новую** БД в том же контейнере и удаляется после.

🇬🇧 The technique is safe because the dump is loaded into a **new** database inside the same
container and deleted afterwards.

### 2.3. ✅ Переезд на новый IP VPS / Migration to the new VPS IP

🇷🇺 `193.8.215.130` заблокирован российскими ISP (per-IP stateful-блок с 2026-08-06: новые потоки
дропаются, старые живут). Рабочий адрес — `95.163.176.103`, проверен по всем портам.
`VPS_HOST` правится в **root-owned** `/opt/nasa/config/.env`, а не в `~/nasa/config/.env`.

На момент аудита доступны **оба** пути: прямой `95.163.176.103` и внутренний `172.29.172.1`
через VPN-туннель.

🇬🇧 `193.8.215.130` is blocked by Russian ISPs (a per-IP stateful block since 2026-08-06: new
flows are dropped, existing ones survive). The working address is `95.163.176.103`, verified on
every port. `VPS_HOST` is edited in the **root-owned** `/opt/nasa/config/.env`, not in
`~/nasa/config/.env`.

At the time of the audit **both** paths are available: the direct `95.163.176.103` and the
internal `172.29.172.1` through the VPN tunnel.

---

## 3. Замеры 2026-08-10 / Measurements 2026-08-10

### 3.1. Хост / Host

| Параметр / Parameter | Значение / Value |
|---|---|
| Ядро / Kernel | 4.9.253-tegra |
| Аптайм / Uptime | 14 ч (перезагрузка 2026-08-09 15:41 UTC — применение USB-quirk для HDD) / 14 h (reboot 2026-08-09 15:41 UTC — applying the USB quirk for the HDD) |
| Load average | 0.60 / 0.94 / 0.94 |
| RAM | 2.0 ГБ из 3.9 занято, 1.6 доступно / 2.0 GB of 3.9 used, 1.6 available |
| Swap (zram ×4) | 312 МБ из 1.9 ГБ / 312 MB of 1.9 GB |
| Температуры / Temperatures | CPU 45 °C, AO 45 °C, GPU 41.5 °C, PMIC 50 °C |
| eth0 | 1000 Мбит/с, Full duplex, link up / 1000 Mbps, Full duplex, link up |
| Kernel cmdline | `usbcore.autosuspend=-1`, `usb-storage.quirks=0bda:9210:rw,152d:a583:u,0bda:9201:u` |

### 3.2. Хранилище / Storage

| Точка / Mount point | Устройство / Device | ФС / FS | Размер / Size | Занято / Used |
|---|---|---|---|---|
| `/` | mmcblk0p1 (SD) | ext4 | 60G | 23G (**40 %**) |
| `/mnt/storage` | sda1 (SSD, JMS583) | ext4 | 229G | 9.7G (**5 %**) |
| `/mnt/hdd2tb` | sdb1 (HDD, RTL9201) | ntfs-3g | 1.9T | 1.4T (**76 %**) |

🇷🇺 Оба USB-моста работают через драйвер **`usb-storage`** (UAS отключён quirk'ом) на шине 5000M.
`dmesg` с момента загрузки: **0** совпадений по `error -71`, `uas_eh`, `I/O error`, `usb disconnect`.

Распределение на SSD: immich 8.9G, backups 150M, logs 488K, остальное — служебное.

🇬🇧 Both USB bridges run through the **`usb-storage`** driver (UAS disabled by the quirk) on a
5000M bus. `dmesg` since boot: **0** matches for `error -71`, `uas_eh`, `I/O error`, `usb disconnect`.

SSD breakdown: immich 8.9G, backups 150M, logs 488K, the rest is housekeeping.

### 3.3. Контейнеры / Containers

🇷🇺 Все 13 — `Up 14 hours`, у всех `restarts=0` и `OOMKilled=false`.

🇬🇧 All 13 are `Up 14 hours`, all with `restarts=0` and `OOMKilled=false`.

| Контейнер / Container | Память / Memory | % лимита / % of limit |
|---|---|---|
| `homecloud_uptime_kuma` | 117.5 / 128 MiB | 🟠 **91.8 %** |
| `homecloud_immich_microservices` | 451.5 / 512 MiB | 🟠 **88.2 %** |
| `homecloud_netdata` | 217.3 / 256 MiB | 🟠 **84.9 %** |
| `homecloud_immich_server` | 552.4 MiB / 1 GiB | 53.9 % |
| `homecloud_immich_db` | 178.1 / 384 MiB | 46.4 % |
| `homecloud_nasa_api` | 57.8 / 128 MiB | 45.2 % |
| `homecloud_samba` | 57.4 / 128 MiB | 44.8 % |
| `homecloud_nextcloud` | 164.3 / 512 MiB | 32.1 % |
| `homecloud_immich_redis` | 19.5 / 64 MiB | 30.5 % |
| `homecloud_nextcloud_db` | 54.9 / 256 MiB | 21.4 % |
| `homecloud_llm_gateway` | 48.7 / 256 MiB | 19.0 % |
| `homecloud_portainer` | 22.0 / 128 MiB | 17.2 % |
| `homecloud_nextcloud_redis` | 9.0 / 64 MiB | 14.1 % |

### 3.4. Сервисы / Services

| Порт / Port | HTTP | Время / Time |
|---|---|---|
| 8080 Nextcloud | 302 | 0.145 с / s |
| 2283 Immich | 200 | 0.011 с / s |
| 8090 LLM Gateway | 404 на `/`, `/health` → ok / 404 on `/`, `/health` → ok | 0.003 с / s |
| 8099 API | 404 на `/`, `/docs` живой / 404 on `/`, `/docs` alive | 0.085 с / s |
| 3001 Uptime Kuma | 302 | 0.048 с / s |
| 19999 Netdata | 200 | 0.028 с / s |
| 9000 Portainer | 200 | 0.194 с / s |

🇷🇺
- Nextcloud **33.0.4**, `installed:true`, `maintenance:false`, `needsDbUpgrade:false`.
- Immich **2.7.5**, 7098 ассетов (6686 фото + 412 видео), 23 альбома, upload 5.8 ГБ.
- LLM Gateway: `{"status":"ok","provider":"deepseek","redaction":"true"}`.
- Talk-бот: `enabled:true, running:true, room:37pcobmf, processed:13, last_error:null`.
- Nextcloud external storage `/HDD-2TB` — mount id 1, Local → `/mnt/hdd2tb`, applicable All,
  `files_external` 1.25.1; каталог виден и из контейнера Nextcloud, и из контейнера Samba.

🇬🇧
- Nextcloud **33.0.4**, `installed:true`, `maintenance:false`, `needsDbUpgrade:false`.
- Immich **2.7.5**, 7098 assets (6686 photos + 412 videos), 23 albums, 5.8 GB uploaded.
- LLM Gateway: `{"status":"ok","provider":"deepseek","redaction":"true"}`.
- Talk bot: `enabled:true, running:true, room:37pcobmf, processed:13, last_error:null`.
- Nextcloud external storage `/HDD-2TB` — mount id 1, Local → `/mnt/hdd2tb`, applicable All,
  `files_external` 1.25.1; the directory is visible both from the Nextcloud container and from
  the Samba container.

### 3.5. systemd

🇷🇺 Failed-юнитов **нет**. Активные таймеры: `nasa-backup`, `nasa-jms583-health` (ежечасно),
`nasa-usb-watchdog`, `nasa-daily-report-telegram`, `jetson-nas-health` (каждые 6 ч).
Активные сервисы: `nasa-tunnel`, `nasa-usb-monitor`, `beszel-agent`.

`nasa-jms583-health` последний прогон: `Kernel quirk 152d:a583:u: ACTIVE`, `errors=0 warnings=0`.

🇬🇧 There are **no** failed units. Active timers: `nasa-backup`, `nasa-jms583-health` (hourly),
`nasa-usb-watchdog`, `nasa-daily-report-telegram`, `jetson-nas-health` (every 6 h).
Active services: `nasa-tunnel`, `nasa-usb-monitor`, `beszel-agent`.

`nasa-jms583-health`, last run: `Kernel quirk 152d:a583:u: ACTIVE`, `errors=0 warnings=0`.

### 3.6. Туннель и VPS / Tunnel and VPS

🇷🇺
- На Jetson: `nasa-tunnel.service` active, ESTAB `192.168.0.50:33882 → 95.163.176.103:22`.
- На VPS подняты все проброшенные порты: 18080, 12283, 18090, 18099, 10022, 45876.
- `nasa_nginx` проксирует: 8080 → 302, 2283 → 200, 8090 → 404 (на `/`), 8099 → 404 (на `/`), 8091 → 200.
- Контейнеры VPS: `beszel_hub`, `nasa_nginx`, `amnezia-awg2` — up 5 недель; `amnezia-xray` — up 2 дня.
- Telegram-отчёт доставлен 2026-08-09 16:33 MSK (`"ok":true`), следующий автозапуск по таймеру.

🇬🇧
- On the Jetson: `nasa-tunnel.service` active, ESTAB `192.168.0.50:33882 → 95.163.176.103:22`.
- On the VPS all forwarded ports are up: 18080, 12283, 18090, 18099, 10022, 45876.
- `nasa_nginx` proxies: 8080 → 302, 2283 → 200, 8090 → 404 (on `/`), 8099 → 404 (on `/`), 8091 → 200.
- VPS containers: `beszel_hub`, `nasa_nginx`, `amnezia-awg2` — up 5 weeks; `amnezia-xray` — up 2 days.
- The Telegram report was delivered 2026-08-09 16:33 MSK (`"ok":true`), the next run is on the timer.

---

## 4. Найдено и исправлено в ходе аудита / Found and fixed during the audit

### 🟠 Забытый тестовый HTTP-сервер на порту 8123 — **устранён** / A forgotten test HTTP server on port 8123 — **removed**

🇷🇺 `python3 -m http.server 8123` (pid 28142, cwd `/dev/shm`) висел **14 часов**, слушая `0.0.0.0`,
и отдавал листинг каталога всем в домашней сети. Остаток от замеров скорости Wi-Fi 2026-08-09.

Процесс погашен, порт закрыт (`8123_CLOSED_OK`), временный файл `/dev/shm/spd.bin` удалён.
Вывод занесён в «Грабли» в `CLAUDE.md`: после разовых замеров гасить процесс.

🇬🇧 `python3 -m http.server 8123` (pid 28142, cwd `/dev/shm`) had been hanging for **14 hours**,
listening on `0.0.0.0` and serving a directory listing to everyone on the home network. A leftover
from the Wi-Fi speed measurements of 2026-08-09.

The process was killed, the port closed (`8123_CLOSED_OK`), and the temporary file
`/dev/shm/spd.bin` deleted. The lesson was recorded in the "Pitfalls" section of `CLAUDE.md`:
kill the process after one-off measurements.

---

## 5. Остаточные риски (не 🔴, но держать в поле зрения) / Residual risks (not 🔴, but worth watching)

| # | Риск / Risk | Суть / Substance | Что делать / What to do |
|---|---|---|---|
| 1 | 🟠 Нет сегментации LAN / No LAN segmentation | Nextcloud, Immich, Portainer, admin-API :8099, Samba открыты **любому, кто знает пароль Wi-Fi**. Периметр интернета закрыт, внутренний — нет / Nextcloud, Immich, Portainer, the admin API on :8099 and Samba are open to **anyone who knows the Wi-Fi password**. The internet perimeter is closed, the internal one is not | Гостевая сеть при перестройке домашней сети (`docs/26`) / A guest network during the home-network rebuild (`docs/26`) |
| 2 | 🟠 Память впритык / Memory is tight | Три контейнера на 85–92 % своих лимитов; суммарные лимиты превышают физическую RAM / Three containers sit at 85–92 % of their limits; the combined limits exceed physical RAM | Пересмотреть лимиты; вынос ML на Vostro снимет часть нагрузки / Revisit the limits; moving ML onto the Vostro will remove part of the load |
| 3 | 🟠 SMART недоступен / SMART unavailable | UAS-quirk → usb-storage BOT → ATA/SCSI passthrough закрыт. `smartd` отключён осознанно / The UAS quirk → usb-storage BOT → ATA/SCSI passthrough is closed. `smartd` is disabled deliberately | Покрыто JMS583-таймером и USB-монитором. Пересмотреть только при обновлении smartmontools (сейчас 6.6 от 2016) / Covered by the JMS583 timer and the USB monitor. Revisit only if smartmontools is updated (currently 6.6 from 2016) |
| 4 | 🟠 Расхождение git ↔ устройство / git ↔ device divergence | На устройстве 8 файлов правлены вручную и не в git; `git pull` их затрёт / 8 files on the device were edited by hand and are not in git; `git pull` would overwrite them | Миграция на переименованный layout — отдельная задача с окном обслуживания / Migrating to the renamed layout is a separate task with a maintenance window |
| 5 | 🟡 Система на SD-карте / The system lives on an SD card | `/` = 60 ГБ SD, занято 40 %; SD — расходник / `/` = 60 GB SD, 40 % used; an SD card is a consumable | Мониторить рост; в перспективе перенос корня / Monitor the growth; eventually move the root filesystem |
| 6 | 🟡 Единственная точка бэкапа / A single backup location | Дампы лежат на том же SSD, что и данные / The dumps sit on the same SSD as the data | Restic off-site (HDD 2 ТБ подключён — блокер снят) / Restic off-site (the 2 TB HDD is attached — the blocker is gone) |
| 7 | 🟡 Зависимость от одного IP VPS / Dependence on a single VPS IP | Повторная блокировка `95.163.176.103` отрежет внешний доступ / A repeat block of `95.163.176.103` would cut off external access | Запасной путь `172.29.172.1` через VPN + IPv6 `2a12:5940:665a::2` / The fallback path `172.29.172.1` through the VPN + IPv6 `2a12:5940:665a::2` |

---

## 6. Проверенные команды аудита / Verified audit commands

```bash
# Единый канал до Jetson извне (позволяет прогнать локальный скрипт)
# A single channel to the Jetson from outside (lets you run a local script)
ssh -o "ProxyCommand=ssh -i ~/.ssh/borovskoy_new_ed25519 -W %h:%p root@95.163.176.103" \
    -p 10022 admin@127.0.0.1 "bash -s" < audit.sh

# Здоровье бэкапов — по файлам, НЕ по статусу юнита
# Backup health — judge by the files, NOT by the unit status
ls -lt /mnt/storage/backups/database-dumps/ | head -5

# Проверка, что .env не сломан / Check that .env is not broken
( set -euo pipefail; source ~/nasa/config/.env >/dev/null ) && echo OK || echo FAIL

# USB-ошибки с момента загрузки / USB errors since boot
dmesg -T | grep -Eic "error -71|uas_eh|I/O error|usb disconnect"   # ожидаем 0 / expect 0

# Туннель / Tunnel
systemctl is-active nasa-tunnel && ss -tn | grep 95.163.176.103

# Счётчики Immich / Immich counters
docker exec homecloud_immich_db psql -U immich -d immich -tAc \
  "select count(*) from asset;"
```

---

## 7. Связанные документы / Related documents

- `docs/plans/SYSTEM_AUDIT_2026-08-01.md` — предыдущий аудит (обе 🔴 закрыты здесь) / the previous audit (both 🔴 items are closed here)
- `docs/12_BACKUP_RESTORE.md` — процедура бэкапа и восстановления / the backup and restore procedure
- `docs/13_MONITORING_RUNBOOK.md` — мониторинг, в т.ч. почему отключён `smartd` / monitoring, including why `smartd` is disabled
- `docs/04_STORAGE_DESIGN.md` — оба диска и UAS-quirks / both disks and the UAS quirks
- `docs/26_DECO_E4_NETWORK.md` — план перестройки домашней сети (решение не принято) / the home-network rebuild plan (no decision made)
- `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md` — вынос ML на отдельный узел (решение не принято) / moving ML onto a separate node (no decision made)
