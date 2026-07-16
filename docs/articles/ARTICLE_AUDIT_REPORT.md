# ARTICLE_AUDIT_REPORT — NAS_Jetson_Nano

**Аудитор:** Claude Code (claude-sonnet-4-6)  
**Дата аудита:** 2026-06-28 (обновлено 2026-06-29)  
**Версия проекта:** v1.4.0  
**Репозиторий:** https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano
**Режим:** READ-ONLY audit + report generation  

---

## 1. Executive Summary

NAS_Jetson_Nano — это рабочий семейный self-hosted облачный сервер на базе NVIDIA Jetson Nano 4 GB + USB SSD (232 GB, DEXP/Realtek RTL9210B-CG). Проект заменяет Google Photos (Immich), Google Drive + Яндекс.Диск (Nextcloud), облачный NAS (Samba). Реализован совместно с Claude Code — AI-агент генерировал код, systemd-юниты, Docker Compose, документацию и диагностические скрипты; владелец принимал решения и проверял результат.

**Состояние на момент аудита:** Stage 1 полностью работает. 13 Docker-контейнеров up/healthy. Android-клиенты подключены. Система пережила 3 инцидента с USB SSD и выработала механизм авто-восстановления через udev hotplug + systemd. 

**Для статьи:** проект готов к публикации на Habr. Главная ценность — не «как поднять Nextcloud», а инженерная история: нестабильное железо → методичная отладка → производственная надёжность при помощи AI-ассистента. Это редкий жанр на Habr.

**Оценка готовности к публикации: 9/10.** Скриншоты 12/14 готовы. Остались: Portainer (LAN), Uptime Kuma (LAN). USB drama, Talk/API, Beszel, Swagger — все секции и скриншоты в habr_draft.md.

---

## 2. Current Project State

| Параметр | Значение |
|---|---|
| Версия | **v1.4.0** |
| Платформа | Jetson Nano 4 GB · Ubuntu 18.04 LTS (L4T 4.9) · aarch64 |
| Системный диск | microSD 64 GB (используется ~28%) |
| Хранилище | **JMS583** USB 3.0 SSD 229 GB ext4 `/mnt/storage` · ~3% использовано |
| USB-мост | **JMS583** (152d:a583, USB 3.0 SuperSpeed, 5 Gbps) · Write **250 MB/s** · UAS quirk активен |
| Предыдущий | RTL9210B-CG **заменён 2026-06-28** |
| Docker | 13 контейнеров up/healthy |
| Пользователи | admin, olga, ivan, ulyana, **anna** (Talk-only) |
| Фото в Immich | **6 484** фото + **210** видео · Immich v2.7.5 |
| Контакты Nextcloud | 2 151 (синхронизируются через DAVx⁵) |
| Android-статус | Immich ✅ Nextcloud ✅ DAVx⁵ ✅ **Talk ✅** |
| Семейный чат | Nextcloud Talk «Семья» (token: 37pcobmf) · 5 участников |
| NAS_Jetson_Nano API | **v0.6.0** · 20 endpoints · Talk + Users + Photos + Actions |
| VPS | 193.8.215.130 (Vienna) · nginx reverse proxy · HTTPS self-signed 10y |
| Мониторинг | Beszel Hub VPS:8091 + Telegram daily report 09:00 |
| CI | 4 GitHub Actions workflows активны |
| Открытые вопросы | Docker 20.10.7 (устаревший), off-site backup не настроен |

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

## 4. Architecture Changes (было → стало)

