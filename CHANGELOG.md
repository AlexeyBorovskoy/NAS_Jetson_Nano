# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added / Добавлено

- 🇷🇺 **Шаг 2 (развитие проекта):** разбор отзывов с Habr и дорожная карта
  (`docs/plans/POST_HABR_FEEDBACK_2026-08.md`, двуязычный); решение ввести старый
  Dell Vostro 15 (2018) как выделенный Immich ML-узел
  (`docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`, двуязычный); раздел «Шаг 2» в README;
  трекинг — issue #9.
- 🇬🇧 **Step 2 (project evolution):** Habr feedback review and roadmap
  (`docs/plans/POST_HABR_FEEDBACK_2026-08.md`, bilingual); decision to add the old
  Dell Vostro 15 (2018) as a dedicated Immich ML node
  (`docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`, bilingual); a "Step 2" section in README;
  tracked in issue #9.
- Added a sanitized inventory and commissioning runbook for the physical
  Keenetic Omni KN-1410 planned as a Wi-Fi extender:
  `docs/25_KEENETIC_OMNI_KN1410.md`.
- Linked the planned extender into `docs/19_NETWORK_INVENTORY.md` and
  `docs/05_NETWORKING_VPN.md`, `README.md`, `docs/index.md`, and `CLAUDE.md`;
  added public-only placeholders to `config/.env.example` without copying label
  credentials or unique identifiers.

### Corrected / Исправлено

