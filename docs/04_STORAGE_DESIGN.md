# 04. Дизайн хранилища / Storage Design

## 1. Цель / Purpose

🇷🇺 USB HDD является основным хранилищем данных. microSD используется для ОС и минимального runtime.

🇬🇧 USB HDD/SSD is the primary data storage. microSD is used for the OS and minimal runtime only.

> 🇷🇺 **Статус 2026-08-10: подключены два диска, оба работают без ошибок.**
>
> | Точка | Устройство | ФС | Размер | Занято | Мост | Скорость |
> |---|---|---|---|---|---|---|
> | `/mnt/storage` | `/dev/sda1` SSD | ext4 | 229G | 5 % (9.7G) | **JMS583** `152d:a583` | write **250** / read 172 МБ/с |
> | `/mnt/hdd2tb` | `/dev/sdb1` HDD | **NTFS** (ntfs-3g) | 1.9T | 76 % (1.4T) | **RTL9201** `0bda:9201` | read **106** / write 92 МБ/с |
>
> Оба моста требуют отключения UAS. В `/boot/extlinux/extlinux.conf`:
> `usb-storage.quirks=0bda:9210:rw,152d:a583:u,0bda:9201:u`. Без quirk оба диска
> отваливались с шины (`uas_eh_abort_handler`, `error -110`, смена буквы устройства).
> С момента загрузки — **0** USB-ошибок в dmesg. RTL9210B-CG заменён 2026-06-28.
>
> 🇬🇧 **Status 2026-08-10: two disks attached, both error-free.** SSD 229G ext4 at
> `/mnt/storage` (JMS583, 250/172 MB/s) and 2TB HDD at `/mnt/hdd2tb` (RTL9201, NTFS via
> ntfs-3g, 106/92 MB/s, 1.4 TB of existing family archive — **must not be reformatted**).
> Both USB bridges need the UAS quirk; zero USB errors since boot.

## 2. Рекомендуемая файловая система / Recommended Filesystem

🇷🇺 Рекомендуется `ext4`, если диск постоянно используется с Linux-сервером. NTFS допустим только как временный режим, если диск нужно регулярно подключать к Windows. Для БД Immich/Nextcloud NTFS не рекомендуется.

🇬🇧 `ext4` is recommended if the disk is used permanently with a Linux server. NTFS is acceptable only as a temporary mode if the disk is regularly connected to Windows. NTFS is not recommended for Immich/Nextcloud databases.

## 3. Существующий HDD с данными / Existing HDD with data

🇷🇺 Частый сценарий: пользователь подключает к Jetson уже используемый USB HDD, часто с файловой системой NTFS и личными данными. Такой диск нельзя сразу превращать в рабочий `/mnt/storage` и нельзя запускать `scripts/storage/setup_disk.sh`, пока не подтверждено, что данные сохранены и есть отдельный план миграции.

🇬🇧 Common scenario: user connects a previously-used USB HDD, often with NTFS and personal data. Never immediately convert such a disk to `/mnt/storage` and never run `scripts/storage/setup_disk.sh` until data is confirmed safe and a migration plan is in place.

🇷🇺 Безопасный порядок:
🇬🇧 Safe procedure:

1. Остановить сервисы, которые могут писать в `/mnt/storage`, если они уже
   запущены. Использовать только `stop`; не использовать `down -v`.
2. Проверить, что `/mnt/storage` сейчас действительно смонтирован на внешний диск,
   а не является обычным каталогом на microSD.
3. Найти диск и раздел через `lsblk`.
4. Смонтировать существующий раздел только для чтения в отдельную точку, например
   `/mnt/hdd-check`.
5. Проверить размер, файловую систему, метку и наличие данных без вывода личных
   имён файлов в публичные отчёты.
6. Только после этого выбрать отдельный сценарий: оставить NTFS как временный
   read-only источник, скопировать данные на новый ext4-диск или сделать backup и
   затем подготовить диск под Linux.

Команды для безопасного read-only intake:

```bash
# 1. Если Nextcloud/Immich уже запущены, остановить их перед проверкой storage.
# Пример для Nextcloud-only deployment:
docker compose -f docker/compose/docker-compose.nextcloud.yml --env-file config/.env stop

# 2. Убедиться, что /mnt/storage не является "ложным" каталогом на microSD.
mountpoint /mnt/storage || echo "/mnt/storage is not mounted"
du -sh /mnt/storage 2>/dev/null || true

# 3. Найти HDD и раздел.
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,TRAN,RO

# 4. Проверить NTFS-драйвер и смонтировать существующий NTFS-раздел только для чтения.
command -v ntfs-3g || sudo apt install -y ntfs-3g
sudo mkdir -p /mnt/hdd-check
sudo mount -t ntfs-3g -o ro /dev/sdXN /mnt/hdd-check

# 5. Подтвердить read-only режим и наличие данных без раскрытия содержимого.
findmnt /mnt/hdd-check
df -hT /mnt/hdd-check
find /mnt/hdd-check -mindepth 1 -maxdepth 1 | wc -l
```

Если NTFS-раздел помечен как dirty/hibernated, не использовать `force` и не
исправлять его на Jetson. Безопаснее отключить диск, проверить его на Windows
(`chkdsk`) и вернуться к read-only проверке.

Важно: монтирование диска в `/mnt/storage` скрывает уже существующие файлы в
одноимённом каталоге на microSD. Перед любым постоянным mount/fstab изменением
нужно проверить `du -sh /mnt/storage` и решить, нужно ли сохранять эти временные
данные.

## 3а. HDD с данными которые некуда перенести — NTFS + ext4 гибрид

### Ситуация

На HDD есть нужные файлы (фото, документы, архивы), объём большой — переносить некуда.
Форматировать нельзя. При этом HDD нужен как основное хранилище NAS_Jetson_Nano.

### Решение: два раздела на одном диске

```
HDD 2 TB (пример)
├── /dev/sda1  NTFS  1.4 TB  — старые файлы (данные сохраняются!)
└── /dev/sda2  ext4   600 GB — NAS_Jetson_Nano данные (Docker, БД, бэкапы)
```

NTFS-раздел монтируется отдельно → доступен через **Samba** со всей домашней сети.
ext4-раздел монтируется как `/mnt/storage` → используется Docker-сервисами.

> Старые файлы не просто сохраняются — они сразу становятся доступны с телефона,
> ноутбука, планшета по локальной сети через Samba.

### Шаг 1 — Сжать NTFS (Windows, до отключения HDD)

1. Подключить HDD к Windows
2. Нажать Win + X → "Управление дисками"
3. ПКМ на NTFS-разделе → **Сжать том**
4. Указать размер сжатия (сколько отдаём под ext4):
   - Рекомендуется: освободить ≥ 100 ГБ (минимум для БД + Nextcloud + Immich + бэкапы)
   - Хватает 50–200 ГБ в зависимости от объёма данных
5. Нажать "Сжать" — данные не затрагиваются, операция занимает секунды
6. Убедиться что в конце диска появилось "Нераспределённое пространство"
7. Безопасно извлечь HDD

### Шаг 2 — Создать ext4 на Jetson

```bash
# Найти диск
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MODEL

# Предположим HDD = /dev/sda, NTFS = /dev/sda1
# Нераспределённое пространство — пока без раздела

# Создать раздел ext4 в нераспределённом пространстве
sudo fdisk /dev/sda
# Нажать: n (новый раздел) → Enter → Enter → Enter → w (записать)
# fdisk сам возьмёт нераспределённое пространство

# Отформатировать новый раздел (обычно /dev/sda2)
sudo mkfs.ext4 -L nas_jetson_nano-storage /dev/sda2

# Получить UUID
sudo blkid /dev/sda2
```

### Шаг 3 — Настроить монтирование обоих разделов

```bash
# Установить поддержку NTFS (если не установлена)
sudo apt install ntfs-3g

# Создать точки монтирования
sudo mkdir -p /mnt/storage     # ext4 — для Docker/NAS_Jetson_Nano
sudo mkdir -p /mnt/hdd-ntfs   # NTFS — старые файлы

# Получить UUID обоих разделов
sudo blkid /dev/sda1  # NTFS
sudo blkid /dev/sda2  # ext4
```