| Версия | Изменение | Причина |
|---|---|---|
| v0.1.0 | Начальная структура: Docker Compose, docs, scripts | Старт проекта |
| v1.3.0 | Добавлены mem_limit, healthchecks, goss, NAS_Jetson_Nano API, Telegram report | Resilience audit (Stage 1H) |
| v1.3.2 | CLAUDE.md, GitHub CLI, Discussions, good first issues | Open-source публикация |
| v1.3.4 | Beszel Hub/Agent, USB watchdog (udev + autosuspend) | USB SSD error -71 инцидент |
| v1.3.4 | autossh tunnel port +45876 (Beszel) | Мониторинг через VPS |
| v1.3.5 | HTTPS: self-signed TLS на alt-портах (:8443/:2443/:9443) | Требование Android-приложений |
| v1.3.5 | Nextcloud trusted proxy (occ) | Корректные HTTPS-заголовки |
| v1.3.6 | USB SSD: порт 4 (сломан) → порт 2 | Аппаратный дефект порта |
| v1.3.7 | nas_jetson_nano-usb-preboot.service (power cycle до монтирования) | RTL9210B-CG crashed state через software reboot |
| v1.3.7 | nas_jetson_nano-usb-monitor.service (dmesg watcher) | Telegram alert при первом error -71 |
| v1.3.7 | .gitattributes: LF enforce | CRLF→bash shebang corruption на Windows |
| v1.3.8 | git filter-repo: удалён leaked password hash из 87 коммитов | Security incident |
| v1.3.8 | Ротация паролей (4 сервиса) | После git history rewrite |
| v1.3.8 | immich-microservices mem_limit 512m | OOM protection |
| v1.3.8 | Repo structure refactor: assets/, artifacts/, docs/prompts/ | Open-source conventions |
| v1.3.9 | nas_jetson_nano-ssd-recovery.service (udev hotplug auto-recovery) | Автовосстановление при подключении SSD |
| **v1.4.0** | **JMS583** (152d:a583) заменил RTL9210B-CG | USB 3.0 SuperSpeed, write 250 MB/s, UAS quirk |
| **v1.4.0** | **Nextcloud Talk** «Семья», 5 участников (+ anna) | Семейный чат, история на SSD |
| **v1.4.0** | **NAS_Jetson_Nano API v0.6.0**: Talk/Users/Photos/Actions (11 новых endpoints) | Control + chat + stats API |
| **v1.4.0** | goss 40/40 (+6 тестов) | Покрытие JMS583, Talk, новых сервисов |
| Отменено | WireGuard через VPS | DKMS несовместим с Tegra kernel 4.9 (ADR-0003) |
| Отменено | Tailscale | Конфликт VPN-профиля с Amnezia на Android (ADR-0004) |

### Оценки (1–10)

| Критерий | Оценка | Комментарий |
|---|---|---|
| Готовность к статье | 8/10 | Всё работает, документация глубокая, 9/13 скриншотов готовы |
| Инженерная зрелость | 8/10 | mem_limit, healthchecks, fail-closed backup, systemd watchdog |
| Воспроизводимость | 7/10 | .env.example + Quick Start + ADR + промпты есть; JMS583 swap не задокументирован |
| Уникальность сюжета | 9/10 | USB SSD нестабильность + AI-assisted engineering = редкий жанр |
| Состояние CI/CD | 7/10 | 4 workflows работают; Trivy и actionlint есть, но не все scripts покрыты |
| Тестовое покрытие | 6/10 | goss 34 теста, smoke-тесты есть; k6 нагрузочный не запускался live |
| Безопасность | 7/10 | Secrets scan CI, no secrets in git, filter-repo done; Docker 20.10.7 устарел |
| Документация | 9/10 | 24+ doc-файла, ADR-0001..0006, двуязычные, промпты, TEST_PLAN, runbook |
| Android-интеграция | 8/10 | Immich + Nextcloud + DAVx⁵ настроены; документация MIUI quirks подробная |
| AI-assisted workflow | 9/10 | AGENTS.md, 5 domain-agents, промпты, CLAUDE.md — образцовая модель |

---

## 5. Hardware Layer

| Компонент | Модель | Характеристики | Проблемы |
|---|---|---|---|
| Вычислительный узел | NVIDIA Jetson Nano Dev Kit | 4 GB LPDDR4, ARM64, GPU Maxwell | Docker 20.10.7 устарел; нет swap (zram 1.9 GB) |
| Системный диск | microSD + Kingston USB | 64 GB (60 GB для OS); 28% использовано | Износ microSD — риск; нет мониторинга wear |
| USB-хаб | Realtek 0bda:5411 | 4-портовый | Ранее входил в autosuspend, убивая дочерние устройства |
| USB SSD (текущий) | **JMS583** (152d:a583) | 229 GB, USB 3.0 SuperSpeed, 5 Gbps, Write 250 MB/s | UAS quirk активен; SMART базовый (smartmontools 6.6) |
| USB SSD (заменён) | DEXP / Realtek RTL9210B-CG | 232 GB, USB 2.0 (деградация), ~40 MB/s | 3x error -71, SMART заблокирован — **заменён 2026-06-28** |
| VPS | Ubuntu 24.04 · 1 vCPU · 2 GB RAM | Vienna | Amnezia VPN (25 клиентов) — не трогать |

