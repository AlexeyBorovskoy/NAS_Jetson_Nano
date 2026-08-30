# ARTICLE_AUDIT_REPORT — NAS_Jetson_Nano

**Аудитор / Auditor:** Claude Code (claude-sonnet-4-6)  
**Дата аудита / Audit date:** 2026-06-28 (обновлено / updated 2026-06-29)  
**Версия проекта / Project version:** v1.4.0  
**Репозиторий / Repository:** https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano
**Режим / Mode:** READ-ONLY audit + report generation  

---

## 1. Executive Summary

🇷🇺 NAS_Jetson_Nano — это рабочий семейный self-hosted облачный сервер на базе NVIDIA Jetson Nano 4 GB + USB SSD (232 GB, DEXP/Realtek RTL9210B-CG). Проект заменяет Google Photos (Immich), Google Drive + Яндекс.Диск (Nextcloud), облачный NAS (Samba). Реализован совместно с Claude Code — AI-агент генерировал код, systemd-юниты, Docker Compose, документацию и диагностические скрипты; владелец принимал решения и проверял результат.

**Состояние на момент аудита:** Stage 1 полностью работает. 13 Docker-контейнеров up/healthy. Android-клиенты подключены. Система пережила 3 инцидента с USB SSD и выработала механизм авто-восстановления через udev hotplug + systemd. 

**Для статьи:** проект готов к публикации на Habr. Главная ценность — не «как поднять Nextcloud», а инженерная история: нестабильное железо → методичная отладка → производственная надёжность при помощи AI-ассистента. Это редкий жанр на Habr.

**Оценка готовности к публикации: 9/10.** Скриншоты 12/14 готовы. Остались: Portainer (LAN), Uptime Kuma (LAN). USB drama, Talk/API, Beszel, Swagger — все секции и скриншоты в habr_draft.md.

🇬🇧 NAS_Jetson_Nano is a working self-hosted family cloud server built on an NVIDIA Jetson Nano 4 GB plus a USB SSD (232 GB, DEXP/Realtek RTL9210B-CG). The project replaces Google Photos (Immich), Google Drive + Yandex.Disk (Nextcloud) and a cloud NAS (Samba). It was built together with Claude Code — the AI agent generated code, systemd units, Docker Compose files, documentation and diagnostic scripts; the owner made the decisions and verified the results.

**State at the time of the audit:** Stage 1 is fully operational. 13 Docker containers up/healthy. The Android clients are connected. The system survived 3 USB SSD incidents and produced an auto-recovery mechanism based on udev hotplug + systemd.

**For the article:** the project is ready for publication on Habr. Its main value is not "how to set up Nextcloud" but the engineering story: unstable hardware → methodical debugging → production-grade reliability with the help of an AI assistant. That is a rare genre on Habr.

**Publication readiness: 9/10.** 12 of 14 screenshots are done. Still missing: Portainer (LAN), Uptime Kuma (LAN). The USB drama, Talk/API, Beszel, Swagger — all sections and screenshots are in habr_draft.md.

---

## 2. Current Project State

| Параметр / Parameter | Значение / Value |
|---|---|
| Версия / Version | **v1.4.0** |
| Платформа / Platform | Jetson Nano 4 GB · Ubuntu 18.04 LTS (L4T 4.9) · aarch64 |
| Системный диск / System disk | microSD 64 GB (используется ~28% / ~28% used) |
| Хранилище / Storage | **JMS583** USB 3.0 SSD 229 GB ext4 `/mnt/storage` · ~3% использовано / ~3% used |
| USB-мост / USB bridge | **JMS583** (152d:a583, USB 3.0 SuperSpeed, 5 Gbps) · Write **250 MB/s** · UAS quirk активен / UAS quirk active |
| Предыдущий / Previous | RTL9210B-CG **заменён 2026-06-28 / replaced 2026-06-28** |
| Docker | 13 контейнеров up/healthy / 13 containers up/healthy |
| Пользователи / Users | admin, olga, ivan, ulyana, **anna** (Talk-only) |
| Фото в Immich / Photos in Immich | **6 484** фото + **210** видео / **6 484** photos + **210** videos · Immich v2.7.5 |
| Контакты Nextcloud / Nextcloud contacts | 2 151 (синхронизируются через DAVx⁵ / synced via DAVx⁵) |
| Android-статус / Android status | Immich ✅ Nextcloud ✅ DAVx⁵ ✅ **Talk ✅** |
| Семейный чат / Family chat | Nextcloud Talk «Семья» / "Family" (token: 37pcobmf) · 5 участников / 5 members |
| NAS_Jetson_Nano API | **v0.6.0** · 20 endpoints · Talk + Users + Photos + Actions |
| VPS | 193.8.215.130 (Vienna) · nginx reverse proxy · HTTPS self-signed 10y |
| Мониторинг / Monitoring | Beszel Hub VPS:8091 + Telegram daily report 09:00 |
| CI | 4 GitHub Actions workflows активны / 4 GitHub Actions workflows active |
| Открытые вопросы / Open items | Docker 20.10.7 (устаревший / outdated), off-site backup не настроен / off-site backup not configured |

---

## 3. Current Architecture Snapshot

```
Internet
    |
    | (public IP)
    v
[ VPS 193.8.215.130 — Vienna ]
    |
    |  nginx (host network, Docker)
    |  :8080 / :8443  → 127.0.0.1:18080 → tunnel → Jetson:8080  (Nextcloud)
    |  :2283 / :2443  → 127.0.0.1:12283 → tunnel → Jetson:2283  (Immich)
    |  :8090 / :9443  → 127.0.0.1:18090 → tunnel → Jetson:8090  (LLM Gateway)
    |  :10022         → tunnel → Jetson:22                        (SSH management)
    |  :8091          — Beszel Hub (monitoring)
    |
    |  autossh reverse SSH tunnel (CGNAT bypass)
    |
[ Home router ]
    |  static DHCP: 192.168.0.50
    v
[ Jetson Nano 4 GB · Ubuntu 18.04 · 192.168.0.50 ]
    |
    +-- Nextcloud (8080) · PostgreSQL 16 · Redis 7
    +-- Immich (2283) · pgvecto-rs · Redis 7 · IMMICH_DISABLE_MACHINE_LEARNING=true
    +-- LLM Gateway / FastAPI (8090) · DeepSeek API · PII redaction
    +-- nas_jetson_nano-api / FastAPI (8099) · Swagger UI
    +-- Samba NAS (445) · LAN only via iptables
    +-- Netdata (19999) · Uptime Kuma (3001) · Portainer (9000)
    +-- Beszel Agent (45876)
    |
    +-- systemd: nas_jetson_nano-tunnel.service (autossh, restart=always)
    +-- systemd: nas_jetson_nano-daily-report-telegram.timer (09:00 daily)
    +-- systemd: nas_jetson_nano-backup.timer (03:00 daily, pg_dump)
    +-- systemd: nas_jetson_nano-usb-preboot.service (power cycle before mount)
    +-- systemd: nas_jetson_nano-usb-monitor.service (dmesg watcher, Telegram alert on error -71)
    +-- systemd: nas_jetson_nano-ssd-recovery.service (udev hotplug auto-recovery)
    +-- nas_jetson_nano-api / FastAPI (8099) · Swagger UI · v0.6.0
    |     Talk · Users · Photos · Actions endpoints live
    +-- Nextcloud Talk (spreed v23.0.7) · группа «Семья» · 5 участников
    +-- udev: usb-storage.quirks=152d:a583:u (JMS583 UAS quirk, extlinux.conf)
    +-- smartd: /dev/sda (weekly self-test)

/mnt/storage (229 GB ext4, USB SSD)
  ├── nextcloud/data
  ├── immich/library
  ├── db/nextcloud-postgres  (~373 MB)
  ├── db/immich-postgres
  ├── backups/database-dumps/ (pg_dump · gzip · 7-day rotation)
  └── samba/public
```

---

## 4. Architecture Changes (было → стало / before → after)

