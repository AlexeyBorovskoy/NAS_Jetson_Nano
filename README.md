# NAS_Jetson_Nano

> **Rename status:** the repository and source identifiers use `NAS_Jetson_Nano`. The live Jetson runtime has not been renamed or restarted yet; its controlled migration is tracked in [docs/MIGRATION_TO_NAS_JETSON_NANO.md](docs/MIGRATION_TO_NAS_JETSON_NANO.md).
### _Old hardware should live_ · _Старое железо должно жить_

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/AlexeyBorovskoy/NAS_Jetson_Nano?color=brightgreen)](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/releases)
[![Platform](https://img.shields.io/badge/Platform-Jetson%20Nano-76b900)](https://developer.nvidia.com/embedded/jetson-nano-developer-kit)
[![Docker](https://img.shields.io/badge/Docker%20Compose-v2-2496ED)](docker/compose/)
[![AI-Assisted](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai/code)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)  
[![Stars](https://img.shields.io/github/stars/AlexeyBorovskoy/NAS_Jetson_Nano?style=social)](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/stargazers)
[![Discussions](https://img.shields.io/github/discussions/AlexeyBorovskoy/NAS_Jetson_Nano)](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/discussions)
[![Issues](https://img.shields.io/github/issues/AlexeyBorovskoy/NAS_Jetson_Nano)](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/issues)
[![CI](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/actions/workflows/secrets-check.yml/badge.svg)](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/actions/workflows/secrets-check.yml)
[![Shellcheck](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/actions/workflows/shellcheck.yml/badge.svg)](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/actions/workflows/shellcheck.yml)

> 🇷🇺 В ящике лежал NVIDIA Jetson Nano — купил когда-то для экспериментов, поиграл неделю и забыл.
> Сын принёс плату DEXP с 232 ГБ памяти — «папа, пригодится». Пригодилась.
> Вместо того чтобы покупать что-то новое — взял то, что уже было, и сделал из этого домашний сервер.
> Заменил Google Фото, Google Drive и Яндекс.Диск. Задумал я — реализовал [Claude Code](https://claude.ai/code). **Новичок тоже справится.**
>
> 🇬🇧 Had an NVIDIA Jetson Nano sitting in a drawer — bought it for experiments, tinkered for a week, then forgot about it.
> My son brought a DEXP board with 232 GB storage — "dad, you'll need this". He was right.
> Instead of buying new hardware — used what was already there and turned it into a proper home server.
> Replaced Google Photos, Google Drive, and Yandex.Disk. My vision — [Claude Code](https://claude.ai/code) did the implementation. **Beginners can do this too.**

**Если проект полезен — поставь ⭐ звезду, это помогает другим его найти.**  
**If you find this useful — please ⭐ star this repo so others can discover it.**

![NAS_Jetson_Nano — реальный стенд](assets/photos/test_sys.jpg)
*Jetson Nano на роутере + DEXP-плата от сына (232 ГБ) · реальный стенд проекта*

---

## Быстрый старт / Quick Start (TL;DR)

> 🇷🇺 Команды ниже разворачивают основные сервисы с конфигурацией проекта по умолчанию.
> 🇬🇧 The following commands deploy the core services using the default project configuration.

### Требования / Requirements

🇷🇺 Перед началом убедитесь, что у вас есть: · 🇬🇧 Before starting, make sure you have:

- NVIDIA Jetson Nano, Raspberry Pi 4/5 или другой совместимый мини-ПК / or another compatible mini-PC
- Docker Engine 20.10+
- Docker Compose v2
- VPS — нужен только для внешнего доступа / required only for external access

```bash
git clone https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano.git ~/nas_jetson_nano
cd ~/nas_jetson_nano
cp config/.env.example config/.env && nano config/.env   # заполнить пароли
docker compose -f docker/compose/docker-compose.nextcloud.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.immich.yml   --env-file config/.env up -d
```

> 📖 Подробный гайд / For the complete setup guide: [Быстрый старт / Full Quick Start](#быстрый-старт--quick-start) ↓

---

## Зачем это нужно / Why

> 🇷🇺 Семейные фото копились в Google и Xiaomi Cloud. В какой-то момент понял, что не хочу чтобы они были у кого-то ещё.
> Не хотелось тратить деньги на подписки и покупать новое железо, когда старое просто лежит.
> Решение: собрать собственный облачный сервер из того что есть.

> 🇬🇧 Family photos were piling up in Google and Xiaomi Cloud. At some point I realised I didn't want them sitting on someone else's server.
> Didn't want to keep paying for subscriptions or buy new hardware when old hardware was just sitting there.
> Solution: build a home cloud from what I already had.

| Было / Before | Стало / After |
|---|---|
| Google Фото — ваши фото у Google | **Immich** — личный фотоархив дома + Android авто-загрузка |
| Google Drive / Яндекс.Диск | **Nextcloud** — файлы, WebDAV, Android авто-синхронизация |
| Google Контакты / Google Calendar | **Nextcloud Contacts + Calendar** — CardDAV/CalDAV через DAVx⁵ |
| Xiaomi Cloud фото-бэкап | **Immich** — всё хранится дома, не у Xiaomi |
| DEXP-плата (232 ГБ) — лежала без дела, принёс сын | **Samba NAS + основное хранилище** |
| ChatGPT / Claude API | **LLM Gateway** — локальный AI-ассистент, данные не уходят |
| Облачный мониторинг | **Beszel** — история CPU/RAM/Disk/Net + Telegram алерты |

---

## Содержание / Table of Contents

- [О проекте / About](#о-проекте--about)
- [Для кого / Who is this for](#для-кого--who-is-this-for)
- [Что работает прямо сейчас / What's running](#что-работает-прямо-сейчас--whats-running)
- [Архитектура / Architecture](#архитектура--architecture)
- [Стек / Stack](#стек--stack)
- [Требования / Prerequisites](#требования--prerequisites)
- [Быстрый старт / Quick Start](#быстрый-старт--quick-start)
- [Конфигурация / Configuration](#конфигурация--configuration)
- [Этапы / Stages](#этапы--stages)
- [Документация / Documentation](#документация--documentation)
- [Безопасность / Security](#безопасность--security)
- [Статьи и публикации / Articles](#статьи-и-публикации--articles)
- [Вклад / Contributing](#вклад--contributing)
- [Лицензия / License](#лицензия--license)


---

## О проекте / About

> 🇷🇺 Русский

Всё началось с того, что в ящике лежал NVIDIA Jetson Nano, купленный несколько лет назад для экспериментов. Поиграл, отложил и забыл. Сын принёс плату DEXP с 232 ГБ памяти — «папа, пригодится». Покупать готовый NAS или новое железо не хотелось.

Решил попробовать сделать домашний сервер из того, что уже есть. Jetson Nano оказался вполне достаточным: 4 ГБ RAM, ARM64, умеет в Docker. SSD смонтирован в `/mnt/storage` (229 GB), 13 контейнеров `Up (healthy)`. USB autosuspend отключён на уровне ядра. HTTPS добавлен на VPS nginx. SSD подключён через **JMS583** (USB 3.0 SuperSpeed, 5 Gbps, 250 MB/s write). Семейный чат работает через Nextcloud Talk — 5 участников. NAS_Jetson_Nano API v0.6.0 живёт на `:8099/docs` (Talk, Photos, Users, Actions).

**NAS_Jetson_Nano** — это не инсталлятор в один клик. Это инженерный шаблон: документация, Docker Compose, диагностические скрипты, systemd-юниты и промпты для агентов, позволяющие разворачивать платформу малыми проверяемыми шагами.

Принципы:

- **Приватность прежде всего** — фото, видео, контакты, календарь и резервные копии не покидают домашнюю сеть.
- **Только LAN + обратный SSH-тоннель** — сервисы недоступны напрямую из интернета; CGNAT обходится через VPS.
- **Малые шаги** — каждый блок разворачивается отдельно и проверяется перед следующим.
- **Без секретов в git** — реальные `.env`, токены, ключи и персональные данные не попадают в репозиторий.
- **Устойчивость** — `restart: always`, mem_limit, Docker healthchecks, ежедневный Telegram-отчёт, автоматический бэкап БД.

> 🇬🇧 English

It started with an NVIDIA Jetson Nano sitting in a drawer — bought years ago for experiments, tinkered with it once, then forgot about it. My son brought a DEXP board with 232 GB storage — "dad, you'll need this". Didn't want to buy a ready-made NAS or new hardware.

Decided to try building a home server from what was already there. The Jetson Nano turned out to be perfectly capable: 4 GB RAM, ARM64, Docker-ready. The DEXP board became the target USB storage. The SSD is mounted at `/mnt/storage` (229 GB), all 13 containers are `Up (healthy)`, USB autosuspend is disabled at kernel level, HTTPS is live on VPS nginx. The **JMS583** enclosure (USB 3.0 SuperSpeed, 5 Gbps, 250 MB/s write) replaced the original DEXP/RTL9210B-CG bridge. Family chat runs on Nextcloud Talk (5 members). NAS_Jetson_Nano API v0.6.0 is live at `:8099/docs` with Talk, Photos, Users, and Actions endpoints.

**NAS_Jetson_Nano** is not a one-command installer. It is an engineering template with documentation, Docker Compose files, diagnostics, systemd units, and agent prompts for safe, step-by-step deployment.

Principles:

- **Privacy first** — photos, videos, contacts, calendars, and backups never leave the home network.
- **LAN + reverse SSH tunnel only** — services are not exposed directly to the internet; CGNAT is bypassed via VPS relay.
- **Small steps** — every deployment block is verified before moving to the next.
- **No real secrets in git** — `.env`, tokens, API keys, and personal data are excluded from the repository.
- **Resilience** — `restart: always`, mem_limit, Docker healthchecks, daily Telegram health report, automated DB backup timer.

---

## Для кого / Who is this for

> 🇷🇺 Если у вас где-то лежит Jetson Nano, Raspberry Pi 4/5 или любой мини-ПК — и он либо не используется, либо используется по крайней необходимости — этот проект для вас. Не нужно быть DevOps-инженером. Нужно быть готовым разбираться шаг за шагом.
>
> Мне не нужна была экспертиза в Docker и systemd — достаточно было сформулировать задачи для [Claude Code](https://claude.ai/code). Агент генерировал код, отлаживал, тестировал, писал документацию. Я проверял, принимал решения, говорил что делать дальше. Получился рабочий сервер.
>
> Весь лог решений открыт: промпты (`docs/prompts/`), архитектурные решения (`docs/decisions/`), CHANGELOG с каждым шагом.

> 🇬🇧 If you have a Jetson Nano, Raspberry Pi 4/5, or any mini-PC sitting somewhere — either unused or barely used — this project is for you. You don't need to be a DevOps engineer. You just need to be willing to work through it step by step.
>
> I didn't need expertise in Docker or systemd — just the ability to formulate tasks for [Claude Code](https://claude.ai/code). The agent wrote the code, debugged it, tested it, and documented everything. I reviewed, made decisions, and directed what to do next. The result: a working home server.
>
> The full decision log is open: agent prompts (`docs/prompts/`), architecture decisions (`docs/decisions/`), CHANGELOG with every step.

---

## Что работает прямо сейчас / What's running

> Состояние на 2026-06-29 / State as of 2026-06-29 · **Stage 1 fully operational**
> Jetson доступен через VPS reverse tunnel. SSD смонтирован в `/mnt/storage` (229 GB, ~222 GB free).
> `storage_preflight.sh` — errors=0, warnings=0. Все 13 контейнеров `Up (healthy)`.
> USB autosuspend отключён: `usbcore.autosuspend=-1` **подтверждён после ребута**.
> Beszel Hub на VPS:8091, оба агента Up (Jetson · VPS).
> nginx HTTPS: Nextcloud :8443 · Immich :2443 · LLM :9443 (самоподписанный сертификат, 10 лет).
> Android: Immich ✅ (6484 фото, 210 видео) · Nextcloud ✅ · DAVx⁵ ✅ · Talk ✅.
> USB SSD: **JMS583** ✅ (152d:a583, USB 3.0 SuperSpeed, 5 Gbps, write 250 MB/s, UAS quirk активен).
> Nextcloud Talk: группа «Семья» ✅ (5 участников: admin, olga, ivan, ulyana, anna).
> Исторический снимок / Historical snapshot (2026-06-29): NAS_Jetson_Nano API **v0.6.0**, Talk, Users, Photos and Actions endpoints, goss 40/40. Требуется повторная проверка для подтверждения текущего состояния / A rerun is required to confirm current state.

| Сервис / Service | Порт / Port | Доступ / Access | Статус / Status |
|---|---|---|---|
| Nextcloud | 8080 / **8443** | VPS `193.8.215.130:8080` · HTTPS `:8443` + LAN | ✅ Live |
| Immich | 2283 / **2443** | VPS `193.8.215.130:2283` · HTTPS `:2443` + LAN | ✅ Live |
| LLM Gateway | 8090 / **9443** | VPS `193.8.215.130:8090` · HTTPS `:9443` + LAN | ✅ Live |
| DAVx⁵ CardDAV/CalDAV | 8443 | `https://193.8.215.130:8443/remote.php/dav` | ✅ Live · Android sync |
| nas_jetson_nano-api (Swagger) | 8099 | LAN `192.168.0.50:8099/docs` | ✅ Live |
| Samba NAS | 445/139 | LAN only (192.168.0.0/24) | ✅ Live, storage-backed |
| Netdata | 19999 | LAN `192.168.0.50:19999` | ✅ Live |
| Uptime Kuma | 3001 | LAN `192.168.0.50:3001` | ✅ Live · 5 monitors configured |
| Portainer | 9000 | LAN `192.168.0.50:9000` | ✅ Live · admin configured |
| Beszel Hub | 8091 | VPS `193.8.215.130:8091` | ✅ Live · Jetson 17% CPU · VPS 2% CPU |
| Beszel Agent Jetson | 45876 | Jetson internal | ✅ Live · systemd, arm64 v0.18.7 |
| Beszel Agent VPS | 45877 | VPS internal | ✅ Live · systemd, amd64 v0.18.7 |
| VPS nginx (HTTP+HTTPS) | — | VPS 193.8.215.130 | ✅ Live · self-signed TLS 10y |
| autossh tunnel | — | Jetson → VPS persistent | ✅ Live |
| Telegram daily report | — | Bot → personal chat | ✅ Live (09:00) + Beszel data |
| DB backup timer | — | pg_dump → /mnt/storage/backups | ✅ Live; fail-closed guard |
| USB storage watchdog | udev | udev rules + systemd timers | ✅ active (nas_jetson_nano-usb-watchdog.timer) |
| Android mobile sync | — | Immich app + DAVx⁵ + Nextcloud + Talk | ✅ Immich (6484 фото/210 видео) · Nextcloud · DAVx⁵ · Talk |
| Nextcloud Talk | 8080/8443 | Семейный чат, 5 участников | ✅ Live · группа «Семья» (admin, olga, ivan, ulyana, anna) |

> **Хранилище / Storage:** `/mnt/storage` — JMS583 USB 3.0 SSD (152d:a583, 229 GB ext4, write 250 MB/s, UAS quirk активен).
> После переподключения / After reconnect: виден как / visible as `/dev/sda1`, смонтирован / mounted `rw,noatime`.
> `e2fsck -f -n` вернул `0`, `storage_preflight.sh` завершился без ошибок / completed without errors.
> История инцидента / Incident log: [docs/plans/STORAGE_INCIDENT_2026-06-23.md](docs/plans/STORAGE_INCIDENT_2026-06-23.md).
> Аудит надёжности / Reliability audit: [docs/plans/RELIABILITY_AUDIT_2026-06-23.md](docs/plans/RELIABILITY_AUDIT_2026-06-23.md).

---

## Архитектура / Architecture

```
Интернет / Internet
        |
        | (публичный IP / public IP)
        v
  [ VPS 193.8.215.130 — Вена / Vienna ]
        |
        |  nginx (host network, docker) — HTTP + HTTPS (self-signed TLS)
        |  :8080 / :8443  → 127.0.0.1:18080 → tunnel → Jetson:8080  (Nextcloud)
        |  :2283 / :2443  → 127.0.0.1:12283 → tunnel → Jetson:2283  (Immich)
        |  :8090 / :9443  → 127.0.0.1:18090 → tunnel → Jetson:8090  (LLM Gateway)
        |  :10022          → tunnel → Jetson:22                       (SSH management / SSH управление)
        |  :8443/remote.php/dav → CardDAV/CalDAV (DAVx⁵ Android sync)
        |
        |  ↑ autossh reverse SSH tunnel (CGNAT bypass / обход CGNAT)
        |
  [ Домашний роутер / Home router ]
        |  (static DHCP / статический DHCP: 192.168.0.50)
        v
  [ Jetson Nano 4GB · Ubuntu 18.04 · 192.168.0.50 ]
        |
        +-- Nextcloud (8080) · PostgreSQL 16 · Redis 7
        |
        +-- Immich (2283) · PostgreSQL 16 + pgvecto-rs · Redis 7
        |   IMMICH_DISABLE_MACHINE_LEARNING=true (Jetson Nano 4GB safe mode)
        |
        +-- LLM Gateway / FastAPI (8090)
        |     +-- [ DeepSeek API ] — privacy-filtered (PII redaction / редакция персданных)
        |
        +-- nas_jetson_nano-api / FastAPI (8099) · Swagger UI /docs · v0.6.0
        |     · /v1/metrics · /v1/containers · /v1/storage · /v1/logs
        |     · /v1/talk/rooms · POST /v1/talk/notify
        |     · /v1/users · /v1/photos/stats
        |     · POST /v1/actions/containers/{name}/restart · POST /v1/actions/backup/now
        |
        +-- Samba NAS (445, LAN only)
        |     iptables: LAN only / разрешён только 192.168.0.0/24
        |
        +-- Netdata (19999)    — CPU, RAM, Disk, Docker, Jetson temp / темп Jetson
        +-- Uptime Kuma (3001) — 5 HTTP monitors / мониторов + Telegram alerts
        +-- Portainer (9000)   — Docker management UI (admin configured / настроен)
        |
        +-- systemd: nas_jetson_nano-tunnel.service       (autossh, restart=always)
        +-- systemd: nas_jetson_nano-daily-report-telegram.timer  (09:00 daily / ежедневно)
        +-- systemd: nas_jetson_nano-backup.timer         (03:00 daily / ежедневно, pg_dump)
        +-- systemd: jetson-nas-health.timer   (SMART HDD monitoring / мониторинг HDD, 6h)
        +-- systemd: beszel-agent.service      (monitoring → Beszel Hub at / на VPS:8091)
        +-- udev:    usb-storage.quirks=152d:a583:u (UAS quirk для JMS583, в extlinux.conf)
        +-- systemd: nas_jetson_nano-usb-preboot.service  (power cycle SSD порта при boot)
        +-- systemd: nas_jetson_nano-usb-monitor.service  (Telegram alert при USB ошибках)
        +-- systemd: nas_jetson_nano-ssd-recovery.service (udev sda1 add → mount → Docker)
        +-- smartd:  /dev/sda monitoring       (S.M.A.R.T., weekly self-test)

/mnt/storage  (JMS583 USB 3.0 SSD 229 GB ext4; mounted, fsck/preflight OK; write 250 MB/s)
  ├── nextcloud/data
  ├── immich/library
  ├── db/
  │   ├── nextcloud-postgres    (~373 MB)
  │   └── immich-postgres
  ├── backups/
  │   └── database-dumps/       (pg_dump · gzip · 7-day rotation / ротация 7 дней)
  └── samba/public
```

**Docker Compose файлы:**

| Файл / File | Назначение / Purpose |
|---|---|
| `docker/compose/docker-compose.nextcloud.yml` | Nextcloud + PostgreSQL + Redis |
| `docker/compose/docker-compose.immich.yml` | Immich + PostgreSQL + Redis |
| `docker/compose/docker-compose.llm-gateway.yml` | LLM Gateway (FastAPI) |
| `docker/compose/docker-compose.samba.yml` | Samba NAS (ARM64, SMB2+) |
| `docker/compose/docker-compose.monitoring.yml` | Netdata + Uptime Kuma + Portainer |
| `docker/compose/docker-compose.nas_jetson_nano-api.yml` | nas_jetson_nano-api (FastAPI, Swagger, JSON logs) |
| `docker/vps/docker-compose.yml` | nginx reverse proxy на VPS (`network_mode: host`) |

---

## Стек / Stack

| Область / Area | Компонент / Component | Версия / Version | Роль / Role |
|---|---|---|---|
| Файлы и документы / Files & docs | Nextcloud | latest (apache) | File cloud, WebDAV, CalDAV, CardDAV |
| Фото и видео / Photos & video | Immich | release | Photo/video archive, Android sync |
| Базы данных / Databases | PostgreSQL | 16 / pgvecto-rs | Nextcloud DB + Immich DB |
| Кэш / Cache & queues | Redis | 7-alpine | Nextcloud cache + Immich queue |
| Локальный NAS / Local NAS | Samba (crazymax/samba) | latest ARM64 | SMB2+ for Windows/Android/macOS |
| LLM-шлюз / LLM Gateway | FastAPI LLM Gateway | — | Privacy shim, PII redaction / редакция персданных |
| LLM API | DeepSeek API | deepseek-chat | Admin assistant / Помощник администратора |
| Admin API | nas_jetson_nano-api (FastAPI) | v0.6.0 | Metrics, logs, containers, Talk, Users, Photos, Actions — Swagger UI |
| Тоннель / Tunnel | autossh + systemd | — | Reverse SSH via CGNAT → VPS |
| VPS прокси / VPS proxy | nginx:alpine | — | Reverse proxy to public ports |
| Мониторинг / Monitoring | Netdata | latest ARM64 | CPU, RAM, Disk, Docker, Jetson temp |
| Uptime | Uptime Kuma | 1 | HTTP uptime + Telegram alerts (5 monitors) |
| Docker UI | Portainer CE | latest | Web UI for Docker management |
| Ежедневный отчёт / Daily report | bash + SSH relay + Telegram | — | 09:00 cluster health report |
| Бэкап БД / DB backup | bash pg_dump + gzip | — | 03:00 daily, 7-day rotation |
| Тестирование / Testing | goss v0.4.9 (ARM64) | — | Infrastructure state tests (40 tests) |
| Здоровье системы / System health | systemd timers + SMART | — | 6h diagnostics + HDD health |
| Unified monitoring | Beszel | 0.18.7 | Hub at VPS:8091, Agent Jetson:45876 + VPS:45877 |
| Android sync | Immich app + DAVx⁵ + Nextcloud | — | Photos / contacts / calendar / files; [docs/android/](docs/android/) |
| Бэкапы файлов / File backups | restic | — | Stage 3 (scripts ready / заготовка готова) |
| Android backup API | services/backup-api | — | Stage 2 placeholder |

---

## Требования / Prerequisites

**Железо / Hardware:**

| Компонент / Component | Рекомендация / Recommendation |
|---|---|
| Вычислительный узел / Compute node | NVIDIA Jetson Nano Developer Kit (4 GB) · or Raspberry Pi 4/5 · or any mini-PC |
| Системный диск / System disk | microSD 64 GB (Class 10 / A2) |
| Диск данных / Data disk | USB SSD/HDD — any USB drive; in this project: DEXP 232 GB (son's old board) |
| Сеть / Network | Home LAN, static DHCP lease |
| Внешний доступ / External access | VPS (any; tested on Ubuntu 24.04, 1 vCPU, 2 GB RAM) |

**ПО на Jetson / Software on Jetson:**

- L4T / JetPack 4.x (Ubuntu 18.04) · or Ubuntu 22.04 (on RPi / mini-PC)
- Docker Engine 20.10+, Docker Compose v2
- autossh (`apt install autossh`)
- curl, openssl (`apt install curl openssl`)
- SSH-ключ для VPS в `~/.ssh/` / SSH key for VPS in `~/.ssh/`

**ПО на VPS / Software on VPS:**

- Docker + Docker Compose v2
- UFW: открыть порты / open ports 8080, 2283, 8090, **8443, 2443, 9443**, 10022 (и / and 22 для SSH / for SSH)
- SSH: разрешить вход от Jetson-ключа / allow login from Jetson key
- nginx HTTPS: запустить / run `scripts/setup/install_nginx_vps.sh` после деплоя / after deploy

---

## Быстрый старт / Quick Start

### 1. Клонировать / Clone

```bash
git clone https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano.git ~/nas_jetson_nano
cd ~/nas_jetson_nano
cp config/.env.example config/.env
chmod 600 config/.env
nano config/.env   # заполнить пароли, пути, DeepSeek API key
```

### 2. Настроить VPS / Setup VPS

```bash
# На VPS:
mkdir -p /opt/nas_jetson_nano
scp -r docker/vps/ root@<VPS_IP>:/opt/nas_jetson_nano/
ssh root@<VPS_IP> "cd /opt/nas_jetson_nano/vps && docker compose up -d"
```

### 3. Настроить тоннель на Jetson / Setup tunnel on Jetson

```bash
# На Jetson:
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@<VPS_IP>

sudo cp systemd/nas_jetson_nano-tunnel.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now nas_jetson_nano-tunnel.service
```

### 4. Запустить сервисы / Start services

```bash
# На Jetson:
cd ~/nas_jetson_nano
docker compose -f docker/compose/docker-compose.nextcloud.yml   --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.immich.yml      --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.llm-gateway.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.monitoring.yml  --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml    --env-file config/.env up -d
```

### 5. Настроить Telegram-отчёты / Setup Telegram reports

```bash
# На Jetson:
sudo mkdir -p /etc/nas_jetson_nano-monitor /var/log/nas_jetson_nano-monitor
sudo cp scripts/monitoring/nas_jetson_nano-daily-report.sh /usr/local/sbin/
sudo cp scripts/monitoring/nas_jetson_nano-send-report-telegram.sh /usr/local/sbin/
sudo chmod +x /usr/local/sbin/nas_jetson_nano-*.sh

sudo tee /etc/nas_jetson_nano-monitor/telegram.env <<EOF
TELEGRAM_BOT_TOKEN=<your-token>
TELEGRAM_CHAT_ID=<your-chat-id>
EOF
sudo chmod 600 /etc/nas_jetson_nano-monitor/telegram.env

sudo cp systemd/nas_jetson_nano-daily-report-telegram.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nas_jetson_nano-daily-report-telegram.timer
```

### 6. Автоматическая настройка UI и бэкапов / Automated UI + backup setup

```bash
# На Jetson:
# Бэкап таймер (pg_dump · 03:00 ежедневно)
bash scripts/backup/install_backup_timer.sh

# Portainer admin (генерирует пароль автоматически)
bash scripts/monitoring/setup_portainer.sh

# Uptime Kuma: admin + 5 мониторов
docker run --rm --network host \
  -v ~/nas_jetson_nano/scripts/monitoring/setup_uptime_kuma.py:/setup.py:ro \
  -e UPTIME_KUMA_ADMIN_USER=admin \
  -e UPTIME_KUMA_ADMIN_PASSWORD=<your-password> \
  -e JETSON_LAN_IP=192.168.0.50 \
  python:3.12-slim bash -c 'pip install uptime-kuma-api -q && python3 /setup.py'
```

### 7. Проверить / Verify

🇷🇺 Команды ниже проверяют, что каждый основной сервис работает корректно после развёртывания. · 🇬🇧 Run the following commands to verify that each core service is running correctly after deployment.

```bash
curl -sf http://localhost:8080/status.php         # Nextcloud → {"installed":true,...}
curl -sf http://localhost:2283/api/server/ping    # Immich → {"res":"pong"}
curl -sf http://localhost:8090/health             # LLM Gateway → {"status":"ok"}
curl -sf http://localhost:8099/healthcheck        # nas_jetson_nano-api → {"status":"ok"}
curl -sf http://localhost:19999/api/v1/info       # Netdata → {...}

goss -g tests/goss/goss.yaml validate --format tap   # 40 infrastructure tests
```

🇷🇺 После развёртывания доступны веб-интерфейсы: · 🇬🇧 After deployment, you can access the following web interfaces (Web UI):
- **Swagger:** http://192.168.0.50:8099/docs
- **Netdata:** http://192.168.0.50:19999
- **Uptime Kuma:** http://192.168.0.50:3001
- **Portainer:** http://192.168.0.50:9000

Полный план тестирования / Full test plan: [docs/14_TEST_PLAN.md](docs/14_TEST_PLAN.md).  
Подготовка microSD / microSD setup: [docs/01A_JETSON_SD_BOOTSTRAP.md](docs/01A_JETSON_SD_BOOTSTRAP.md).  
Операционный runbook / Operations runbook: [docs/13_MONITORING_RUNBOOK.md](docs/13_MONITORING_RUNBOOK.md).

---

## Конфигурация / Configuration

Все переменные — в `config/.env` (не коммитится) / All variables go in `config/.env` (not committed). Шаблон / Template: `config/.env.example`.

```bash
# Хранилище
STORAGE_ROOT=/mnt/storage
NEXTCLOUD_DATA=/mnt/storage/nextcloud/data
IMMICH_UPLOAD_LOCATION=/mnt/storage/immich/library
BACKUP_ROOT=/mnt/storage/backups

# Базы данных
NEXTCLOUD_DB_PASSWORD=changeme
IMMICH_DB_PASSWORD=changeme
REDIS_PASSWORD=changeme

# VPS tunnel
VPS_HOST=your.vps.ip
VPS_USER=root
VPS_SSH_KEY=/home/admin/.ssh/id_ed25519

# LLM Gateway
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
IMMICH_DISABLE_MACHINE_LEARNING=true   # обязательно для Jetson Nano 4GB
```

Никогда не коммитьте реальный `config/.env`. Он в `.gitignore`. / Never commit the real `config/.env`. It is listed in `.gitignore`.

---

## Этапы / Stages

| Этап / Stage | Содержание / Content | Статус / Status |
|---|---|---|
| Stage 0 | microSD, первый boot, SSH, USB device mode | ✅ Задокументировано |
| Stage 1A | Hardware audit, DEXP USB storage setup, Samba NAS | ✅ **Storage recovered; reboot verified** |
| Stage 1B | Nextcloud + PostgreSQL + Redis | ✅ **Recovered; DB/Redis healthy; reboot verified** |
| Stage 1C | Immich (ML отключён для Jetson) | ✅ **Развёрнут и работает** |
| Stage 1D | LLM Gateway + DeepSeek | ✅ **Развёрнут и работает** |
| Stage 1E | VPS + reverse SSH tunnel (autossh) | ✅ **Работает, nginx на VPS** |
| Stage 1F | Мониторинг (Netdata, Uptime Kuma, Portainer) | ✅ **Развёрнут и работает** |
| Stage 1G | nas_jetson_nano-api (FastAPI, Swagger, JSON logs) + Telegram отчёт | ✅ **Развёрнут и работает** |
| Stage 1H | Resilience audit: healthchecks, mem_limit, goss | ✅ **8/10 findings fixed** |
| Stage 1 Ops | Uptime Kuma (5 мониторов) + Portainer (admin) + бэкап-таймер | ✅ **Monitoring + fail-closed backup live** |
| Stage 2 | Android sync: Immich + DAVx⁵ + Nextcloud + Talk + миграция с Google | ✅ **Работает** · [docs/android/](docs/android/) · семья подключена |
| Stage 3 | Backup / restore (restic full + pg\_dump) | 🔜 Скрипты готовы |
| Stage 3.1 | USB HDD: резервное расширение хранилища (NTFS + ext4 гибрид) | 📋 Готово к подключению |
| Stage 4 | Analytics, RAG, fallback LLM providers | 📋 Будущее |

---

## Документация / Documentation

| Файл / File | Описание / Description |
|---|---|
| [docs/00_OVERVIEW.md](docs/00_OVERVIEW.md) | Обзор концепции / Project concept overview |
| [docs/01_HARDWARE_AUDIT.md](docs/01_HARDWARE_AUDIT.md) | Аппаратный аудит Jetson Nano |
| [docs/01A_JETSON_SD_BOOTSTRAP.md](docs/01A_JETSON_SD_BOOTSTRAP.md) | Подготовка microSD, первый boot |
| [docs/03_ARCHITECTURE.md](docs/03_ARCHITECTURE.md) | Архитектурная схема |
| [docs/04_STORAGE_DESIGN.md](docs/04_STORAGE_DESIGN.md) | Дизайн хранилища (USB HDD, mount, fstab) |
| [docs/05_NETWORKING_VPN.md](docs/05_NETWORKING_VPN.md) | LAN/VPN-модель, тоннели, порты |
| [docs/06_NEXTCLOUD_DESIGN.md](docs/06_NEXTCLOUD_DESIGN.md) | Дизайн Nextcloud |
| [docs/07_IMMICH_DESIGN.md](docs/07_IMMICH_DESIGN.md) | Дизайн Immich (Jetson-safe) |
| [docs/08_LLM_GATEWAY_DEEPSEEK.md](docs/08_LLM_GATEWAY_DEEPSEEK.md) | LLM Gateway и DeepSeek API |
| [docs/12_BACKUP_RESTORE.md](docs/12_BACKUP_RESTORE.md) | Backup и restore workflow |
| [docs/13_MONITORING_RUNBOOK.md](docs/13_MONITORING_RUNBOOK.md) | Runbook: диагностика, бэкапы, Uptime Kuma, Netdata |
| [docs/14_TEST_PLAN.md](docs/14_TEST_PLAN.md) | План тестирования по этапам |
| [docs/17_MONITORING_OBSERVABILITY.md](docs/17_MONITORING_OBSERVABILITY.md) | Анализ инструментов мониторинга |
| [docs/19_NETWORK_INVENTORY.md](docs/19_NETWORK_INVENTORY.md) | Сетевой паспорт стенда |
| [docs/20_AGENT_OPERATING_MODEL.md](docs/20_AGENT_OPERATING_MODEL.md) | Операционная модель субагентов |
| [docs/21_LOGGING_API.md](docs/21_LOGGING_API.md) | JSON-логирование и nas_jetson_nano-api (Swagger) |
| [docs/22_AUDIT_RESILIENCE.md](docs/22_AUDIT_RESILIENCE.md) | Аудит надёжности: goss, shellcheck, итоги |
| [docs/23_GITHUB_INTEGRATION.md](docs/23_GITHUB_INTEGRATION.md) | GitHub CLI + Claude Code интеграция, AI DevOps workflow |
| [docs/24_CLIENT_SETUP.md](docs/24_CLIENT_SETUP.md) | **Подключение устройств: Android, Windows, Linux** |
| [docs/android/ANDROID_SETUP.md](docs/android/ANDROID_SETUP.md) | **Настройка Xiaomi MIUI/HyperOS** — Immich, Nextcloud, DAVx⁵, HTTPS через VPS |
| [docs/android/GOOGLE_MIGRATION.md](docs/android/GOOGLE_MIGRATION.md) | **Миграция с Google** — Google Takeout → Immich/Nextcloud/DAVx⁵, чеклист |
| [docs/android/XIAOMI_MIUI_QUIRKS.md](docs/android/XIAOMI_MIUI_QUIRKS.md) | Специфика MIUI/HyperOS — battery whitelist, автозапуск, блокировка в RAM |
| [docs/decisions/ADR-0006-vps-nginx-https.md](docs/decisions/ADR-0006-vps-nginx-https.md) | ADR-0006: HTTPS на VPS nginx — почему self-signed, не Tailscale, не Let's Encrypt |
| [docs/metrics/GITHUB_TRAFFIC.md](docs/metrics/GITHUB_TRAFFIC.md) | Ежедневный мониторинг GitHub трафика, клонов, звёзд — целевые метрики |
| [docs/plans/STORAGE_INCIDENT_2026-06-23.md](docs/plans/STORAGE_INCIDENT_2026-06-23.md) | USB storage incident: `error -71`, recovery status, Nextcloud controlled start |
| [docs/plans/RELIABILITY_AUDIT_2026-06-23.md](docs/plans/RELIABILITY_AUDIT_2026-06-23.md) | Live reliability audit: fsck/preflight, boot guard, restart policy, remaining risks |
| [docs/plans/VPS_INTEGRATION_PLAN.md](docs/plans/VPS_INTEGRATION_PLAN.md) | План интеграции VPS + тоннель |
| [AGENTS.md](AGENTS.md) | Правила для Codex/агентов |
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | Зафиксированные решения и ограничения |
| [docs/architecture_nas_jetson_nano.md](docs/architecture_nas_jetson_nano.md) | Полная архитектурная карта (Mermaid) |

---

## Безопасность / Security

🇷🇺
- Не коммитьте реальные `.env`, ключи, токены, дампы и персональные данные.
- LLM Gateway блокирует отправку фото, видео, контактов и ключей во внешний API.
- Samba доступна только из локальной сети (`iptables`: 192.168.0.0/24 → 445/139).
- VPS nginx слушает публичные порты, но данные хранятся только на Jetson.
- Telegram-токен передаётся через зашифрованный SSH-туннель, не раскрывается в `ps aux` на VPS.

🇬🇧
- Do not commit real `.env` files, keys, tokens, database dumps, or personal data.
- LLM Gateway blocks sending photos, videos, contacts, and credentials to external APIs.
- Samba is LAN-only (`iptables`: 192.168.0.0/24 → 445/139).
- VPS nginx forwards public ports, but all data stays on Jetson.
- Telegram bot token travels through an encrypted SSH tunnel — never visible in `ps aux` on VPS.

Проверка перед push / Pre-push check:

```bash
./scripts/security/check_no_secrets.sh
```

CI автоматически проверяет секреты / CI automatically checks for secrets: `.github/workflows/secrets-check.yml`.

Полная политика / Full policy: [SECURITY.md](SECURITY.md) · [docs/10_SECURITY_PRIVACY.md](docs/10_SECURITY_PRIVACY.md) · [docs/11_SECRETS_POLICY.md](docs/11_SECRETS_POLICY.md).

---

## Известные ограничения / Known Limitations

- **JMS583 USB SSD enclosure** (152d:a583) — UAS quirk активен (`usb-storage.quirks=152d:a583:u` в extlinux.conf). Для применения требуется reboot. Write 250 MB/s подтверждён. SMART passthrough ограничен (smartmontools 6.6 — базовые данные без SCSI passthrough). / UAS quirk active (`usb-storage.quirks=152d:a583:u` in extlinux.conf). Requires reboot to apply. Write 250 MB/s confirmed. SMART limited (smartmontools 6.6).
- **HTTPS self-signed** — VPS nginx обслуживает Nextcloud на :8443, Immich на :2443, LLM на :9443 с самоподписанным сертификатом (10 лет). Let's Encrypt потребует доменное имя.
- `scripts/backup/backup_databases.sh` работает fail-closed: если `/mnt/storage` не является отдельным mountpoint, backup не пишется в ложный каталог на microSD.
- `services/backup-api` — Stage 2 placeholder, не production backup-сервис.
- Immich работает без machine learning (`IMMICH_DISABLE_MACHINE_LEARNING=true`) — Jetson Nano 4 GB с ML не тестировался.
- VPS IP может меняться — при смене обновить `VPS_HOST` в `config/.env` на Jetson и перезапустить `nas_jetson_nano-tunnel.service`.
- Docker 20.10.7 (JetPack 4.x) — устаревший. Обновление нетривиально из-за зависимостей NVIDIA runtime. Для home lab допустимо.
- HTTPS для VPS nginx — Let's Encrypt не настроен (нет доменного имени).

---

## Статьи и публикации / Articles

🇷🇺 **Habr:** статья **не опубликована**. В репозитории хранится только черновик и материалы подготовки. Ранее указанный адрес Песочницы на 16.07.2026 возвращает HTTP 404 и не является доказательством публикации.

🇬🇧 **Habr:** the article is **not published**. The repository contains only a draft and preparation materials. The previously recorded Sandbox URL returned HTTP 404 on 2026-07-16 and is not evidence of publication.

🇬🇧 **GitHub Pages:** [alexeyborovskoy.github.io/NAS_Jetson_Nano](https://alexeyborovskoy.github.io/NAS_Jetson_Nano/) — project site with architecture, reliability story, evidence.

| Материал | Язык | Ссылка |
|---|---|---|
| Черновик статьи для Habr / Habr article draft | RU | [docs/articles/habr_article_ru.md](docs/articles/habr_article_ru.md) |
| GitHub Pages | EN/RU | [alexeyborovskoy.github.io/NAS_Jetson_Nano](https://alexeyborovskoy.github.io/NAS_Jetson_Nano/) |
| Hackaday.io | EN | [docs/articles/hackaday_project_en.md](docs/articles/hackaday_project_en.md) |
| Архив версий статьи | — | [docs/articles/README.md](docs/articles/README.md) |

---

## Вклад / Contributing

🇷🇺 Вклад приветствуется. Прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) перед тем, как открывать pull request.

**Есть вопрос или идея?** Заходи в [Discussions](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/discussions) — там есть тема для знакомства и Q&A.

Правила:
- Не коммитьте секреты и персональные данные.
- Предпочитайте небольшие PR с документацией.
- Stage 1 должен оставаться безопасным: нет прямого публичного доступа к сервисам.

🇬🇧 Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

**Questions or ideas?** Join the [Discussions](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/discussions) — there's an intro thread and Q&A.

Rules:
- Do not commit secrets or personal data.
- Prefer small PRs with documentation.
- Keep Stage 1 safe: no direct public access to services.

Хорошие первые задачи / Good first issues:
- [#5 Адаптация под Raspberry Pi 4/5](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/issues/5) — только документация / documentation only, no code changes.
- [#4 HTTPS (Let's Encrypt) для VPS nginx](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/issues/4) — самоподписанный сертификат готов / self-signed cert ready, need a domain for Let's Encrypt.
- [#6 Netdata Telegram alerts](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/issues/6) — настроить и описать / configure and document.
- CI shellcheck для всех bash-скриптов / for all bash scripts in `scripts/`.
- Подключение **USB HDD** как резервного хранилища / as backup storage (Stage 3.1, план в `docs/04_STORAGE_DESIGN.md`).

---

## Лицензия / License

MIT — см. [LICENSE](LICENSE).