**Аппаратные риски:**
- Docker 20.10.7 (2021) — устаревший, известные CVE (F-01, Open)
- microSD wear: нет мониторинга S.M.A.R.T. для встроенной карты
- RTL9210B-CG **заменён** на JMS583 (2026-06-28). Watchdog ✅ active.

---

## 6. Service Layer

| Контейнер | Image | Порт | mem_limit | Healthcheck | restart | Статус |
|---|---|---|---|---|---|---|
| homecloud_nextcloud | nextcloud:apache | 8080 | 512m | /status.php | always | ✅ |
| homecloud_nextcloud_db | postgres:16-alpine | — | 512m | pg_isready | always | ✅ |
| homecloud_nextcloud_redis | redis:7-alpine | — | 64m | redis-cli ping | always | ✅ |
| homecloud_immich_server | immich-server:release | 2283 | 1024m | /api/server/ping | always | ✅ |
| homecloud_immich_db | pgvecto-rs:pg16 | — | 384m | pg_isready | always | ✅ |
| homecloud_immich_redis | redis:7-alpine | — | 64m | redis-cli ping | always | ✅ |
| homecloud_immich_microservices | immich-server:release | — | 512m | (нет) | always | ✅ |
| homecloud_llm_gateway | custom FastAPI | 8090 | 256m | /health | always | ✅ |
| homecloud_nas_jetson_nano_api | custom FastAPI | 8099 | 128m | /healthcheck | always | ✅ |
| homecloud_samba | crazymax/samba | 445/139 | не задан | (нет) | always | ✅ LAN only |
| homecloud_netdata | netdata:latest | 19999 | 256m | /api/v1/info | always | ✅ |
| homecloud_uptime_kuma | louislam/uptime-kuma:1 | 3001 | 128m | built-in | always | ✅ 5 monitors |
| homecloud_portainer | portainer/portainer-ce | 9000 | 128m | (scratch) | always | ✅ |

**Примечания:**
- IMMICH_DISABLE_MACHINE_LEARNING=true — обязательно для Jetson 4 GB (нет swap + GPU RAM shared)
- Samba доступна только из LAN через iptables (192.168.0.0/24 → 445/139)
- Beszel Agent работает как systemd-юнит вне Docker (arm64 binary 0.18.7)
- immich-microservices не имеет healthcheck — возможно незначительный gap

---

## 7. Network Layer

### Топология

```
LAN (192.168.0.0/24)
  └─ Jetson Nano: 192.168.0.50 (static DHCP)
       └─ iptables: Samba LAN-only, DROP остальное для 445/139

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
  :45876       — Beszel Agent Jetson (через VPS tunnel)
  :45877       — Beszel Agent VPS (localhost)
```

### Архитектурные решения (ADR)

| ADR | Решение | Статус |
|---|---|---|
| ADR-0001 | Nextcloud + Immich + DeepSeek Gateway | Accepted |
| ADR-0002 | USB SSD хранилище, UUID/fstab | Accepted |
| ADR-0003 | LAN-only (нет direct internet exposure) | Accepted |
| ADR-0004 | Tailscale — отклонён (VPN-конфликт на Android) | Rejected |
| ADR-0005 | autossh reverse SSH tunnel (CGNAT bypass) | Implemented |
| ADR-0006 | HTTPS self-signed на alt-портах (нет домена) | Accepted |

### Известные ограничения сети

- Нет доменного имени → Let's Encrypt недоступен → self-signed TLS + браузерное предупреждение
- VPS IP может меняться (нет DDN) → ручное обновление VPS_HOST в .env
- Порт 443 занят Amnezia xray — не трогать

---

## 8. Storage Layer

| Параметр | Значение |
|---|---|
| Устройство | /dev/sda1 (JMS583 · 152d:a583) |
| Размер | 229 GB ext4 |
| Использование | ~3% (~7 GB) |
| Монтирование | /mnt/storage · UUID в /etc/fstab · noatime |
| Скорость | Write **250 MB/s** · Read **172 MB/s** (dd bs=1M) |
| Preflight | scripts/storage/storage_preflight.sh (errors=0 verified) |
| Backup | pg_dump · gzip · /mnt/storage/backups/database-dumps · 7-day rotation |
| Backup guard | fail-closed: не пишет в microSD если /mnt/storage не mountpoint |
| SMART | Базовый (smartmontools 6.6, SAT passthrough ограничен) |
| USB quirks | **usb-storage.quirks=152d:a583:u** (UAS quirk, BOT mode, extlinux.conf) |
| USB autosuspend | usbcore.autosuspend=-1 (kernel param, подтверждён после reboot) |
| SCSI timeout | 120s (udev правило, активно) |