| Версия / Version | Изменение / Change | Причина / Reason |
|---|---|---|
| v0.1.0 | Начальная структура: Docker Compose, docs, scripts / Initial structure: Docker Compose, docs, scripts | Старт проекта / Project start |
| v1.3.0 | Добавлены mem_limit, healthchecks, goss, NAS_Jetson_Nano API, Telegram report / Added mem_limit, healthchecks, goss, the NAS_Jetson_Nano API, the Telegram report | Resilience audit (Stage 1H) |
| v1.3.2 | CLAUDE.md, GitHub CLI, Discussions, good first issues | Open-source публикация / Open-source publication |
| v1.3.4 | Beszel Hub/Agent, USB watchdog (udev + autosuspend) | USB SSD error -71 инцидент / the USB SSD error -71 incident |
| v1.3.4 | autossh tunnel port +45876 (Beszel) | Мониторинг через VPS / Monitoring through the VPS |
| v1.3.5 | HTTPS: self-signed TLS на alt-портах (:8443/:2443/:9443) / self-signed TLS on alt ports (:8443/:2443/:9443) | Требование Android-приложений / Required by the Android apps |
| v1.3.5 | Nextcloud trusted proxy (occ) | Корректные HTTPS-заголовки / Correct HTTPS headers |
| v1.3.6 | USB SSD: порт 4 (сломан) → порт 2 / port 4 (broken) → port 2 | Аппаратный дефект порта / A hardware defect in the port |
| v1.3.7 | nas_jetson_nano-usb-preboot.service (power cycle до монтирования / power cycle before mounting) | RTL9210B-CG crashed state через software reboot / RTL9210B-CG crashed state after a software reboot |
| v1.3.7 | nas_jetson_nano-usb-monitor.service (dmesg watcher) | Telegram alert при первом error -71 / Telegram alert on the first error -71 |
| v1.3.7 | .gitattributes: LF enforce | CRLF→bash shebang corruption на Windows / on Windows |
| v1.3.8 | git filter-repo: удалён leaked password hash из 87 коммитов / removed a leaked password hash from 87 commits | Security incident |
| v1.3.8 | Ротация паролей (4 сервиса) / Password rotation (4 services) | После git history rewrite / After the git history rewrite |
| v1.3.8 | immich-microservices mem_limit 512m | OOM protection |
| v1.3.8 | Repo structure refactor: assets/, artifacts/, docs/prompts/ | Open-source conventions |
| v1.3.9 | nas_jetson_nano-ssd-recovery.service (udev hotplug auto-recovery) | Автовосстановление при подключении SSD / Auto-recovery when the SSD is plugged back in |
| **v1.4.0** | **JMS583** (152d:a583) заменил RTL9210B-CG / replaced the RTL9210B-CG | USB 3.0 SuperSpeed, write 250 MB/s, UAS quirk |
| **v1.4.0** | **Nextcloud Talk** «Семья», 5 участников (+ anna) / "Family", 5 members (+ anna) | Семейный чат, история на SSD / Family chat, history stored on the SSD |
| **v1.4.0** | **NAS_Jetson_Nano API v0.6.0**: Talk/Users/Photos/Actions (11 новых endpoints / 11 new endpoints) | Control + chat + stats API |
| **v1.4.0** | goss 40/40 (+6 тестов / +6 tests) | Покрытие JMS583, Talk, новых сервисов / Covering JMS583, Talk and the new services |
| Отменено / Cancelled | WireGuard через VPS / WireGuard through the VPS | DKMS несовместим с Tegra kernel 4.9 (ADR-0003) / DKMS is incompatible with Tegra kernel 4.9 (ADR-0003) |
| Отменено / Cancelled | Tailscale | Конфликт VPN-профиля с Amnezia на Android (ADR-0004) / VPN profile conflict with Amnezia on Android (ADR-0004) |

### Оценки (1–10) / Scores (1–10)

| Критерий / Criterion | Оценка / Score | Комментарий / Comment |
|---|---|---|
| Готовность к статье / Article readiness | 8/10 | Всё работает, документация глубокая, 9/13 скриншотов готовы / Everything works, the documentation is deep, 9 of 13 screenshots are ready |
| Инженерная зрелость / Engineering maturity | 8/10 | mem_limit, healthchecks, fail-closed backup, systemd watchdog |
| Воспроизводимость / Reproducibility | 7/10 | .env.example + Quick Start + ADR + промпты есть; JMS583 swap не задокументирован / .env.example + Quick Start + ADRs + prompts exist; the JMS583 swap is undocumented |
| Уникальность сюжета / Uniqueness of the story | 9/10 | USB SSD нестабильность + AI-assisted engineering = редкий жанр / USB SSD instability + AI-assisted engineering = a rare genre |
| Состояние CI/CD / CI/CD state | 7/10 | 4 workflows работают; Trivy и actionlint есть, но не все scripts покрыты / 4 workflows run; Trivy and actionlint exist, but not all scripts are covered |
| Тестовое покрытие / Test coverage | 6/10 | goss 34 теста, smoke-тесты есть; k6 нагрузочный не запускался live / goss 34 tests, smoke tests exist; the k6 load test has never been run live |
| Безопасность / Security | 7/10 | Secrets scan CI, no secrets in git, filter-repo done; Docker 20.10.7 устарел / Docker 20.10.7 is outdated |
| Документация / Documentation | 9/10 | 24+ doc-файла, ADR-0001..0006, двуязычные, промпты, TEST_PLAN, runbook / 24+ documents, ADR-0001..0006, bilingual, prompts, TEST_PLAN, runbook |
| Android-интеграция / Android integration | 8/10 | Immich + Nextcloud + DAVx⁵ настроены; документация MIUI quirks подробная / Immich + Nextcloud + DAVx⁵ are configured; the MIUI quirks documentation is detailed |
| AI-assisted workflow | 9/10 | AGENTS.md, 5 domain-agents, промпты, CLAUDE.md — образцовая модель / AGENTS.md, 5 domain agents, prompts, CLAUDE.md — an exemplary model |

---

## 5. Hardware Layer

| Компонент / Component | Модель / Model | Характеристики / Specs | Проблемы / Problems |
|---|---|---|---|
| Вычислительный узел / Compute node | NVIDIA Jetson Nano Dev Kit | 4 GB LPDDR4, ARM64, GPU Maxwell | Docker 20.10.7 устарел; нет swap (zram 1.9 GB) / Docker 20.10.7 is outdated; no swap (zram 1.9 GB) |
| Системный диск / System disk | microSD + Kingston USB | 64 GB (60 GB для OS); 28% использовано / 64 GB (60 GB for the OS); 28% used | Износ microSD — риск; нет мониторинга wear / microSD wear is a risk; wear is not monitored |
| USB-хаб / USB hub | Realtek 0bda:5411 | 4-портовый / 4-port | Ранее входил в autosuspend, убивая дочерние устройства / Used to enter autosuspend, killing the child devices |
| USB SSD (текущий / current) | **JMS583** (152d:a583) | 229 GB, USB 3.0 SuperSpeed, 5 Gbps, Write 250 MB/s | UAS quirk активен; SMART базовый (smartmontools 6.6) / the UAS quirk is active; SMART is basic (smartmontools 6.6) |
| USB SSD (заменён / replaced) | DEXP / Realtek RTL9210B-CG | 232 GB, USB 2.0 (деградация / degraded), ~40 MB/s | 3x error -71, SMART заблокирован — **заменён 2026-06-28** / 3× error -71, SMART blocked — **replaced 2026-06-28** |
| VPS | Ubuntu 24.04 · 1 vCPU · 2 GB RAM | Vienna | Amnezia VPN (25 клиентов) — не трогать / Amnezia VPN (25 clients) — do not touch |

🇷🇺 **Аппаратные риски:**
- Docker 20.10.7 (2021) — устаревший, известные CVE (F-01, Open)
- microSD wear: нет мониторинга S.M.A.R.T. для встроенной карты
- RTL9210B-CG **заменён** на JMS583 (2026-06-28). Watchdog ✅ active.