Добавить в `/etc/fstab`:
```text
# NAS_Jetson_Nano storage (ext4) — Docker volumes, databases, backups
UUID=<ext4-UUID>  /mnt/storage   ext4  defaults,noatime,nofail  0 2

# Old data (NTFS) — existing files, accessible via Samba
UUID=<ntfs-UUID>  /mnt/hdd-ntfs  ntfs-3g  ro,uid=1000,gid=1000,umask=0022,nofail,_netdev  0 0
```

> `ro` — монтировать NTFS только для чтения (безопасно). Убрать `ro` если нужна запись.
> `nofail` — Jetson загрузится даже если HDD не подключён.

```bash
# Применить
sudo mount -a
df -h /mnt/storage /mnt/hdd-ntfs

# Проверить что обе точки смонтированы
mountpoint /mnt/storage && echo "OK: ext4"
mountpoint /mnt/hdd-ntfs && echo "OK: ntfs"
```

### Шаг 4 — Сделать NTFS-папку доступной через Samba

Добавить в `configs/samba/config.yml` новую шару:

```yaml
share:
  - name: archive
    path: /mnt/hdd-ntfs
    comment: "Old archive from HDD"
    browsable: yes
    readonly: yes          # читать можно, писать нельзя — данные в безопасности
    guestok: yes           # без пароля из домашней сети
```

Или в `configs/samba/smb.conf`:
```ini
[archive]
   path = /mnt/hdd-ntfs
   comment = Old HDD Archive
   browseable = yes
   read only = yes
   guest ok = yes
```

После изменения конфига перезапустить Samba:
```bash
ssh admin@192.168.0.50 "docker compose -f ~/nas_jetson_nano/docker/compose/docker-compose.samba.yml --env-file ~/nas_jetson_nano/config/.env restart"
```

### Итог: что где хранится

| Что | Где | Формат | Доступ |
|---|---|---|---|
| Старые файлы (фото, документы, архивы) | `/mnt/hdd-ntfs` | NTFS | Samba `\\192.168.0.50\archive` |
| Nextcloud файлы новых пользователей | `/mnt/storage/nextcloud/data` | ext4 | Nextcloud web/desktop/mobile |
| Immich фотоархив | `/mnt/storage/immich/library` | ext4 | Immich app |
| Базы данных (PostgreSQL) | `/mnt/storage/db/` | ext4 | Docker internal |
| Бэкапы | `/mnt/storage/backups/` | ext4 | Автоматически (03:00) |

### Если свободного места на диске нет совсем

Если NTFS занимает весь диск и нет нераспределённого пространства:

**Вариант A** — использовать microSD для баз данных (текущая конфигурация, `/mnt/storage` на microSD).
Баз данных сейчас ~434 МБ — microSD справляется. NTFS HDD монтируется только для Samba.

**Вариант B** — добавить второй USB-носитель (даже 32 ГБ флешка) под ext4 для баз данных.

**Вариант C** — сжать NTFS со стороны Windows и освободить хотя бы 30–50 ГБ.

## 3б. Как это сделано фактически (as-built, 2026-08-09)

🇷🇺 Раздел 3а описывает общий рецепт. В проекте выбран **более простой путь**: разделять диск
не понадобилось, потому что под данные NAS уже был отдельный SSD.

🇬🇧 Section 3a is the generic recipe. The project took a **simpler route** — no repartitioning
was needed, because a dedicated SSD already served as NAS storage.

| Диск | Роль | ФС | Точка | Почему так |
|---|---|---|---|---|
| SSD 250 ГБ (JMS583) | рабочее хранилище NAS | ext4 | `/mnt/storage` | БД, Docker-тома, бэкапы — им нужен ext4 и скорость |
| HDD 2 ТБ (RTL9201) | семейный архив | **NTFS целиком** | `/mnt/hdd2tb` | На диске 1.4 ТБ данных, переносить некуда → **не форматируем** |

**Опасения про «FUSE медленный» не подтвердились:** сырое чтение 106 МБ/с, запись через
ntfs-3g 92 МБ/с, после 5 ГБ трафика — 0 ошибок.

### Фактическая строка `/etc/fstab`