### История инцидентов USB SSD

| Дата | Событие | Причина | Решение |
|---|---|---|---|
| 2026-06-23 | error -71, SSD исчез с шины, Docker offline | RTL9210B-CG + USB autosuspend | Физическое переподключение + storage_preflight |
| 2026-06-24 | USB watchdog установлен | Предотвращение повторения | udev power/control=on, smartd, autosuspend=-1 |
| 2026-06-26 | error -71 при boot | Порт 4 (1-2.4) аппаратно сломан | Переткнут в порт 2 (1-2.2) |
| 2026-06-26 | CRLF в shebang | git на Windows конвертировал LF→CRLF | .gitattributes LF enforce + dos2unix |
| 2026-06-27 | Всё работает стабильно | preboot + monitor + port 2 | 7 boot подряд без инцидентов |
| 2026-06-28 | nas_jetson_nano-ssd-recovery.service (udev hotplug) | Автовосстановление при горячем подключении | udev → mount → preflight → docker start |

### off-site backup

**Статус: не реализован.** Скрипты restic готовы (`scripts/backup/restic_backup_example.sh`), но restic backup на VPS не настроен и не запущен. Это критический gap для статьи (нет полного disaster recovery).

---

## 9. Android Client Layer

| Приложение | Статус | URL | Примечание |
|---|---|---|---|
| Immich | ✅ настроен, работает | http://193.8.215.130:2283 | 6723 файлов, 31 альбом, бэкап активирован |
| Nextcloud | ✅ настроен | https://193.8.215.130:8443 | HTTPS, self-signed → принять 1 раз |
| DAVx⁵ | ✅ настроен | https://193.8.215.130:8443/remote.php/dav | 2151 контакт импортируется |
| Samba | LAN only | \\192.168.0.50\public | Доступен в домашней сети |
| Immich local URL | Не настроен | http://192.168.0.50:2283 | Приоритет по WiFi (TP-Link_828C) |

**Документация Android:** `docs/android/ANDROID_SETUP.md`, `GOOGLE_MIGRATION.md`, `XIAOMI_MIUI_QUIRKS.md` — подробные пошаговые инструкции для Xiaomi MIUI/HyperOS.

**Специфика MIUI:** battery whitelist, автозапуск, блокировка в RAM — задокументированы в `XIAOMI_MIUI_QUIRKS.md`. Это ценный материал для статьи (проблема знакома большинству пользователей Xiaomi).

---

## 10. AI-Agent Automation Layer

Это один из наиболее сильных аспектов проекта для статьи.

### Инфраструктура агентов

| Файл | Назначение |
|---|---|
| `AGENTS.md` | Правила работы агентов: hard limits, safety boundaries, workflow |
| `CLAUDE.md` | Контекстный файл для Claude Code: живое состояние системы |
| `docs/20_AGENT_OPERATING_MODEL.md` | Операционная модель: 6 ролей субагентов, safety gates, workflow |
| `docs/prompts/CODEX_*.md` | 8+ промптов для субагентов по областям (Storage, Android, LLM, Security...) |

### 5 domain agents (Prompt A model)

| Агент | Промпт-файл | Зона ответственности |
|---|---|---|
| Code Agent | `CODEX_CODE_AGENT.md` | services/, Dockerfiles, CI |
| Hardware Agent | `CODEX_HARDWARE_AGENT.md` | scripts/diagnostics/, systemd/, Jetson SSH |
| Docs Agent | `CODEX_DOCS_AGENT.md` | docs/, README, CHANGELOG, ADR |
| Network Agent | `CODEX_NETWORK_AGENT.md` | scripts/network/, docker/vps/, VPS nginx |
| SysApps Agent | `CODEX_SYSAPPS_AGENT.md` | docker/compose/, configs/, .env.example |

### Паттерны AI-assisted workflow в проекте