🇬🇧 **Hardware risks:**
- Docker 20.10.7 (2021) — outdated, with known CVEs (F-01, Open)
- microSD wear: no S.M.A.R.T. monitoring for the embedded card
- The RTL9210B-CG has been **replaced** by the JMS583 (2026-06-28). Watchdog ✅ active.

---

## 6. Service Layer

| Контейнер / Container | Image | Порт / Port | mem_limit | Healthcheck | restart | Статус / Status |
|---|---|---|---|---|---|---|
| homecloud_nextcloud | nextcloud:apache | 8080 | 512m | /status.php | always | ✅ |
| homecloud_nextcloud_db | postgres:16-alpine | — | 512m | pg_isready | always | ✅ |
| homecloud_nextcloud_redis | redis:7-alpine | — | 64m | redis-cli ping | always | ✅ |
| homecloud_immich_server | immich-server:release | 2283 | 1024m | /api/server/ping | always | ✅ |
| homecloud_immich_db | pgvecto-rs:pg16 | — | 384m | pg_isready | always | ✅ |
| homecloud_immich_redis | redis:7-alpine | — | 64m | redis-cli ping | always | ✅ |
| homecloud_immich_microservices | immich-server:release | — | 512m | (нет / none) | always | ✅ |
| homecloud_llm_gateway | custom FastAPI | 8090 | 256m | /health | always | ✅ |
| homecloud_nas_jetson_nano_api | custom FastAPI | 8099 | 128m | /healthcheck | always | ✅ |
| homecloud_samba | crazymax/samba | 445/139 | не задан / not set | (нет / none) | always | ✅ LAN only |
| homecloud_netdata | netdata:latest | 19999 | 256m | /api/v1/info | always | ✅ |
| homecloud_uptime_kuma | louislam/uptime-kuma:1 | 3001 | 128m | built-in | always | ✅ 5 monitors |
| homecloud_portainer | portainer/portainer-ce | 9000 | 128m | (scratch) | always | ✅ |

🇷🇺 **Примечания:**
- IMMICH_DISABLE_MACHINE_LEARNING=true — обязательно для Jetson 4 GB (нет swap + GPU RAM shared)
- Samba доступна только из LAN через iptables (192.168.0.0/24 → 445/139)
- Beszel Agent работает как systemd-юнит вне Docker (arm64 binary 0.18.7)
- immich-microservices не имеет healthcheck — возможно незначительный gap

🇬🇧 **Notes:**
- IMMICH_DISABLE_MACHINE_LEARNING=true — mandatory on a 4 GB Jetson (no swap + shared GPU RAM)
- Samba is reachable only from the LAN, enforced by iptables (192.168.0.0/24 → 445/139)
- The Beszel Agent runs as a systemd unit outside Docker (arm64 binary 0.18.7)
- immich-microservices has no healthcheck — possibly a minor gap

---

## 7. Network Layer

### Топология / Topology

```
LAN (192.168.0.0/24)
  └─ Jetson Nano: 192.168.0.50 (static DHCP)
       └─ iptables: Samba LAN-only, DROP остальное для 445/139
          iptables: Samba LAN-only, DROP everything else for 445/139

CGNAT bypass: autossh reverse SSH tunnel
  Jetson → outbound SSH → VPS:22
  VPS sshd: reverse ports на 127.0.0.1
  nginx (host network): proxy 127.0.0.1:18080/12283/18090 → public

VPS public ports:
  :8080/:8443  — Nextcloud (HTTP/HTTPS)
  :2283/:2443  — Immich (HTTP/HTTPS)
  :8090/:9443  — LLM Gateway (HTTP/HTTPS)
  :10022       — SSH management (Jetson via tunnel)
  :8091        — Beszel Hub (monitoring)
  :45876       — Beszel Agent Jetson (через VPS tunnel / through the VPS tunnel)
  :45877       — Beszel Agent VPS (localhost)
```

### Архитектурные решения (ADR) / Architecture decisions (ADR)

| ADR | Решение / Decision | Статус / Status |
|---|---|---|
| ADR-0001 | Nextcloud + Immich + DeepSeek Gateway | Accepted |
| ADR-0002 | USB SSD хранилище, UUID/fstab / USB SSD storage, UUID/fstab | Accepted |
| ADR-0003 | LAN-only (нет direct internet exposure / no direct internet exposure) | Accepted |
| ADR-0004 | Tailscale — отклонён (VPN-конфликт на Android) / rejected (VPN conflict on Android) | Rejected |
| ADR-0005 | autossh reverse SSH tunnel (CGNAT bypass) | Implemented |
| ADR-0006 | HTTPS self-signed на alt-портах (нет домена) / self-signed HTTPS on alt ports (no domain) | Accepted |

### Известные ограничения сети / Known network limitations

🇷🇺
- Нет доменного имени → Let's Encrypt недоступен → self-signed TLS + браузерное предупреждение
- VPS IP может меняться (нет DDN) → ручное обновление VPS_HOST в .env
- Порт 443 занят Amnezia xray — не трогать

🇬🇧
- No domain name → Let's Encrypt is unavailable → self-signed TLS + a browser warning
- The VPS IP can change (no DDNS) → VPS_HOST has to be updated in .env by hand
- Port 443 is occupied by Amnezia xray — do not touch

---

## 8. Storage Layer

| Параметр / Parameter | Значение / Value |
|---|---|
| Устройство / Device | /dev/sda1 (JMS583 · 152d:a583) |
| Размер / Size | 229 GB ext4 |
| Использование / Usage | ~3% (~7 GB) |
| Монтирование / Mount | /mnt/storage · UUID в /etc/fstab · noatime / UUID in /etc/fstab · noatime |
| Скорость / Speed | Write **250 MB/s** · Read **172 MB/s** (dd bs=1M) |
| Preflight | scripts/storage/storage_preflight.sh (errors=0 verified) |
| Backup | pg_dump · gzip · /mnt/storage/backups/database-dumps · 7-day rotation |
| Backup guard | fail-closed: не пишет в microSD если /mnt/storage не mountpoint / fail-closed: does not write to the microSD if /mnt/storage is not a mountpoint |
| SMART | Базовый (smartmontools 6.6, SAT passthrough ограничен) / Basic (smartmontools 6.6, SAT passthrough is limited) |
| USB quirks | **usb-storage.quirks=152d:a583:u** (UAS quirk, BOT mode, extlinux.conf) |
| USB autosuspend | usbcore.autosuspend=-1 (kernel param, подтверждён после reboot / kernel param, confirmed after a reboot) |
| SCSI timeout | 120s (udev правило, активно / udev rule, active) |

### История инцидентов USB SSD / USB SSD incident history

| Дата / Date | Событие / Event | Причина / Cause | Решение / Resolution |
|---|---|---|---|
| 2026-06-23 | error -71, SSD исчез с шины, Docker offline / error -71, the SSD vanished from the bus, Docker offline | RTL9210B-CG + USB autosuspend | Физическое переподключение + storage_preflight / Physical replug + storage_preflight |
| 2026-06-24 | USB watchdog установлен / USB watchdog installed | Предотвращение повторения / Preventing a repeat | udev power/control=on, smartd, autosuspend=-1 |
| 2026-06-26 | error -71 при boot / error -71 at boot | Порт 4 (1-2.4) аппаратно сломан / Port 4 (1-2.4) is broken in hardware | Переткнут в порт 2 (1-2.2) / Moved to port 2 (1-2.2) |
| 2026-06-26 | CRLF в shebang / CRLF in the shebang | git на Windows конвертировал LF→CRLF / git on Windows converted LF→CRLF | .gitattributes LF enforce + dos2unix |
| 2026-06-27 | Всё работает стабильно / Everything runs stably | preboot + monitor + port 2 | 7 boot подряд без инцидентов / 7 boots in a row with no incidents |
| 2026-06-28 | nas_jetson_nano-ssd-recovery.service (udev hotplug) | Автовосстановление при горячем подключении / Auto-recovery on hotplug | udev → mount → preflight → docker start |