- 🇷🇺 Исправлено недостоверное заявление о публикации статьи на Habr: статья не опубликована; в репозитории находятся только черновики и материалы подготовки. **(Обновление 2026-08-01: статья Часть 1 опубликована — https://habr.com/ru/articles/1062914/; статусные доки приведены в соответствие.)**
- 🇬🇧 Corrected the unsupported claim that the Habr article had been published: it is unpublished; the repository contains drafts and preparation materials only. **(Update 2026-08-01: Part 1 is now published — https://habr.com/ru/articles/1062914/; status docs updated accordingly.)**

---

## [1.4.1] — 2026-06-29 · GitHub Pages + Habr preparation

### Added / Добавлено

- **GitHub Pages** (`docs/` → `main` branch):
  - `docs/_config.yml` — Jekyll theme (jekyll-theme-minimal)
  - `docs/index.md` — landing page: highlights, status table, links
  - `docs/pages/architecture.md` · `reliability.md` · `android.md` · `evidence.md`
  - `docs/assets/screenshots/article/redacted/` — 7 редактированных скриншотов (01–07)
  - URL: https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
- **Habr article / Статья для Habr** — подготовлены черновики и форматы для редактора; публикация не подтверждена и фактически не состоялась.
  - `docs/articles/habr_article_ru.md` — канонический вариант для GitHub Pages (пути 01–07)
  - `docs/articles/habr_ready.md` — чистая версия для вставки в Markdown-редактор Хабра
  - `docs/articles/habr_wysiwyg.html` — HTML для вставки в WYSIWYG-редактор Хабра
  - `docs/articles/hackaday_project_en.md` — черновик для Hackaday.io
- **`.gitleaks.toml`** — конфиг подавления ложных срабатываний (placeholders)
- **README.md**: раздел «Статьи и публикации / Articles» с черновиком Habr и ссылкой на GitHub Pages
- **`docs/prompts/CODEX_GITHUB_PAGES_PUBLICATION_PROMPT.md`** — сохранён промпт публикации

---

## [1.4.0] — 2026-06-29 · JMS583 USB SSD + Nextcloud Talk + NAS_Jetson_Nano API v0.6.0

### Added / Добавлено

- **JMS583 USB SSD enclosure** (152d:a583, USB 3.0 SuperSpeed, 5 Gbps) — заменил RTL9210B-CG:
  - Write **250 MB/s**, Read **172 MB/s** подтверждены (`dd bs=1M`)
  - `usb-storage.quirks=152d:a583:u` в `/boot/extlinux/extlinux.conf` — UAS quirk, BOT mode
  - `scripts/monitoring/jms583_health.sh` + `systemd/nas_jetson_nano-jms583-health.{service,timer}` —
    ежечасный мониторинг: USB ошибки, скорость I/O, статус очереди; Telegram-алерт
- **Nextcloud Talk** — семейный чат на базе Nextcloud spreed v23.0.7:
  - Группа «Семья» (`token: 37pcobmf`), 5 участников: admin, olga, ivan, ulyana, anna
  - Пользователь `anna` (Talk-only) добавлен в Nextcloud
  - `artifacts/users/ANNA_setup.txt` — памятка для Anna (Talk-only)
  - Памятки OLGA/IVAN/ULYANA переписаны: Talk → первый раздел
- **NAS_Jetson_Nano API v0.6.0** — новые роутеры:
  - `GET /v1/talk/rooms` · `GET /v1/talk/rooms/{token}` · `POST /v1/talk/notify` — Talk интеграция
  - `GET /v1/users` · `GET /v1/users/{username}` · `POST /v1/users/{username}/notify` — пользователи
  - `GET /v1/photos/stats` · `GET /v1/photos/users` — статистика Immich (6484 фото, 210 видео, 4.24 GB)
  - `POST /v1/actions/containers/{name}/restart` · `POST /v1/actions/backup/now` · `GET /v1/actions/history`
  - `main.py` v0.6.0: 9 Swagger-секций, `tryItOutEnabled`, `persistAuthorization`
  - `config.py`: `NEXTCLOUD_ADMIN_PASSWORD`, `IMMICH_API_KEY`, `TALK_FAMILY_ROOM`, `RESTARTABLE_CONTAINERS`
  - `docker-compose.nas_jetson_nano-api.yml`: новые env vars пробрасываются в контейнер
  - Immich API key `nas_jetson_nano-api-monitor` создан (permission: all), сохранён в `config/secrets.json`
- **goss**: 40/40 тестов (было 34) — добавлены тесты для JMS583, Talk, новых systemd-сервисов
- **`docs/plans/NAS_Jetson_Nano_API_ROADMAP.md`** — дорожная карта NAS_Jetson_Nano API, v0.2.0→v0.6.0

### Fixed / Исправлено

- **exec bit loss** — 33 bash-скрипта потеряли exec bit после Windows pull;
  `git update-index --chmod=+x` для 9 критических; `nas_jetson_nano-ssd-recovery.service` восстановлен
- **NEXTCLOUD_ADMIN_PASSWORD** в `.env` на Jetson исправлен (регистр: `all270174bae` → `ALL_270174_bae`)
- **Nextcloud `overwrite.cli.url`** → `https://193.8.215.130:8443` — исправлен для корректного
  browser redirect при login через Talk/Nextcloud app на Android
- **Дубликаты Talk-комнат** (3 шт.) удалены через `occ talk:room:delete`; осталась одна `37pcobmf`

### Security / Безопасность

- Immich API key добавлен в `config/secrets.json` (gitignored)

---

## [1.3.9] — 2026-06-28 · SSD hotplug auto-recovery + Android family setup + users

### Added / Добавлено

- **`scripts/storage/ssd_hotplug_recovery.sh`** + **`systemd/nas_jetson_nano-ssd-recovery.service`** —
  udev hotplug auto-recovery: `sda1 ADD` → mount → preflight → `systemctl start docker` →
  `docker start` stopped containers. Logs: `/var/log/nas_jetson_nano-monitor/ssd-recovery.log`
- **udev rule** (in `install_usb_watchdog.sh`): `ACTION=="add", KERNEL=="sda1"` → start recovery service
- **Family users** — OLGA, IVAN, ULYANA created in Nextcloud and Immich; setup memos: `artifacts/users/`
- **2151 contacts imported** to Nextcloud via CardDAV PUT (Python script, bulk VCF → individual vCards)
- **Android apps configured**: Immich ✅ (6719 photos, backup active), Nextcloud ✅, DAVx⁵ ✅ (CalDAV/CardDAV)
- **Samba `config.yml`** (`configs/samba/config.yml`) — proper YAML config for crazymax/samba;
  shares: `public` (guest OK), `nextcloud` (read-only), `immich` (read-only)
- **`docs/plans/API_MOBILE_PLAN.md`** — NAS_Jetson_Nano API expansion plan: FastAPI facade + JWT + Flutter MVP
- **`docs/articles/habr_draft.md`** — Habr article first draft

### Fixed / Исправлено

- **Immich admin password** — reset via bcrypt + PostgreSQL after rotation; saved to `config/secrets.json`
- **Samba `config.yml` was a directory** — Docker bind-mount created dir when file missing; fixed + YAML added
- **SSD mounted at boot** — `nas_jetson_nano-usb-preboot.service` ensures power cycle before `fstab` mount attempt
- **immich-microservices `mem_limit: 512m`** — applied and confirmed on Jetson

### Security / Безопасность

- **`config/secrets.json`** updated with Immich admin + family user credentials (gitignored)
- All service passwords rotated 2026-06-28; git history clean (filter-repo done in v1.3.8)

---

## [1.3.8] — 2026-06-27 · Password rotation + repo refactor + tech debt closure

### Added / Добавлено

- **Repository structure refactor** per open-source conventions: new dirs `assets/`, `artifacts/`, `archive/`, `docs/prompts/`; agent prompts moved `prompts/` → `docs/prompts/`; hardware photos → `assets/photos/`; audit reports → `artifacts/reports/`; migration log at `docs/quality/STRUCTURE_REFACTOR_REPORT.md`
- **`docs/REPOSITORY_STRUCTURE.md`** — guide for where to put new files, Docker Compose commands reference
- **`tests/storage/smart_check.sh`** — updated for RTL9210B-CG: detects USB bridge, skips SMART (blocked), checks USB bus speed, runs `dd` read test; reports USB 2.0 degradation (480 Mbps / ~40 MB/s vs expected 5 Gbps)
- **`.gitattributes`** — enforces LF for `*.md` docs (prevents Windows CRLF in documentation files)

### Fixed / Исправлено

- **Security: git history rewrite** — removed leaked password hash from 87 commits using `git filter-repo`; force-pushed clean history to GitHub
- **Password rotation** — Jetson sudo, Nextcloud admin, Portainer admin, Beszel Hub admin all rotated; `config/secrets.json` updated (gitignored, never committed)
- **`immich-microservices` mem_limit** — 512 MB applied and confirmed (`MemoryLimit: 536870912`); container recreated to apply
- **CLAUDE.md** — comprehensive update: watchdog ⚠️ STOPPED (pending JMS583 swap), prompts path → `docs/prompts/`, password rotation dated, mem_limit confirmed
- **Stale path references** in README.md: `photo/test_sys.jpg` → `assets/photos/test_sys.jpg`, `prompts/` → `docs/prompts/`
- **README.md bilingual** — Security and Contributing sections fully bilingual (🇷🇺+🇬🇧), broken image table removed (images not tracked in git)
- **`docs/references/EXTERNAL_DOCS_CACHE.md`** — all path references updated `external_docs/` → `docs/references/external_docs/`

### Security / Безопасность

- Leaked password removed from git history via `git filter-repo` (87 commits rewritten, force-pushed)
- All 4 service passwords rotated; old credentials invalidated on Jetson, Nextcloud, Portainer, Beszel Hub
- `config/secrets.json` confirmed gitignored; `config/.env` confirmed gitignored

---

## [1.3.7] — 2026-06-26 · USB SSD audit + watchdog hardening

### Added / Добавлено

- **`.gitattributes`** — force LF line endings для *.sh, *.service, *.timer, *.yml;
  предотвращает CRLF-коррупцию скриптов при работе из Windows
- **`scripts/storage/usb_preboot_cycle.sh`** + **`systemd/nas_jetson_nano-usb-preboot.service`** —
  power cycle USB порта ДО монтирования SSD при каждом boot;
  сбрасывает RTL9210B-CG из crashed-состояния (выживает software reboot)
- **`scripts/monitoring/usb_error_monitor.sh`** + **`systemd/nas_jetson_nano-usb-monitor.service`** —
  real-time dmesg watcher: Telegram-алерт при первом `error -71` до того,
  как Docker начнёт падать; немедленно запускает watchdog (не ждать 3 мин)
- **`scripts/storage/deploy_usb_fix.sh`** — идемпотентный деплой-скрипт
  с `sed 's/\r$//'` для защиты от CRLF при копировании из git

### Fixed / Исправлено

- **RTL9210B-CG root cause audit**:
  - CRLF в shebang (`#!/usr/bin/env bash\r`) → systemd 203/EXEC →
    watchdog не работал 4+ часов → SSD в broken state без recovery
  - watchdog `POWER_OFF_SECS` увеличен 15s→45s (15s недостаточно для
    разряда bypass-конденсаторов RTL9210B-CG)
  - watchdog `WAIT_ENUM_SECS` увеличен 20s→30s
  - watchdog timer `OnBootSec` уменьшен 5min→2min
- **dos2unix** установлен на Jetson; деплой-скрипт использует его автоматически

### Root cause / Анализ

Два независимых сбоя:
1. RTL9210B-CG (Realtek USB-SATA bridge) сохраняет crashed-состояние через
   software reboot (USB hub остаётся под питанием) и не восстанавливается
   через uhubctl power cycle (паразитное питание через bypass-конденсаторы).
   Единственный надёжный сброс — физическое отключение USB кабеля.
2. Git на Windows конвертировал LF→CRLF в shell-скриптах, что при `cp`
   из репозитория создавало нерабочие shebang-строки.

**Hardware note**: RTL9210B-CG ненадёжен по дизайну.
Рекомендация: заменить энклоужер на JMicron JMS578 или ASMedia ASM1153E.

---

## [1.3.6] — 2026-06-26 · Android Immich backup + USB SSD port fix

### Added / Добавлено

- **Immich Android полностью настроен** (сессия 2026-06-26):
  - Создан admin-аккаунт через API: `admin@nas_jetson_nano.local`
  - Приложение авторизовано через VPS: `http://193.8.215.130:2283`
  - Выбраны все 31 альбом устройства (6710 фото/видео)
  - Бэкап активирован (toggle "Активировать" = ON)
  - Включена загрузка фото по мобильному интернету
  - Включена синхронизация альбомов

### Fixed / Исправлено

- **USB SSD порт 4 (1-2.4) сломан → переткнут в порт 2 (1-2.2)**:
  error -71 (EPROTO) при каждом boot — аппаратная неисправность порта;
  смена физического порта решила проблему мгновенно
- **Watchdog PORT=4 → PORT=2** в `scripts/storage/usb_recovery_watchdog.sh`
  и на Jetson `/usr/local/sbin/nas_jetson_nano-usb-watchdog.sh`
- **SCSI timeout 120s подтверждён**: `cat /sys/block/sda/device/timeout` = 120 ✅
- **usb-storage.quirks=0bda:9210:rw подтверждён**: dmesg показывает
  `Quirks match for vid 0bda pid 9210: 220` при enumeration

### Validated / Проверено

- Все 13 Docker контейнеров healthy через 3 мин после boot
- SSD монтируется при каждом boot (7 boot подряд на порту 2)
- USB watchdog timer active: `nas_jetson_nano-usb-watchdog.timer`
- Immich API: `GET /api/server/ping` → `{"res":"pong"}`

---

## [1.3.5] — 2026-06-25 · Android mobile sync + HTTPS

### Added / Добавлено

- **Android mobile module** — `docs/android/`:
  - `ANDROID_SETUP.md` — пошаговая настройка Immich, Nextcloud, DAVx⁵ на Xiaomi MIUI/HyperOS
  - `GOOGLE_MIGRATION.md` — миграция с Google Photos/Contacts/Calendar/Drive через Google Takeout;
    чеклист, инструкция по immich-go для массового импорта с метаданными GPS/дата
  - `XIAOMI_MIUI_QUIRKS.md` — whitelist батарея, автозапуск, блокировка в RAM для Immich/DAVx⁵
- **nginx HTTPS на VPS** — `scripts/setup/install_nginx_vps.sh`:
  добавляет TLS (самоподписанный, 10 лет) к уже работающему `nas_jetson_nano_nginx` Docker контейнеру;
  открывает порты 8443 (Nextcloud), 2443 (Immich), 9443 (LLM) в ufw;
  без конфликта с Amnezia (443 занят xray → используются alt-порты)

### Fixed / Исправлено

- **usbcore.autosuspend=-1 подтверждён** после ребута Jetson (2026-06-25):
  `/sys/module/usbcore/parameters/autosuspend = -1` — kernel param активен
- **Nextcloud trusted proxy** настроен через `occ`: `trusted_proxies`, `overwriteprotocol=https`,
  `forwarded_for_headers` — HTTPS-заголовки корректно проксируются

---

## [1.3.4] — 2026-06-24 · Beszel monitoring + USB watchdog

### Added / Добавлено

- **Beszel: оба агента зарегистрированы и активны** (2026-06-24):
  - `jetson-nano` (127.0.0.1:45876) → status `up`, CPU 17%, RAM 58%
  - `vps-vienna` (127.0.0.1:45877) → status `up`, CPU 2%, RAM 27%
  - `scripts/monitoring/install_beszel_agent_vps.sh` — установщик amd64 агента на VPS;
    читает Hub pubkey из `/opt/nas_jetson_nano/beszel-hub/data/id_ed25519` автоматически;
    wrapper-скрипт обходит systemd ExecStart-ограничения при ключе с пробелами

---

## [1.3.4] — 2026-06-24 · Beszel monitoring + USB watchdog

### Added / Добавлено

- **Beszel monitoring** — Hub на VPS (порт 8091, Docker host network, SQLite история),
  Agent на Jetson (binary 0.18.7, arm64, systemd, порт 45876).
  Telegram алерты через Shoutrrr (23+ канала).
  `docker/vps/docker-compose.yml` — beszel-hub сервис.
  `scripts/monitoring/install_beszel_agent.sh` — установщик агента.
- **USB storage watchdog** — `scripts/storage/install_usb_watchdog.sh`:
  - udev rule: `power/control=on` для RTL9210B-CG (0bda:9210) **и USB-хаба** (0bda:5411 / 0411);
    хаб в autosuspend убивает дочерние устройства вне зависимости от настроек bridge
  - `usbcore.autosuspend=-1` в `/boot/extlinux/extlinux.conf` (belt-and-suspenders, после ребута)
  - smartd с явным `/dev/sda` (DEVICESCAN не работает на Tegra kernel 4.9)
  - Telegram alert на remove/add `/dev/sda` через VPS SSH relay
  - Root cause: RTL9210B-CG входит в ELPG цикл при USB reset mid-write →
    только физический power cycle выводит. Fix предотвращает сам вход.
- **Tunnel port 45876** — `systemd/nas_jetson_nano-tunnel.service`: добавлен
  `-R 45876:localhost:45876` для Beszel Agent → Hub через VPS.
- **GitHub traffic monitoring** — `docs/metrics/GITHUB_TRAFFIC.md`:
  ежедневный лог просмотров, клонов, источников трафика, звёзд.
  Первая запись: 2026-06-24 (371 клон / 149 уник. за 14 дней, 0 звёзд).

### Fixed / Исправлено

- `install_usb_watchdog.sh`: добавлены udev-правила для USB-хаба (0bda:5411/0411) —
  без них хаб мог засыпить шину, роняя SSD
- `install_usb_watchdog.sh`: `DEVICESCAN` → явный `/dev/sda` в smartd.conf —
  DEVICESCAN падает на Tegra kernel 4.9 (нет `/dev/discs/disc*`)

### Changed / Изменено

- `README.md`: статус обновлён до 2026-06-24; Beszel Hub/Agent добавлены в таблицу сервисов;
  USB watchdog в Known Limitations заменён описанием применённого фикса

- `scripts/storage/storage_preflight.sh`: fail-closed sudo storage preflight before
  starting Nextcloud/Immich/backup; checks mountpoint, backing device, fstab UUID,
  read-only mounts, critical paths and Nextcloud `.ncdata`.
- `scripts/storage/install_mount_service.sh`: safe installer for
  `jetson-nas-mount.service`; install/enable by default, immediate mount only with
  explicit `--start`.
- `scripts/storage/install_docker_storage_guard.sh` and
  `systemd/docker.service.d/10-nas_jetson_nano-storage.conf`: optional strict boot guard
  that makes Docker wait for `/mnt/storage` after power loss or USB failure.
- `docs/plans/RELIABILITY_AUDIT_2026-06-23.md`: live reliability audit via VPS
  with confirmed Jetson findings, repo mitigations, and SSD recovery paths.

### Changed / Изменено

- `docker/compose/docker-compose.nas_jetson_nano-api.yml`,
  `services/nas_jetson_nano-api/app/config.py`, and
  `scripts/monitoring/nas_jetson_nano-daily-report.sh`: expected containers now use real
  `homecloud_*` container names instead of stale compose-generated names.
- `scripts/monitoring/nas_jetson_nano-daily-report.sh`: adds storage mount health,
  Nextcloud `.ncdata` presence check, recent kernel storage errors, and separate
  VPS checks for Nextcloud, Immich, and LLM Gateway.
- `scripts/backup/backup_databases.sh`: refuses to write database dumps when
  `${STORAGE_ROOT}` is not a mountpoint, cannot be resolved, points to microSD, or
  is not writable.
- `systemd/nas_jetson_nano-backup.service` and `systemd/jetson-nas-health.service`: require
  `/mnt/storage` to be a real mountpoint before running.
- `systemd/jetson-nas-mount.service`: uses `STORAGE_ROOT=/mnt/storage` default,
  reads `/home/admin/nas_jetson_nano/config/.env`, and avoids unsupported shell-style
  `${VAR:-default}` expansion in systemd `ExecStart`.
- `docker/compose/docker-compose.samba.yml`, `docker/compose/docker-compose.stage1.yml`,
  and `docker/vps/docker-compose.yml`: normalized restart policy to `always`.
- `docs/13_MONITORING_RUNBOOK.md`: added USB storage failure runbook for
  `error -71`, ext4 read-only remounts, safe recovery order, and preflight usage.
- Top-level and operational docs now reflect the recovered SSD state, intentional
  Nextcloud stop, live DB backup success, and the remaining hardware risk in the
  USB cable/enclosure/power chain.
- Jetson `~/nas_jetson_nano` checkout synchronized to `6844447`; the pre-sync live diff is
  preserved on Jetson as `stash@{0}` for audit/recovery.
- Nextcloud data/app review completed read-only: 503 traced to the earlier
  read-only storage remount; `.ncdata`, ownership, config and DB checks are
  clean, with controlled start left as the next step.
- Nextcloud controlled start completed: `homecloud_nextcloud` is running,
  `restart=always`, healthcheck is healthy, local and VPS `/status.php` return
  HTTP 200, and no new kernel storage errors were observed after start.
- Reboot/autorecovery test completed: Jetson returned with a new boot id, the
  VPS reverse tunnel recovered, `/mnt/storage` mounted as `/dev/sda1`, preflight
  passed, storage-backed containers became healthy, VPS endpoints returned HTTP
  200, and `jetson-nas-health.timer` finished with `issues: 0`.

## [1.3.3] — 2026-06-21 · Client setup + HDD hybrid storage

### Added / Добавлено

- **`docs/24_CLIENT_SETUP.md`**: полное руководство по подключению устройств —
  Android (Nextcloud app, DAVx⁵, Immich, Samba), Windows (Desktop client, WebDAV, net use),
  Linux (nextcloudcmd, cifs-utils, Nautilus); таблица URL для LAN и внешнего доступа
- **`docs/04_STORAGE_DESIGN.md` §3а**: новый раздел "HDD с данными — NTFS + ext4 гибрид":
  пошаговый план сжатия NTFS (Windows), создания ext4 на Jetson, двойного fstab-монтирования,
  добавления NTFS-шары в Samba (`archive`); таблица "что где хранится"
- **`README.md`**: добавлены docs/23 и docs/24 в таблицу документации

## [1.3.2] — 2026-06-21 · GitHub integration + promotion

### Added / Добавлено

- **`CLAUDE.md`**: контекстный файл проекта для Claude Code — автоматически читается
  при открытии репозитория; содержит адреса сервисов, команды SSH, workflow, ограничения
- **`docs/23_GITHUB_INTEGRATION.md`**: полное руководство по GitHub CLI интеграции —
  авторизация PAT, `gh issue/pr/release`, стандартный workflow сессии, AI-assisted DevOps цикл
- **`AGENTS.md` §6**: новый раздел GitHub CLI — разрешённые операции, аварийное восстановление auth
- **`gh` CLI** (`C:\tools\gh\bin\`, v2.74.1): авторизован через Windows keyring (полные права `repo`)
- **GitHub Discussions** включены; Welcome-дискуссия (#7) создана
- **GitHub Issues** #4, #5, #6 — три `good first issue` задачи (HTTPS, RPi guide, Netdata alerts)

### Changed / Изменено

- **`README.md`**: полный рерайт вводной части — личная история (Jetson в ящике, HDD через раз),
  убрана таблица цен, более живой и человеческий язык в секциях "О проекте" и "Для кого"
- **`README.md`**: добавлены бейджи stars/discussions/issues/CI, призыв поставить ⭐
- **`README.md`**: секция Contributing — прямые ссылки на good first issues
- **GitHub**: homepage очищен (был бессмысленный `#readme`)

## [1.3.1] — 2026-06-21 · Phase 1 ops tasks

### Added / Добавлено

- **`systemd/nas_jetson_nano-backup.{service,timer}`**: systemd timer for daily automated
  `pg_dump` at 03:00 (±15 min randomized delay); `Persistent=true` so missed
  runs are retried on next boot
- **`scripts/backup/install_backup_timer.sh`**: one-command installer — copies
  units, patches `NAS_JETSON_NANO_PROJECT_DIR`, calls `daemon-reload`, enables and starts timer
- **`docs/13_MONITORING_RUNBOOK.md` §12-14**: added operational setup sections:
  backup timer install & verify, Uptime Kuma initial monitor list (5 services),
  Netdata Telegram alerts config via `docker exec`

## [1.3.0] — 2026-06-21 · Stage 1G + 1H complete

### Added / Добавлено

- **Monitoring stack deployed** (Stage 1F): Netdata (19999), Uptime Kuma (3001), Portainer (9000)
  running on Jetson via `docker-compose.monitoring.yml`
- **nas_jetson_nano-api** (Stage 1G): FastAPI service on port 8099 with Swagger UI at `/docs`
  — endpoints: `/v1/metrics`, `/v1/containers`, `/v1/logs`, `POST /v1/report/now`
  — pydantic-settings config, JSON structured logging (RotatingFileHandler 10 MB × 5)
  — `docker/compose/docker-compose.nas_jetson_nano-api.yml`
- **Telegram daily health report** (09:00): `scripts/monitoring/nas_jetson_nano-daily-report.sh`
  collects RAM, CPU, disk, container states, HTTP checks; sent via VPS SSH relay
  (`scripts/monitoring/nas_jetson_nano-send-report-telegram.sh`)
  — systemd timer: `nas_jetson_nano-daily-report-telegram.{service,timer}`
- **Docker healthchecks** added to all 10 containers:
  Nextcloud (`curl /status.php`), nextcloud-db/immich-db (`pg_isready`),
  nextcloud-redis/immich-redis (`redis-cli ping` with auth),
  immich-server (`curl /api/server/ping`), llm-gateway/nas_jetson_nano-api (`python3 urllib`),
  netdata (`curl /api/v1/info`), uptime-kuma (`extra/healthcheck`),
  portainer (`disable: true` — scratch image, no shell)
- **`depends_on: condition: service_healthy`** for nextcloud and immich stacks
  — containers wait for DB + Redis to be healthy before starting
- **`mem_limit`** added to all remaining containers:
  llm-gateway 256m, nas_jetson_nano-api 128m, netdata 256m, uptime-kuma 128m, portainer 128m
- **`restart: always`** applied to llm-gateway, nas_jetson_nano-api, and all monitoring services
- **`NETDATA_UPDATE_EVERY=5`** — reduces Netdata CPU from 19.5% to ~4%
- **goss v0.4.9 spec**: `tests/goss/goss.yaml` — 34 tests (ports, services, files, HTTP)
- **docs/21_LOGGING_API.md**: bilingual documentation for logging subsystem and nas_jetson_nano-api
- **docs/22_AUDIT_RESILIENCE.md**: resilience audit report — tools, 10 findings, fixes

### Fixed / Исправлено

- **F-05 (SC2029)**: `nas_jetson_nano-send-report-telegram.sh` — Telegram token no longer appears
  in `ps aux` on VPS; passed via ephemeral SSH env file on remote
- **F-06**: `nas_jetson_nano-daily-report-telegram.service` — added `Restart=on-failure` + `RestartSec=60`
- **F-08 (SC2046)**: `scripts/fetch_external_docs.sh:182` — `$(find ...)` replaced with `xargs`
- **Immich healthcheck endpoint**: corrected from deprecated `/api/server-info/ping`
  to `/api/server/ping` (Immich v1.100+)

### Changed / Изменено

- README: complete rewrite to reflect Stage 1 complete state — all services live,
  accurate architecture diagram, updated stages/docs/stack tables
- `docker-compose.nextcloud.yml`, `docker-compose.immich.yml`: `restart: unless-stopped`
  → `restart: always` for all services (applied live via `docker update`)
- Audit report status updated: F-02 → MEDIUM/Mitigated, F-03/F-04/F-06/F-07 → Fixed

### Added / Добавлено (deep audit 2026-06-20)

- `config/.env.example`: `STORAGE_DEVICE` variable for SMART monitoring; `SAMBA_NAS_PASSWORD`
  for Samba secrets; `VPS_HOST` changed from real IP to placeholder `your.vps.ip.here`
- `docker/compose/docker-compose.stage1.yml`: `mem_limit` on all services (protect 4 GB / no-swap Jetson);
  `immich-microservices` moved to `profiles: [microservices]` (off by default); `immich-redis`
  now password-protected; removed incorrect `depends_on: nextcloud` from `llm-gateway`;
  added `REDIS_PASSWORD` env to `immich-server`
- `.github/workflows/validate-compose.yml`: added CI validation for 3 new compose files
  (`docker-compose.samba.yml`, `docker-compose.monitoring.yml`, `docker/vps/docker-compose.yml`)
- `systemd/jetson-nas-mount.service`: replaced `mount -a` (all fstab) with targeted
  `mount ${STORAGE_ROOT}` + added `Before=docker.service`

### Changed / Изменено (deep audit 2026-06-20)

- `CHANGELOG.md`: fixed repo URL in footer links (`NAS_Jetson_Nano` not `nas-jetson-nano`)
- `README.md`: fixed clone URL; Samba marked as implemented (not "planned"); updated
  Stack, Architecture, Stages, Known Limitations tables; added all new compose files to table;
  removed stale `IMMICH_DISABLE_MACHINE_LEARNING` limitation note
- `PROJECT_TREE.txt`: fully regenerated — now reflects all directories added since v0.1.0
  (`systemd/`, `tests/`, `configs/samba/`, `scripts/storage/`, `scripts/network/`,
  `docker/vps/`, `docs/articles/`, `docs/17-20_*.md`, `docs/decisions/ADR-0002..0004`, etc.)
- `scripts/network/setup_vps_tunnel.sh`: removed hardcoded fallback `193.8.215.130`;
  script now exits with error if `VPS_HOST` is not set in `.env`

### Added / Добавлено

- NAS research report (`docs/18_NAS_RESEARCH_REPORT.md`): analysis of 6 open-source NAS projects
  (JetsonHacks bootFromUSB, OMV, NextcloudPi, RetroNAS, NasberryPi, docker-samba)
- Samba SMB layer: `docker/compose/docker-compose.samba.yml` (crazymax/samba, ARM64 native)
  + `configs/samba/config.yml` (YAML config) + `configs/samba/smb.conf` (native reference)
- `systemd/` directory: `jetson-nas-health.service`, `jetson-nas-health.timer` (6h),
  `nas_jetson_nano-tunnel.service` (autossh), `jetson-nas-mount.service`
- `tests/` directory: `test_samba_config.sh`, `test_mount.sh`, `test_healthcheck.sh`
- `scripts/storage/setup_disk.sh` — USB HDD mount setup with UUID/fstab (NasberryPi pattern)
- `scripts/storage/benchmark_io.sh` — sequential I/O benchmark (JetsonHacks reference speeds)
- VPS integration: reverse SSH tunnel architecture (`docs/plans/VPS_INTEGRATION_PLAN.md`)
  - autossh tunnel script for Jetson Nano (`scripts/network/setup_vps_tunnel.sh`)
  - nginx reverse proxy compose for VPS (`docker/vps/docker-compose.yml`)
  - VPS UFW rules configured (SSH, Amnezia ports, NAS_Jetson_Nano tunnel ports 8080/2283/8090)
  - Docker Compose v5.1.4 installed on VPS
- `config/.env.example`: added VPS_HOST, VPS_USER, VPS_SSH_KEY section
- Monitoring stack analysis and documentation (`docs/17_MONITORING_OBSERVABILITY.md`)
- Docker Compose for monitoring stack (`docker/compose/docker-compose.monitoring.yml`): Netdata + Uptime Kuma + Portainer, ARM64-native
- `prompts/CODEX_MONITORING_PROMPT.md` — bilingual agent prompt for monitoring deployment
- ADR-0002 (storage design), ADR-0003 (networking LAN-only), ADR-0004 (Tailscale external access)
- `docs/plans/TAILSCALE_ACCESS_PLAN.md` — step-by-step Tailscale setup on Jetson Nano
- Full operational bash scripts: `backup_databases.sh`, `restic_backup_example.sh`, `docker_health.sh`, `storage_health.sh`, `docker_update_plan.sh`, `network_health.sh` (in `scripts/network/`)
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1, bilingual RU/EN)
- Existing-data HDD intake documentation: read-only NTFS check flow before using
  `/mnt/storage` or `scripts/storage/setup_disk.sh`
- `docs/19_NETWORK_INVENTORY.md` — sanitized home LAN/router/Jetson/HDD/VPS
  inventory table with secret values kept in `config/.env`
- `docs/20_AGENT_OPERATING_MODEL.md` — standard subagent roles, safety gates,
  report format, and workflow integration

### Changed / Изменено

- `README.md`: added "Old hardware should live" tagline, AI-Assisted badge, updated Samba stack entry
- `AGENTS.md`: added the mandatory subagent operating model pointer and report
  requirements
- `scripts/diagnostics/storage_health.sh`: added SMART monitoring section (smartctl, USB-SATA bridge handling)
- `docs/articles/habr_draft.md`: rewritten with "human vision + AI implementation" angle
- `README.md` переписан по стандартам GitHub open-source проектов: badges, двуязычные секции, ASCII-диаграмма, таблицы стека и документации, Quick Start / README.md rewritten to GitHub open-source standards
- `AGENTS.md` дополнен разделом сетевых ограничений (Amnezia, nas_jetson_nano-lan, Tailscale)
- `docs/13_MONITORING_RUNBOOK.md` расширен: ссылки на мониторинг-стек, таблица алертов
- `docs/16_GITHUB_PUBLICATION.md` дополнен: GitHub Actions, Issue templates, pre-release checklist
- `docker/compose/docker-compose.stage1.yml`: добавлен `immich-microservices`, `IMMICH_DISABLE_MACHINE_LEARNING`, `container_name` для всех сервисов

---

## [0.1.0] - 2026-06-20

### Added / Добавлено

- Initial project structure: `docs/`, `scripts/`, `services/`, `config/`, `docker/`, `prompts/`
- Bilingual documentation (RU/EN) for all stages (Stage 0–3):
  - `docs/00_OVERVIEW.md` — project overview
  - `docs/01_HARDWARE_AUDIT.md` — hardware audit guide
  - `docs/01A_JETSON_SD_BOOTSTRAP.md` — Jetson Nano microSD bootstrap recipe
  - `docs/03_ARCHITECTURE.md` — architecture overview
  - `docs/04_STORAGE_DESIGN.md` — USB HDD storage design
  - `docs/05_NETWORKING_VPN.md` — networking and VPN setup (wg-nas_jetson_nano, EU VPS)
  - `docs/06_NEXTCLOUD_DESIGN.md` — Nextcloud deployment design
  - `docs/07_IMMICH_DESIGN.md` — Immich deployment design (Jetson-safe mode)
  - `docs/08_LLM_GATEWAY_DEEPSEEK.md` — LLM Gateway and DeepSeek API integration
  - `docs/12_BACKUP_RESTORE.md` — backup and restore workflow
  - `docs/14_TEST_PLAN.md` — test plan for staged rollout
  - `docs/16_GITHUB_PUBLICATION.md` — GitHub publication checklist
- Docker Compose drafts (modern Compose spec, top-level `name:` key):
  - `docker/compose/docker-compose.stage1.yml` — full Stage 1 stack
  - `docker/compose/docker-compose.nextcloud.yml` — Nextcloud + PostgreSQL + Redis
  - `docker/compose/docker-compose.immich.yml` — Immich (ML disabled for Jetson Nano)
  - `docker/compose/docker-compose.llm-gateway.yml` — LLM Gateway FastAPI service
- `services/llm-gateway/` — FastAPI privacy shim for DeepSeek API:
  - personal data redaction (email, phone, tokens, private keys)
  - mock mode when `DEEPSEEK_API_KEY` is not set
  - Stage 1 raw-mode block
- `services/backup-api/` — Stage 2 placeholder for Android backup/restore
- `config/.env.example` — public environment variable template (no real secrets)
- `config/llm-policy.yaml` — LLM privacy policy draft
- Diagnostic scripts:
  - `scripts/diagnostics/hardware_audit.sh` — Jetson Nano hardware audit
  - `scripts/diagnostics/docker_health.sh` — Docker and container health check
  - `scripts/diagnostics/storage_health.sh` — USB HDD and mount point health check
- Backup scripts:
  - `scripts/backup/backup_databases.sh` — PostgreSQL dump skeleton
  - `scripts/backup/restic_backup_example.sh` — restic snapshot workflow example
- Security tooling:
  - `scripts/security/check_no_secrets.sh` — pre-publish secret scanner (scans git-tracked files only)
- Agent and Codex prompts:
  - 8 prompt templates in `prompts/CODEX_*` covering Stage 0–2 tasks
- Architecture decision records:
  - `docs/decisions/ADR-0001-nextcloud-immich-deepseek.md` — selected stack rationale
- Project meta files:
  - `README.md` — bilingual project overview (RU/EN)
  - `CONTRIBUTING.md` — contribution rules and good first issues
  - `SECURITY.md` — security policy and LLM privacy rules
  - `AGENTS.md` — agent/Codex onboarding instructions
  - `PROJECT_CONTEXT.md` — fixed decisions and hardware constraints
  - `LICENSE` — MIT License
- GitHub infrastructure:
  - `.github/ISSUE_TEMPLATE/bug_report.md` — bilingual bug report template
  - `.github/ISSUE_TEMPLATE/feature_request.md` — bilingual feature request template
  - `.github/ISSUE_TEMPLATE/config.yml` — issue template configuration
  - `.github/pull_request_template.md` — bilingual PR checklist
  - `.github/CODEOWNERS` — code ownership declaration
  - `.github/workflows/secrets-check.yml` — CI secret scanner on push/PR
  - `.github/workflows/validate-compose.yml` — CI Docker Compose validation

[Unreleased]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.9...v1.4.0
[1.3.9]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.8...v1.3.9
[1.3.8]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.7...v1.3.8
[1.3.4]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/releases/tag/v1.3.0
[0.1.0]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/releases/tag/v0.1.0