- Claude Code запускал параллельные субагенты для Bootstrap prompt (4 агента одновременно)
- `AGENTS.md` — «память агента между сессиями»; жёсткие правила предотвращают повторные инциденты (Amnezia VPN)
- Агент генерировал systemd-юниты, udev-правила, CRLF-fix, filter-repo — задачи, требующие специфических знаний
- AI предупредил о рисках WireGuard на Tegra kernel 4.9 (несовместимость DKMS)
- После VPN-инцидента правило «не трогать Amnezia» зафиксировано в AGENTS.md — агент напоминает при любой попытке

### Честная оценка подхода

**Плюсы:**
- Скорость: недели DevOps → часы
- Документация создаётся параллельно с кодом
- Ошибки фиксируются в ADR, не теряются
- Агент знает нормы GitHub open-source (CI, badges, CODEOWNERS)

**Минусы:**
- Агент не знает конкретное железо — нужно объяснять детали (USB-SATA мост, реальное RAM)
- Финальная проверка — всегда человек: firewall, fstab, пароли
- Контекст сессии конечен — решается AGENTS.md + CLAUDE.md

---

## 11. Reliability and Validation Layer

### CI/CD (GitHub Actions)

| Workflow | Триггер | Что проверяет | Статус |
|---|---|---|---|
| secrets-check.yml | push/PR → main | bash check_no_secrets.sh | ✅ |
| shellcheck.yml | push/PR scripts/** | shellcheck --severity=error | ✅ |
| validate-compose.yml | push/PR docker/** | docker compose config --quiet | ✅ |
| quality-checks.yml | push/PR | (дополнительные проверки) | ✅ |

### Тестирование

| Тип | Инструмент | Покрытие | Статус |
|---|---|---|---|
| Infrastructure state | goss v0.4.9 | 34 теста (порты, сервисы, файлы, HTTP) | 33/34 прошли (1 — nas_jetson_nano-api /health transient) |
| Shell scripts | shellcheck | scripts/ (**/*.sh) | CI, 11/14 чистые |
| Python code | bandit | services/ (738 строк) | 0 проблем безопасности |
| Dockerfiles | hadolint | 3 Dockerfile | 3/3 чистые |
| Service smoke | curl | Nextcloud, Immich, LLM GW, nas_jetson_nano-api | ✅ скрипты в tests/service/ |
| Storage mount | mountpoint + df | /mnt/storage | ✅ скрипты в tests/storage/ |
| SMART | smartctl | /dev/sda | ⚠️ заблокирован RTL9210B-CG (docs в smart_check.sh) |
| Load test (k6) | k6 | nextcloud-smoke.js (5 VU/2min) | Скрипт готов, live не запускался |
| Backup restore | rsync dry-run | tests/backup/restore_test.sh | Скрипт готов, не задокументировано live прохождение |
| Android manual | ADB (readonly) | tests/android/adb_readonly_check.sh | Скрипт готов; ручная проверка выполнена |
| Network | connectivity_check.sh | Jetson + VPS | ✅ |

### Resilience findings (doc/22_AUDIT_RESILIENCE.md)

| ID | Серьёзность | Статус |
|---|---|---|
| F-01 | CRITICAL: Docker 20.10.7 устарел | Open (нетривиальное обновление на JetPack) |
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

**Сильные стороны для статьи:**

1. **Реальная история USB SSD crisis.** Три инцидента с RTL9210B-CG задокументированы с kernel logs, recovery procedures, постморемами. Это живой инженерный нарратив.

2. **AI-assisted engineering workflow.** AGENTS.md как «память агента», 5 domain-agents, параллельные субагенты, реальные промпты — это уникальный паттерн, не описанный на Habr.

3. **Архитектура CGNAT bypass.** ADR-0005 объясняет почему Tailscale и WireGuard были отклонены и как autossh reverse tunnel решает задачу без domain name.

4. **Билингвальная документация.** 24+ документа на RU+EN, ADR-0001..0006, TEST_PLAN, TEST_MATRIX, RUNBOOK — проект готов для международной аудитории.

5. **Воспроизводимая Quick Start инструкция.** `config/.env.example` + 5 docker compose команд + goss validate = полный deploy path.

6. **Реальные пользователи.** 4 аккаунта (admin, olga, ivan, ulyana), 6723 фото в Immich, 2151 контакт — система используется семьёй, не только тестируется.

7. **Честный список ограничений.** Known Limitations раздел в README: устаревший Docker, self-signed TLS, нет off-site backup, ML отключён.