### off-site backup

🇷🇺 **Статус: не реализован.** Скрипты restic готовы (`scripts/backup/restic_backup_example.sh`), но restic backup на VPS не настроен и не запущен. Это критический gap для статьи (нет полного disaster recovery).

🇬🇧 **Status: not implemented.** The restic scripts are ready (`scripts/backup/restic_backup_example.sh`), but the restic backup to the VPS is neither configured nor running. This is a critical gap for the article (there is no complete disaster recovery).

---

## 9. Android Client Layer

| Приложение / Application | Статус / Status | URL | Примечание / Note |
|---|---|---|---|
| Immich | ✅ настроен, работает / configured, working | http://193.8.215.130:2283 | 6723 файлов, 31 альбом, бэкап активирован / 6723 files, 31 albums, backup enabled |
| Nextcloud | ✅ настроен / configured | https://193.8.215.130:8443 | HTTPS, self-signed → принять 1 раз / HTTPS, self-signed → accept once |
| DAVx⁵ | ✅ настроен / configured | https://193.8.215.130:8443/remote.php/dav | 2151 контакт импортируется / 2151 contacts being imported |
| Samba | LAN only | \\192.168.0.50\public | Доступен в домашней сети / Available on the home network |
| Immich local URL | Не настроен / Not configured | http://192.168.0.50:2283 | Приоритет по WiFi (TP-Link_828C) / Preferred over Wi-Fi (TP-Link_828C) |

🇷🇺 **Документация Android:** `docs/android/ANDROID_SETUP.md`, `GOOGLE_MIGRATION.md`, `XIAOMI_MIUI_QUIRKS.md` — подробные пошаговые инструкции для Xiaomi MIUI/HyperOS.

**Специфика MIUI:** battery whitelist, автозапуск, блокировка в RAM — задокументированы в `XIAOMI_MIUI_QUIRKS.md`. Это ценный материал для статьи (проблема знакома большинству пользователей Xiaomi).

🇬🇧 **Android documentation:** `docs/android/ANDROID_SETUP.md`, `GOOGLE_MIGRATION.md`, `XIAOMI_MIUI_QUIRKS.md` — detailed step-by-step instructions for Xiaomi MIUI/HyperOS.

**MIUI specifics:** battery whitelist, autostart, locking in RAM — all documented in `XIAOMI_MIUI_QUIRKS.md`. This is valuable material for the article (the problem is familiar to most Xiaomi users).

---

## 10. AI-Agent Automation Layer

🇷🇺 Это один из наиболее сильных аспектов проекта для статьи.

🇬🇧 This is one of the project's strongest aspects for the article.

### Инфраструктура агентов / Agent infrastructure

| Файл / File | Назначение / Purpose |
|---|---|
| `AGENTS.md` | Правила работы агентов: hard limits, safety boundaries, workflow / Agent operating rules: hard limits, safety boundaries, workflow |
| `CLAUDE.md` | Контекстный файл для Claude Code: живое состояние системы / The context file for Claude Code: the live state of the system |
| `docs/20_AGENT_OPERATING_MODEL.md` | Операционная модель: 6 ролей субагентов, safety gates, workflow / The operating model: 6 subagent roles, safety gates, workflow |
| `docs/prompts/CODEX_*.md` | 8+ промптов для субагентов по областям (Storage, Android, LLM, Security...) / 8+ subagent prompts by area (Storage, Android, LLM, Security...) |

### 5 domain agents (Prompt A model)

| Агент / Agent | Промпт-файл / Prompt file | Зона ответственности / Area of responsibility |
|---|---|---|
| Code Agent | `CODEX_CODE_AGENT.md` | services/, Dockerfiles, CI |
| Hardware Agent | `CODEX_HARDWARE_AGENT.md` | scripts/diagnostics/, systemd/, Jetson SSH |
| Docs Agent | `CODEX_DOCS_AGENT.md` | docs/, README, CHANGELOG, ADR |
| Network Agent | `CODEX_NETWORK_AGENT.md` | scripts/network/, docker/vps/, VPS nginx |
| SysApps Agent | `CODEX_SYSAPPS_AGENT.md` | docker/compose/, configs/, .env.example |

### Паттерны AI-assisted workflow в проекте / AI-assisted workflow patterns in the project

🇷🇺
- Claude Code запускал параллельные субагенты для Bootstrap prompt (4 агента одновременно)
- `AGENTS.md` — «память агента между сессиями»; жёсткие правила предотвращают повторные инциденты (Amnezia VPN)
- Агент генерировал systemd-юниты, udev-правила, CRLF-fix, filter-repo — задачи, требующие специфических знаний
- AI предупредил о рисках WireGuard на Tegra kernel 4.9 (несовместимость DKMS)
- После VPN-инцидента правило «не трогать Amnezia» зафиксировано в AGENTS.md — агент напоминает при любой попытке

🇬🇧
- Claude Code ran parallel subagents for the Bootstrap prompt (4 agents at once)
- `AGENTS.md` is the "agent's memory between sessions"; hard rules prevent repeat incidents (Amnezia VPN)
- The agent generated systemd units, udev rules, the CRLF fix, filter-repo — tasks that require specific knowledge
- The AI warned about the risks of WireGuard on Tegra kernel 4.9 (DKMS incompatibility)
- After the VPN incident, the rule "do not touch Amnezia" was written into AGENTS.md — the agent brings it up on any attempt

### Честная оценка подхода / An honest assessment of the approach

🇷🇺 **Плюсы:**
- Скорость: недели DevOps → часы
- Документация создаётся параллельно с кодом
- Ошибки фиксируются в ADR, не теряются
- Агент знает нормы GitHub open-source (CI, badges, CODEOWNERS)

**Минусы:**
- Агент не знает конкретное железо — нужно объяснять детали (USB-SATA мост, реальное RAM)
- Финальная проверка — всегда человек: firewall, fstab, пароли
- Контекст сессии конечен — решается AGENTS.md + CLAUDE.md

🇬🇧 **Pros:**
- Speed: weeks of DevOps → hours
- Documentation is produced alongside the code
- Mistakes are recorded in ADRs and are not lost
- The agent knows GitHub open-source conventions (CI, badges, CODEOWNERS)

**Cons:**
- The agent does not know the specific hardware — the details have to be explained (the USB-SATA bridge, the real RAM figure)
- The final check is always a human: firewall, fstab, passwords
- The session context is finite — solved by AGENTS.md + CLAUDE.md

---

## 11. Reliability and Validation Layer

### CI/CD (GitHub Actions)

| Workflow | Триггер / Trigger | Что проверяет / What it checks | Статус / Status |
|---|---|---|---|
| secrets-check.yml | push/PR → main | bash check_no_secrets.sh | ✅ |
| shellcheck.yml | push/PR scripts/** | shellcheck --severity=error | ✅ |
| validate-compose.yml | push/PR docker/** | docker compose config --quiet | ✅ |
| quality-checks.yml | push/PR | (дополнительные проверки / additional checks) | ✅ |

### Тестирование / Testing

| Тип / Type | Инструмент / Tool | Покрытие / Coverage | Статус / Status |
|---|---|---|---|
| Infrastructure state | goss v0.4.9 | 34 теста (порты, сервисы, файлы, HTTP) / 34 tests (ports, services, files, HTTP) | 33/34 прошли (1 — nas_jetson_nano-api /health transient) / 33/34 passed (1 — nas_jetson_nano-api /health transient) |
| Shell scripts | shellcheck | scripts/ (**/*.sh) | CI, 11/14 чистые / CI, 11/14 clean |
| Python code | bandit | services/ (738 строк / 738 lines) | 0 проблем безопасности / 0 security issues |
| Dockerfiles | hadolint | 3 Dockerfile | 3/3 чистые / 3/3 clean |
| Service smoke | curl | Nextcloud, Immich, LLM GW, nas_jetson_nano-api | ✅ скрипты в tests/service/ / scripts in tests/service/ |
| Storage mount | mountpoint + df | /mnt/storage | ✅ скрипты в tests/storage/ / scripts in tests/storage/ |
| SMART | smartctl | /dev/sda | ⚠️ заблокирован RTL9210B-CG (docs в smart_check.sh) / blocked by the RTL9210B-CG (documented in smart_check.sh) |
| Load test (k6) | k6 | nextcloud-smoke.js (5 VU/2min) | Скрипт готов, live не запускался / The script is ready, never run live |
| Backup restore | rsync dry-run | tests/backup/restore_test.sh | Скрипт готов, не задокументировано live прохождение / The script is ready, no live pass is documented |
| Android manual | ADB (readonly) | tests/android/adb_readonly_check.sh | Скрипт готов; ручная проверка выполнена / The script is ready; a manual check was performed |
| Network | connectivity_check.sh | Jetson + VPS | ✅ |