```text
UUID=8480B9A880B9A0DA /mnt/hdd2tb ntfs-3g defaults,nofail,noatime,uid=33,gid=33,umask=0000,big_writes,allow_other,x-systemd.device-timeout=30 0 0
```

- `uid/gid=33` = `www-data` (Nextcloud), `umask=0000` — чтобы писал и Samba-пользователь `nas`
  (uid 1000). У NTFS всё равно нет POSIX-прав.
- В `/etc/fuse.conf` добавлен `user_allow_other`.
- Перед первым монтированием прогнан `ntfsfix -d` (снят dirty-флаг).

### Доступ к архиву

| Путь | Как | Откуда |
|---|---|---|
| Nextcloud external storage `/HDD-2TB` | `files_external`, backend Local → `/mnt/hdd2tb`, applicable All | из любой точки мира (через VPN) |
| Samba шара `hdd2tb` | `\\192.168.0.50\hdd2tb`, пользователь `nas`, read-write, guest запрещён | домашняя LAN |

Проброс в контейнер — строка `- /mnt/hdd2tb:/mnt/hdd2tb` в `docker-compose.nextcloud.yml`
и `docker-compose.samba.yml`.

### ⚠️ Грабли

1. **После правки `/etc/fstab` обязателен `systemctl daemon-reload`** — иначе systemd
   примонтирует диск по устаревшему сгенерированному юниту со старыми опциями.
2. **FUSE + Docker:** если хостовое монтирование пересоздаётся, контейнеры продолжают держать
   мёртвую ссылку и дают `Input/output error`. Лечится только
   `docker compose up -d --force-recreate` этих контейнеров. При обычной загрузке проблемы нет —
   fstab монтирует до старта Docker.
3. **UAS-quirk нужен и этому мосту.** Через ~2 ч работы диск отвалился с шины и переехал
   `sdb` → `sdc`, контейнеры получили I/O error. Лечится добавлением `0bda:9201:u` в
   `usb-storage.quirks` (см. раздел 1).

## 4. Целевая структура

Перед созданием каталогов или запуском Nextcloud/Immich/backup обязательно
проверить, что `/mnt/storage` является mountpoint на внешнем устройстве, а не
обычной директорией на microSD:

```bash
sudo bash scripts/storage/storage_preflight.sh
```

```text
/mnt/storage
├── nextcloud/
│   ├── data/
│   └── config-backup/
├── immich/
│   ├── library/
│   ├── upload/
│   └── profile/
├── db/
│   ├── nextcloud-postgres/
│   ├── immich-postgres/
│   └── redis/
├── samba/
│   ├── public/
│   ├── exchange/
│   └── family/
├── backups/
│   ├── database-dumps/
│   ├── configs/
│   └── restic-repo/
└── diagnostics/
    ├── hardware/
    ├── docker/
    └── logs/
```

## 5. Создание каталогов

```bash
sudo mkdir -p /mnt/storage/{nextcloud/data,nextcloud/config-backup}
sudo mkdir -p /mnt/storage/{immich/library,immich/upload,immich/profile}
sudo mkdir -p /mnt/storage/db/{nextcloud-postgres,immich-postgres,redis}
sudo mkdir -p /mnt/storage/samba/{public,exchange,family}
sudo mkdir -p /mnt/storage/backups/{database-dumps,configs,restic-repo}
sudo mkdir -p /mnt/storage/diagnostics/{hardware,docker,logs}
sudo chown -R $USER:$USER /mnt/storage
```

## 6. Автомонтирование

Получить UUID:

```bash
sudo blkid
```

Пример `/etc/fstab`:

```text
UUID=<HDD_UUID> /mnt/storage ext4 defaults,noatime 0 2
```

Проверка:

```bash
sudo mount -a
df -h /mnt/storage
sudo bash scripts/storage/storage_preflight.sh
```

## 7. Критический контроль

После перезагрузки:

```bash
mount | grep /mnt/storage
df -h /mnt/storage
sudo dmesg | grep -i -E "error|reset|i/o" | tail -n 100
sudo bash scripts/storage/storage_preflight.sh
```

Если `storage_preflight.sh` не проходит, нельзя запускать backup, Nextcloud
data repair или массовую запись на `/mnt/storage`: есть риск записать данные на
microSD или усугубить I/O-инцидент.