8. **Единственное фото стенда.** `assets/photos/test_sys.jpg` — Jetson Nano на роутере + DEXP-плата. Реальный стенд.

---

## 13. What Is Not Ready Yet

**Пробелы, которые нужно закрыть до публикации:**

1. **Скриншоты частично готовы.** Сделаны: Immich web, Nextcloud dashboard, Nextcloud Talk, Telegram report, Immich Android (галерея + профиль + бэкап), Nextcloud Android, DAVx⁵. Ещё нужны (LAN only): Portainer (13 контейнеров), Beszel Hub (CPU/RAM графики), Uptime Kuma (5 мониторов), NAS_Jetson_Nano API Swagger UI. Все в `assets/screenshots/article/`.

2. **Live замеры производительности не задокументированы.** I/O benchmark (`scripts/storage/benchmark_io.sh` существует, но результатов нет). 40 MB/s на RTL9210B-CG — цифра есть в README, источник неясен.

3. **off-site backup не реализован.** restic скрипты готовы, но backup на VPS не настроен. Если это упомянуть в статье — читатели спросят «а как восстановиться если Jetson умрёт?».

4. **k6 load test не запускался live.** Скрипт есть (`tests/load/nextcloud-smoke.js`), результатов нет.

5. **Docker 20.10.7 открытая уязвимость (F-01).** Для статьи желательно либо обновить, либо явно объяснить почему нетривиально (JetPack зависимости).

6. **JMS583 замена не задокументирована.** Ключевое планируемое событие (прибыл 2026-06-28) — нет документа о процедуре замены и валидации после.

7. **Backup restore не протестирован end-to-end.** `tests/backup/restore_test.sh` существует, но нет доказательства live прохождения.

8. **CHANGELOG содержит только v1.3.8 тег.** v1.3.9 упомянут в CLAUDE.md, но не в CHANGELOG — несоответствие для читателей репозитория.

---

## 14. Risks Before Publication

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| Docker 20.10.7 CVE | Medium | High | Задокументировать в Known Limitations; добавить Trivy в CI |
| off-site backup отсутствует | High | High | Добавить раздел «что будет если Jetson умрёт» в статью |
| RTL9210B-CG до замены JMS583 | High | Critical | Watchdog остановлен; написать в статье как реальный open item |
| VPS IP без домена | Medium | Medium | DDNS или купить домен (Issue #4 в GitHub) |
| Утечка секретов в будущих коммитах | Low | Critical | CI secrets-check активен; .gitignore корректен |
| Miui battery kill Immich backup | Medium | Medium | Задокументировано в XIAOMI_MIUI_QUIRKS.md |
| Wear microSD | Low | High | Нет мониторинга; добавить в Netdata или systemd timer |

---

## 15. Evidence Package Checklist

Что нужно подготовить для сопровождения статьи:

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

---

## 16. Habr Article Plan

**Заголовок:** Домашнее облако на Jetson Nano: задумал я — реализовал Claude Code. История трёх USB-инцидентов, 13 Docker-контейнеров и семейного фотоархива

**Хабы:** Системное администрирование · Open Source · Искусственный интеллект · Self-hosted  
**Теги:** `selfhosted` `nextcloud` `immich` `jetson-nano` `docker` `homelab` `claude-code` `ai-assisted-dev` `usb-storage`

---

### Структура статьи

**Лид (до cut):** 3-4 абзаца — личная история (Jetson в ящике, HDD от сына, Google Photos без места), идея, ключевой сюжет: не «как поднять Nextcloud», а «как строили отказоустойчивость вокруг нестабильного железа с помощью AI».

---

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

---

## 17. Hackaday.io Project Plan

**Название проекта:** Home Cloud for Old Hardware — Jetson Nano Family Server

**Tagline:** Turn forgotten Jetson Nano + USB drive into a private family cloud replacing Google Photos, Drive, and Contacts. Survived 3 USB SSD failures. Built with AI.

**Категории:** Raspberry Pi · Linux · Software · Home Automation

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

**Главный сюжет:** «Reliability story + AI-assisted engineering»

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

---

## 19. Priority Fixes Before Publication

Критичный (нельзя публиковать без этого):

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

---

## 20. Final Recommendation

**Публиковать? Да, после скриншотов.**

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

---

*Отчёт создан автоматически на основании анализа репозитория. Проверить все утверждения об актуальном live-состоянии системы.*