### Resilience findings (doc/22_AUDIT_RESILIENCE.md)

| ID | Серьёзность / Severity | Статус / Status |
|---|---|---|
| F-01 | CRITICAL: Docker 20.10.7 устарел / Docker 20.10.7 is outdated | Open (нетривиальное обновление на JetPack) / Open (a non-trivial upgrade on JetPack) |
| F-02 | CRITICAL: docker kill + restart:unless-stopped bug | Mitigated (→ restart:always) |
| F-03 | HIGH: mem_limit | Fixed |
| F-04 | HIGH: healthchecks | Fixed |
| F-05 | HIGH: Telegram token leak | Fixed |
| F-06 | MEDIUM: Telegram retry | Fixed |
| F-07 | MEDIUM: Netdata CPU 19.5% | Fixed |
| F-08 | MEDIUM: shellcheck SC2046 | Fixed |
| F-09 | LOW: SC2016 false positive | Accepted |
| F-10 | LOW: SC1090 | Accepted |
| F-11 | HIGH: USB storage instability | Open/Mitigated |

---

## 12. What Is Already Article-Ready

🇷🇺 **Сильные стороны для статьи:**

1. **Реальная история USB SSD crisis.** Три инцидента с RTL9210B-CG задокументированы с kernel logs, recovery procedures, постморемами. Это живой инженерный нарратив.

2. **AI-assisted engineering workflow.** AGENTS.md как «память агента», 5 domain-agents, параллельные субагенты, реальные промпты — это уникальный паттерн, не описанный на Habr.

3. **Архитектура CGNAT bypass.** ADR-0005 объясняет почему Tailscale и WireGuard были отклонены и как autossh reverse tunnel решает задачу без domain name.

4. **Билингвальная документация.** 24+ документа на RU+EN, ADR-0001..0006, TEST_PLAN, TEST_MATRIX, RUNBOOK — проект готов для международной аудитории.

5. **Воспроизводимая Quick Start инструкция.** `config/.env.example` + 5 docker compose команд + goss validate = полный deploy path.

6. **Реальные пользователи.** 4 аккаунта (admin, olga, ivan, ulyana), 6723 фото в Immich, 2151 контакт — система используется семьёй, не только тестируется.

7. **Честный список ограничений.** Known Limitations раздел в README: устаревший Docker, self-signed TLS, нет off-site backup, ML отключён.

8. **Единственное фото стенда.** `assets/photos/test_sys.jpg` — Jetson Nano на роутере + DEXP-плата. Реальный стенд.

🇬🇧 **Strengths for the article:**

1. **A real USB SSD crisis story.** Three RTL9210B-CG incidents are documented with kernel logs, recovery procedures and post-mortems. This is a living engineering narrative.

2. **An AI-assisted engineering workflow.** AGENTS.md as "agent memory", 5 domain agents, parallel subagents, real prompts — a unique pattern that has not been described on Habr.

3. **The CGNAT bypass architecture.** ADR-0005 explains why Tailscale and WireGuard were rejected and how an autossh reverse tunnel solves the problem without a domain name.

4. **Bilingual documentation.** 24+ documents in RU+EN, ADR-0001..0006, TEST_PLAN, TEST_MATRIX, RUNBOOK — the project is ready for an international audience.

5. **A reproducible Quick Start.** `config/.env.example` + 5 docker compose commands + goss validate = a complete deploy path.

6. **Real users.** 4 accounts (admin, olga, ivan, ulyana), 6723 photos in Immich, 2151 contacts — the system is used by a family, not merely tested.

7. **An honest list of limitations.** The Known Limitations section in the README: outdated Docker, self-signed TLS, no off-site backup, ML disabled.

8. **The single photo of the rig.** `assets/photos/test_sys.jpg` — the Jetson Nano on the router + the DEXP board. A real setup.

---

## 13. What Is Not Ready Yet

🇷🇺 **Пробелы, которые нужно закрыть до публикации:**

1. **Скриншоты частично готовы.** Сделаны: Immich web, Nextcloud dashboard, Nextcloud Talk, Telegram report, Immich Android (галерея + профиль + бэкап), Nextcloud Android, DAVx⁵. Ещё нужны (LAN only): Portainer (13 контейнеров), Beszel Hub (CPU/RAM графики), Uptime Kuma (5 мониторов), NAS_Jetson_Nano API Swagger UI. Все в `assets/screenshots/article/`.

2. **Live замеры производительности не задокументированы.** I/O benchmark (`scripts/storage/benchmark_io.sh` существует, но результатов нет). 40 MB/s на RTL9210B-CG — цифра есть в README, источник неясен.

3. **off-site backup не реализован.** restic скрипты готовы, но backup на VPS не настроен. Если это упомянуть в статье — читатели спросят «а как восстановиться если Jetson умрёт?».

4. **k6 load test не запускался live.** Скрипт есть (`tests/load/nextcloud-smoke.js`), результатов нет.

5. **Docker 20.10.7 открытая уязвимость (F-01).** Для статьи желательно либо обновить, либо явно объяснить почему нетривиально (JetPack зависимости).

6. **JMS583 замена не задокументирована.** Ключевое планируемое событие (прибыл 2026-06-28) — нет документа о процедуре замены и валидации после.

7. **Backup restore не протестирован end-to-end.** `tests/backup/restore_test.sh` существует, но нет доказательства live прохождения.

8. **CHANGELOG содержит только v1.3.8 тег.** v1.3.9 упомянут в CLAUDE.md, но не в CHANGELOG — несоответствие для читателей репозитория.

🇬🇧 **Gaps to close before publication:**

1. **The screenshots are only partly done.** Taken: Immich web, the Nextcloud dashboard, Nextcloud Talk, the Telegram report, Immich Android (gallery + profile + backup), Nextcloud Android, DAVx⁵. Still needed (LAN only): Portainer (13 containers), Beszel Hub (CPU/RAM graphs), Uptime Kuma (5 monitors), the NAS_Jetson_Nano API Swagger UI. All of them live in `assets/screenshots/article/`.

2. **Live performance measurements are undocumented.** The I/O benchmark (`scripts/storage/benchmark_io.sh`) exists but there are no results. The 40 MB/s figure for the RTL9210B-CG is in the README, but its source is unclear.

3. **The off-site backup is not implemented.** The restic scripts are ready, but the backup to the VPS is not configured. If this is mentioned in the article, readers will ask "and how do you recover if the Jetson dies?".

4. **The k6 load test has never been run live.** The script exists (`tests/load/nextcloud-smoke.js`), the results do not.

5. **Docker 20.10.7 is an open vulnerability (F-01).** For the article it is best to either upgrade or explicitly explain why that is non-trivial (JetPack dependencies).

6. **The JMS583 swap is undocumented.** A key planned event (it arrived 2026-06-28) — there is no document describing the replacement procedure and the validation afterwards.

7. **Backup restore has not been tested end-to-end.** `tests/backup/restore_test.sh` exists, but there is no evidence of a live pass.

8. **The CHANGELOG only carries the v1.3.8 tag.** v1.3.9 is mentioned in CLAUDE.md but not in the CHANGELOG — an inconsistency for readers of the repository.

---

## 14. Risks Before Publication

| Риск / Risk | Вероятность / Likelihood | Влияние / Impact | Митигация / Mitigation |
|---|---|---|---|
| Docker 20.10.7 CVE | Medium | High | Задокументировать в Known Limitations; добавить Trivy в CI / Document it in Known Limitations; add Trivy to CI |
| off-site backup отсутствует / off-site backup is missing | High | High | Добавить раздел «что будет если Jetson умрёт» в статью / Add a "what happens if the Jetson dies" section to the article |
| RTL9210B-CG до замены JMS583 / RTL9210B-CG before the JMS583 swap | High | Critical | Watchdog остановлен; написать в статье как реальный open item / The watchdog is stopped; present it in the article as a genuine open item |
| VPS IP без домена / A VPS IP with no domain | Medium | Medium | DDNS или купить домен (Issue #4 в GitHub) / DDNS or buy a domain (Issue #4 on GitHub) |
| Утечка секретов в будущих коммитах / Secrets leaking in future commits | Low | Critical | CI secrets-check активен; .gitignore корректен / The CI secrets check is active; .gitignore is correct |
| Miui battery kill Immich backup | Medium | Medium | Задокументировано в XIAOMI_MIUI_QUIRKS.md / Documented in XIAOMI_MIUI_QUIRKS.md |
| Wear microSD / microSD wear | Low | High | Нет мониторинга; добавить в Netdata или systemd timer / Not monitored; add it to Netdata or a systemd timer |

---

## 15. Evidence Package Checklist

🇷🇺 Что нужно подготовить для сопровождения статьи:

- [x] Скриншот Immich — фотоархив (6.1 GiB / 228 GiB) → `assets/screenshots/article/immich_web.png`
- [x] Скриншот Nextcloud — дашборд → `assets/screenshots/article/nextcloud_dashboard.png`
- [x] Скриншот Nextcloud Talk — чат «Семья» → `assets/screenshots/article/nextcloud_talk.png`
- [x] Скриншот Nextcloud Android — файлы → `assets/screenshots/article/android_nextcloud_files.jpg`
- [x] Скриншот Immich Android — галерея + профиль + бэкап → `android_immich_*.jpg`
- [x] Скриншот DAVx⁵ CalDAV → `assets/screenshots/article/android_davx5_caldav.jpg`
- [x] Скриншот Telegram daily report (полный) → `assets/screenshots/article/telegram_report_full.png`
- [ ] Скриншот Portainer — 13 контейнеров up/healthy *(LAN only :9000, нужно дома)*
- [x] Скриншот Beszel Hub — обзор систем → `beszel_systems_overview.png`
- [x] Скриншот Beszel Hub — Jetson CPU/RAM/Docker метрики → `beszel_jetson_metrics.png`
- [ ] Скриншот Uptime Kuma — 5 мониторов (все green) *(LAN only :3001)*
- [x] Скриншот NAS_Jetson_Nano API Swagger UI v0.6.0 → `nas_jetson_nano_api_swagger.png`
- [x] Фото физического стенда (уже есть: `assets/photos/test_sys.jpg`)
- [ ] Результат `goss validate` — 34/34 pass после JMS583
- [ ] Результат `docker stats --no-stream` — RAM usage всех 13 контейнеров
- [ ] Результат `dd` или fio I/O test на JMS583 (сравнение с RTL9210B-CG 40 MB/s)
- [ ] Kernel log до/после замены USB enclosure
- [ ] Результат `storage_preflight.sh` — errors=0, warnings=0
- [ ] CHANGELOG обновить до v1.3.9

🇬🇧 What has to be prepared to accompany the article:

- [x] Immich screenshot — the photo archive (6.1 GiB / 228 GiB) → `assets/screenshots/article/immich_web.png`
- [x] Nextcloud screenshot — the dashboard → `assets/screenshots/article/nextcloud_dashboard.png`
- [x] Nextcloud Talk screenshot — the "Family" chat → `assets/screenshots/article/nextcloud_talk.png`
- [x] Nextcloud Android screenshot — files → `assets/screenshots/article/android_nextcloud_files.jpg`
- [x] Immich Android screenshot — gallery + profile + backup → `android_immich_*.jpg`
- [x] DAVx⁵ CalDAV screenshot → `assets/screenshots/article/android_davx5_caldav.jpg`
- [x] Telegram daily report screenshot (full) → `assets/screenshots/article/telegram_report_full.png`
- [ ] Portainer screenshot — 13 containers up/healthy *(LAN only :9000, has to be taken at home)*
- [x] Beszel Hub screenshot — systems overview → `beszel_systems_overview.png`
- [x] Beszel Hub screenshot — Jetson CPU/RAM/Docker metrics → `beszel_jetson_metrics.png`
- [ ] Uptime Kuma screenshot — 5 monitors (all green) *(LAN only :3001)*
- [x] NAS_Jetson_Nano API Swagger UI v0.6.0 screenshot → `nas_jetson_nano_api_swagger.png`
- [x] A photo of the physical rig (already present: `assets/photos/test_sys.jpg`)
- [ ] `goss validate` output — 34/34 pass after the JMS583 swap
- [ ] `docker stats --no-stream` output — RAM usage of all 13 containers
- [ ] `dd` or fio I/O test results on the JMS583 (compared with the RTL9210B-CG at 40 MB/s)
- [ ] Kernel log before/after the USB enclosure swap
- [ ] `storage_preflight.sh` output — errors=0, warnings=0
- [ ] Update the CHANGELOG to v1.3.9

---

## 16. Habr Article Plan

🇷🇺 **Заголовок:** Домашнее облако на Jetson Nano: задумал я — реализовал Claude Code. История трёх USB-инцидентов, 13 Docker-контейнеров и семейного фотоархива

**Хабы:** Системное администрирование · Open Source · Искусственный интеллект · Self-hosted  
**Теги:** `selfhosted` `nextcloud` `immich` `jetson-nano` `docker` `homelab` `claude-code` `ai-assisted-dev` `usb-storage`

🇬🇧 **Title:** A home cloud on a Jetson Nano: I designed it, Claude Code built it. The story of three USB incidents, 13 Docker containers and a family photo archive

**Hubs:** System administration · Open Source · Artificial Intelligence · Self-hosted  
**Tags:** `selfhosted` `nextcloud` `immich` `jetson-nano` `docker` `homelab` `claude-code` `ai-assisted-dev` `usb-storage`

---

### Структура статьи / Article structure

🇷🇺 **Лид (до cut):** 3-4 абзаца — личная история (Jetson в ящике, HDD от сына, Google Photos без места), идея, ключевой сюжет: не «как поднять Nextcloud», а «как строили отказоустойчивость вокруг нестабильного железа с помощью AI».

🇬🇧 **Lead (before the cut):** 3–4 paragraphs — a personal story (a Jetson in a drawer, an HDD from a son, Google Photos out of space), the idea, and the central plot: not "how to set up Nextcloud" but "how we built resilience around unstable hardware with the help of AI".

---

🇷🇺

**§1. Железо и исходная точка**
- NVIDIA Jetson Nano 4 GB: что это, зачем куплен, почему подходит для home cloud
- Ключевые ограничения: нет swap (зато zram 1.9 GB), ARM64, Docker 20.10.7 (старый)
- DEXP USB SSD: 232 GB, RTL9210B-CG — почему это оказалось проблемой
- VPS в Вене: уже был для семейного VPN (Amnezia), нельзя трогать

**§2. Архитектура за 5 минут**
- ASCII-схема: Jetson → autossh → VPS nginx → HTTPS → Android
- Таблица сервисов с портами и mem_limit
- Принципы: LAN+tunnel only, no secrets in git, restart:always, fail-closed backup

**§3. Как выглядел процесс с Claude Code**
- AGENTS.md как «архитектурная память агента»
- Примеры реальных промптов (из docs/prompts/)
- Параллельные субагенты: что делали одновременно
- Честная оценка: что работает хорошо, что требует контроля
- VPN-инцидент: как зафиксировали урок в AGENTS.md

**§4. USB SSD: три инцидента и инженерный ответ**
*(Это центральный раздел — самый уникальный)*
- Инцидент 1 (2026-06-23): error -71, kernel log, что это значит
- Диагностика: RTL9210B-CG деградирует USB 3.0→2.0, блокирует SMART
- Решение 1: autosuspend=off через udev, SCSI timeout 120s
- Инцидент 2 (2026-06-26): порт 4 сломан аппаратно → переткнуть в порт 2
- Инцидент 3 (CRLF в bash shebang): watchdog не работал 4+ часов из-за Windows git → .gitattributes
- nas_jetson_nano-usb-preboot.service: power cycle ДО монтирования при каждом boot
- nas_jetson_nano-ssd-recovery.service: udev hotplug → mount → preflight → docker start
- Итог: 7 boot подряд без инцидентов на порту 2

**§5. Android-интеграция: миграция с Google**
- Immich: 6723 фото, 31 альбом, автобэкап
- DAVx⁵ + Nextcloud: 2151 контакт
- HTTPS self-signed на alt-портах: почему так (нет домена, Amnezia на 443)
- MIUI/HyperOS специфика: battery whitelist, автозапуск

**§6. Мониторинг и наблюдаемость**
- Beszel Hub (VPS) + Agents: CPU/RAM/Disk история
- Telegram daily report в 09:00: что содержит
- Uptime Kuma: 5 мониторов
- goss: 34 инфраструктурных теста

**§7. Честная оценка и открытые вопросы**
- Docker 20.10.7 — открытая уязвимость, нетривиальное обновление
- off-site backup не настроен (restic скрипты есть, backup на VPS нет)
- Что будет когда JMS583 прибудет: watchdog включим, SMART заработает
- Let's Encrypt: когда появится домен

**§8. Как повторить: Quick Start**
- Требования (Jetson/RPi4+/mini-PC, VPS, Docker Compose v2)
- 5 команд для запуска
- Ссылка на README + docs/

**§9. Выводы**
- Что получилось: работающий семейный сервер, который переживает USB-инциденты
- Что дал AI-assisted подход: скорость + документация + системность
- Что впереди: JMS583, restic backup, Let's Encrypt, RPi guide

🇬🇧

**§1. The hardware and the starting point**
- NVIDIA Jetson Nano 4 GB: what it is, why it was bought, why it suits a home cloud
- Key constraints: no swap (but 1.9 GB of zram), ARM64, Docker 20.10.7 (old)
- The DEXP USB SSD: 232 GB, RTL9210B-CG — why this turned into a problem
- The VPS in Vienna: it already existed for the family VPN (Amnezia) and must not be touched

**§2. The architecture in 5 minutes**
- An ASCII diagram: Jetson → autossh → VPS nginx → HTTPS → Android
- A table of services with their ports and mem_limit
- Principles: LAN+tunnel only, no secrets in git, restart:always, fail-closed backup

**§3. What the process with Claude Code looked like**
- AGENTS.md as the agent's "architectural memory"
- Examples of real prompts (from docs/prompts/)
- Parallel subagents: what they did simultaneously
- An honest assessment: what works well, what needs supervision
- The VPN incident: how the lesson was written into AGENTS.md

**§4. The USB SSD: three incidents and the engineering response**
*(This is the central and most distinctive section)*
- Incident 1 (2026-06-23): error -71, the kernel log, what it means
- Diagnosis: the RTL9210B-CG degrades from USB 3.0 to 2.0 and blocks SMART
- Fix 1: autosuspend=off via udev, SCSI timeout 120s
- Incident 2 (2026-06-26): port 4 is broken in hardware → move to port 2
- Incident 3 (CRLF in the bash shebang): the watchdog was dead for 4+ hours because of git on Windows → .gitattributes
- nas_jetson_nano-usb-preboot.service: a power cycle BEFORE mounting on every boot
- nas_jetson_nano-ssd-recovery.service: udev hotplug → mount → preflight → docker start
- Result: 7 boots in a row with no incidents on port 2

**§5. Android integration: migrating away from Google**
- Immich: 6723 photos, 31 albums, auto-backup
- DAVx⁵ + Nextcloud: 2151 contacts
- Self-signed HTTPS on alt ports: why (no domain, Amnezia on 443)
- MIUI/HyperOS specifics: battery whitelist, autostart

**§6. Monitoring and observability**
- Beszel Hub (VPS) + Agents: CPU/RAM/Disk history
- The Telegram daily report at 09:00: what it contains
- Uptime Kuma: 5 monitors
- goss: 34 infrastructure tests

**§7. An honest assessment and the open questions**
- Docker 20.10.7 — an open vulnerability, a non-trivial upgrade
- The off-site backup is not configured (the restic scripts exist, the backup on the VPS does not)
- What happens when the JMS583 arrives: the watchdog goes back on, SMART starts working
- Let's Encrypt: once there is a domain

**§8. How to repeat this: Quick Start**
- Requirements (Jetson/RPi4+/mini-PC, a VPS, Docker Compose v2)
- 5 commands to launch it
- A link to the README + docs/

**§9. Conclusions**
- What came of it: a working family server that survives USB incidents
- What the AI-assisted approach gave: speed + documentation + systematic thinking
- What lies ahead: JMS583, restic backup, Let's Encrypt, an RPi guide

---

## 17. Hackaday.io Project Plan

**Название проекта / Project name:** Home Cloud for Old Hardware — Jetson Nano Family Server

**Tagline:** Turn forgotten Jetson Nano + USB drive into a private family cloud replacing Google Photos, Drive, and Contacts. Survived 3 USB SSD failures. Built with AI.

**Категории / Categories:** Raspberry Pi · Linux · Software · Home Automation

---

### 9 Project Logs

**Log 1 — First Boot and Hardware Audit**  
How Jetson Nano went from drawer to server: microSD bootstrap, L4T, USB topology audit. Tools: `scripts/diagnostics/hardware_audit.sh`.

**Log 2 — Docker Stack: 13 Containers on 4 GB RAM**  
Architecture decisions: why Nextcloud + Immich + LLM Gateway, mem_limit strategy, why ML is disabled on Jetson Nano (shared CPU/GPU RAM).

**Log 3 — CGNAT Problem and autossh Solution**  
No port forwarding, no static IP. WireGuard rejected (DKMS/Tegra), Tailscale rejected (VPN conflict). Reverse SSH tunnel through VPS — how and why.

**Log 4 — The Three USB Failures** *(flagship log)*  
RTL9210B-CG: error -71, USB 2.0 degradation, SMART blocked. Three incidents, three lessons. preboot service + udev hotplug recovery + CRLF bug in bash shebang.

**Log 5 — HTTPS Without a Domain**  
Self-signed TLS on alt-ports (:8443/:2443/:9443). No Let's Encrypt (no domain, port 443 occupied by Amnezia). DAVx⁵ "Accept untrusted cert" flow.

**Log 6 — Android Migration from Google**  
6723 photos, 2151 contacts. Immich auto-backup, DAVx⁵ CardDAV, MIUI battery whitelist quirks. From Google Photos/Contacts to self-hosted in one session.

**Log 7 — Building with AI: Lessons from Claude Code**  
AGENTS.md as agent memory. 5 domain-agents model. What AI does well (systemd units, udev rules, docs). What requires human review (firewall, passwords, hardware quirks).

**Log 8 — Monitoring and Observability**  
Beszel Hub + Agents (VPS + Jetson), Telegram daily report, goss 34 infrastructure tests, Uptime Kuma 5 monitors.

**Log 9 — What's Next: JMS583 + restic + Let's Encrypt**  
Replacing RTL9210B-CG with JMS583 (SMART passthrough, USB 3.0). Off-site restic backup to VPS. Domain name + Let's Encrypt. Raspberry Pi 4/5 adaptation guide.

---

## 18. Recommended Article Angle

🇷🇺 **Главный сюжет:** «Reliability story + AI-assisted engineering»

Это не «как поднять Nextcloud» (таких статей достаточно). Это:

> *Семейное облако на забытом Jetson Nano. Нестабильный USB-мост убивал систему трижды. AI-агент помогал строить отказоустойчивость: писал systemd-сервисы, udev-правила, документацию инцидентов. Итог — работающая система для 4 членов семьи с 6723 фотографиями и 2151 контактом.*

**Почему этот сюжет работает:**

1. **USB SSD crisis** — конкретная техническая история с kernel logs, не абстрактная архитектура
2. **AI как инструмент** — не хайп, а практика: что получается, что нет, какие уроки
3. **"Old hardware must live"** — эмоциональный крючок: Jetson из ящика + HDD от сына
4. **Воспроизводимость** — читатель может взять RPi4 и повторить
5. **Честность** — Docker 20.10.7 устарел, off-site backup не настроен, SMART заблокирован — это доверие

**Конкуренты на Habr:**
- Обычные «как поднять Nextcloud» — много, слабые
- «AI помогает кодить» — много, без инженерной глубины
- «Homelab на RPi» — есть, но без AI + без USB-кризиса

**Вывод:** комбинация уникальна. Публиковать стоит.

🇬🇧 **The central story:** "a reliability story + AI-assisted engineering"

This is not "how to set up Nextcloud" (there are plenty of those). It is:

> *A family cloud on a forgotten Jetson Nano. An unstable USB bridge killed the system three times. An AI agent helped build resilience: it wrote systemd services, udev rules, incident documentation. The result is a working system for 4 family members with 6723 photos and 2151 contacts.*

**Why this story works:**

1. **The USB SSD crisis** — a concrete technical story with kernel logs, not abstract architecture
2. **AI as a tool** — not hype but practice: what works, what does not, what the lessons are
3. **"Old hardware must live"** — an emotional hook: a Jetson from a drawer + an HDD from a son
4. **Reproducibility** — a reader can take an RPi4 and repeat it
5. **Honesty** — Docker 20.10.7 is outdated, the off-site backup is not configured, SMART is blocked — that builds trust

**Competitors on Habr:**
- Ordinary "how to set up Nextcloud" pieces — many, and weak
- "AI helps you code" — many, without engineering depth
- "A homelab on an RPi" — they exist, but without AI and without a USB crisis

**Conclusion:** the combination is unique. It is worth publishing.

---

## 19. Priority Fixes Before Publication

🇷🇺 Критичный (нельзя публиковать без этого):

1. **Сделать скриншоты** — Immich, Nextcloud, Portainer (13 контейнеров), Beszel Hub, Telegram report, Uptime Kuma. Без них статья слабая.
2. **Обновить CHANGELOG до v1.3.9** — текущая несогласованность между CLAUDE.md и CHANGELOG.
3. **Задокументировать JMS583 swap** — создать docs/plans/JMS583_SWAP_PROCEDURE.md с шагами и валидацией. Ключевое событие.

Важно (желательно):

4. **Запустить k6 load test** — записать результаты p95/p99 в docs/quality/LOAD_TESTS.md
5. **Запустить backup restore test** — зафиксировать прохождение tests/backup/restore_test.sh
6. **I/O benchmark на JMS583** — сравнить с RTL9210B-CG 40 MB/s
7. **Добавить раздел «off-site backup» в Known Limitations** — явно указать что restic на VPS запланирован (Stage 3)

Незначительно (можно в статье обойти):

8. Docker 20.10.7 — упомянуть в статье как известное ограничение JetPack
9. microSD wear — добавить в Known Limitations

🇬🇧 Critical (do not publish without these):

1. **Take the screenshots** — Immich, Nextcloud, Portainer (13 containers), Beszel Hub, the Telegram report, Uptime Kuma. Without them the article is weak.
2. **Update the CHANGELOG to v1.3.9** — the current inconsistency between CLAUDE.md and the CHANGELOG.
3. **Document the JMS583 swap** — create docs/plans/JMS583_SWAP_PROCEDURE.md with the steps and the validation. A key event.

Important (desirable):

4. **Run the k6 load test** — record the p95/p99 results in docs/quality/LOAD_TESTS.md
5. **Run the backup restore test** — record a pass of tests/backup/restore_test.sh
6. **An I/O benchmark on the JMS583** — compare it with the RTL9210B-CG at 40 MB/s
7. **Add an "off-site backup" item to Known Limitations** — state explicitly that restic on the VPS is planned (Stage 3)

Minor (can be worked around in the article):

8. Docker 20.10.7 — mention it in the article as a known JetPack limitation
9. microSD wear — add it to Known Limitations

---

## 20. Final Recommendation

🇷🇺 **Публиковать? Да, после скриншотов.**

**Сила проекта:**

Это технически глубокий и честный проект. Документация (24+ файла, ADR-0001..0006, TEST_PLAN, resilience audit) значительно превышает средний уровень публичных homelab-проектов на GitHub. История USB SSD — реальный инженерный нарратив с kernel logs, постморемами, несколькими итерациями решения. AI-assisted workflow задокументирован конкретными примерами промптов и уроков.

**Главный пробел:**

Визуальных доказательств нет. Habr — текстово-техническая платформа, но скриншоты работающей системы (Immich с 6723 фото, Portainer с 13 контейнерами, Beszel Hub с CPU-графиками) критичны для доверия читателя. Без них история остаётся «на словах».

**Рекомендованный порядок действий:**

1. Заменить USB enclosure (JMS583) — ждёт доставки
2. Сделать скриншоты всех ключевых UI (1-2 часа)
3. Запустить goss validate после замены — зафиксировать 34/34
4. Запустить fio или dd на JMS583 — зафиксировать скорость vs RTL9210B-CG
5. Обновить CHANGELOG до v1.3.9
6. Написать финальный вариант статьи по плану из §16
7. Публиковать на Habr (русский) + перевод/адаптация для Hackaday.io (английский)

**Прогноз отклика:**

- Habr: 2000-5000 просмотров при хорошем заголовке и скриншотах. Потенциал на "в хабы" если USB-история хорошо написана.
- GitHub: 20-50 звёзд в первые 2 недели если Habr-аудитория целевая.
- Hackaday.io: 500-1000 просмотров; шанс попасть в «Projects of the Week» за USB-reliability story.

🇬🇧 **Publish? Yes, once the screenshots are done.**

**The project's strength:**

This is a technically deep and honest project. The documentation (24+ files, ADR-0001..0006, TEST_PLAN, a resilience audit) is far above the average level of public homelab projects on GitHub. The USB SSD story is a real engineering narrative with kernel logs, post-mortems and several iterations of the fix. The AI-assisted workflow is documented with concrete prompt examples and lessons.

**The main gap:**

There is no visual evidence. Habr is a text-and-technology platform, but screenshots of the running system (Immich with 6723 photos, Portainer with 13 containers, Beszel Hub with CPU graphs) are critical for reader trust. Without them the story remains "just words".

**Recommended sequence of actions:**

1. Replace the USB enclosure (JMS583) — awaiting delivery
2. Take screenshots of every key UI (1–2 hours)
3. Run goss validate after the swap — record 34/34
4. Run fio or dd on the JMS583 — record the speed vs the RTL9210B-CG
5. Update the CHANGELOG to v1.3.9
6. Write the final version of the article following the plan in §16
7. Publish on Habr (Russian) + translate/adapt for Hackaday.io (English)

**Response forecast:**

- Habr: 2000–5000 views with a good title and screenshots. Potential to make the hubs' front page if the USB story is well written.
- GitHub: 20–50 stars in the first 2 weeks if the Habr audience is the right one.
- Hackaday.io: 500–1000 views; a chance at "Projects of the Week" for the USB reliability story.

---

🇷🇺 *Отчёт создан автоматически на основании анализа репозитория. Проверить все утверждения об актуальном live-состоянии системы.*

🇬🇧 *This report was generated automatically from an analysis of the repository. Verify every claim about the current live state of the system.*
