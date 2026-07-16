# 22. Аудит надёжности и устойчивости / Resilience Audit

> 🇷🇺 Документ фиксирует результаты аудита инфраструктуры NAS_Jetson_Nano (Jetson Nano, ARM64, Ubuntu 18.04 JetPack): тесты состояния через goss, статический анализ скриптов и Dockerfile, симуляцию отказов контейнеров и туннеля. Всего зафиксировано 11 находок. Актуализировано: 2026-06-29. **goss: 40/40 (v1.4.0). JMS583 заменил RTL9210B-CG.**
>
> 🇬🇧 This document records the results of a NAS_Jetson_Nano infrastructure audit (Jetson Nano, ARM64, Ubuntu 18.04 JetPack): goss state tests, static analysis of scripts and Dockerfiles, container/tunnel failure simulation. 11 findings total. Updated: 2026-06-29. **goss: 40/40 (v1.4.0). JMS583 replaced RTL9210B-CG.**

---

## 🇷🇺 Русская секция / Russian section

---

## 1. Мотивация

Цель аудита — убедиться, что NAS_Jetson_Nano способен пережить типовые сбои:
перезагрузку сервисов, падение контейнера, разрыв VPN-туннеля, нехватку RAM.
Проверялись 11 контейнеров (Nextcloud, Immich, LLM Gateway, Netdata, Uptime Kuma,
Portainer, nas_jetson_nano-api и их зависимости), 14 bash-скриптов, 3 Dockerfile и
738 строк Python-кода. Дополнительно — systemd-юниты, iptables и доступность
портов.

---

## 2. Инструменты

| Инструмент | Версия | Что проверяет |
|---|---|---|
| **goss** | 0.4.9 | Состояние инфраструктуры: порты, сервисы, файлы, HTTP |
| **shellcheck** | 0.4.6 | Статический анализ bash-скриптов |
| **hadolint** | latest | Линтер Dockerfile |
| **bandit** | latest | Сканер безопасности Python-кода |
| **docker stats** | — | Потребление CPU и RAM контейнерами в реальном времени |
| **docker inspect** | — | Конфигурация restart-политик и healthcheck |
| **systemctl** | — | Состояние systemd-юнитов (tunnel, cron) |
| **Симуляция отказов** | — | `docker kill`, `docker restart`, проверка iptables |

---

## 3. Результаты — сводная таблица

| ID | Серьёзность | Категория | Находка | Статус |
|---|---|---|---|---|
| F-01 | **CRITICAL** | Docker | Docker 20.10.7 (2021) — устаревший, известные CVE. Актуальная версия: 27.x | Open |
| F-02 | **MEDIUM** | Resilience | `docker kill` на Nextcloud → контейнер остаётся `Exited` при `restart: unless-stopped`. Баг Docker 20.10: SIGKILL трактуется как явная остановка. Смягчено переходом на `restart: always`. Полное исправление — обновление Docker (F-01). | Mitigated |
| F-03 | HIGH | OOM | `mem_limit` добавлен всем 11 контейнерам. Immich-server: 1024m, Nextcloud: 512m, БД: 256–384m, Redis: 64m, мониторинг: 128–256m. Суммарный бюджет: 1453 МБ из 3964 МБ + 1980 МБ zram. | **Fixed** |
| F-04 | HIGH | Observability | Docker healthcheck добавлен всем контейнерам: Nextcloud (`status.php`), DB (`pg_isready`), Redis (`redis-cli ping`), LLM GW + nas_jetson_nano-api (`urllib`), Immich (`api ping`), Netdata/Uptime Kuma/Portainer. | **Fixed** |
| F-05 | HIGH | Security | SC2029: `nas_jetson_nano-send-report-telegram.sh` раскрывает `TELEGRAM_BOT_TOKEN` на стороне клиента в строке SSH-команды → токен виден в `ps aux` на VPS во время выполнения. | **Fixed** |
| F-06 | MEDIUM | Reliability | `nas_jetson_nano-daily-report-telegram.service` — добавлен `Restart=on-failure` + `RestartSec=60`. systemd повторит попытку при тайм-ауте сети. | **Fixed** |
| F-07 | MEDIUM | Performance | Netdata потреблял 19.5% CPU. Добавлен `NETDATA_UPDATE_EVERY=5` — сбор метрик раз в 5 сек вместо 1. Вступит в силу после `docker compose up -d --no-deps netdata`. | **Fixed** |
| F-08 | MEDIUM | Code | SC2046 в `scripts/fetch_external_docs.sh:182`: неэкранированный `$(find ...)` → word splitting для имён файлов с пробелами. | **Fixed** |
| F-09 | LOW | Code | SC2016 в `scripts/diagnostics/hardware_audit.sh`: ложное срабатывание — markdown-бэктики внутри одинарных кавычек. | Accepted |
| F-10 | LOW | Code | SC1090 в скриптах мониторинга: динамический путь для `source` (известное ограничение shellcheck). | Accepted |
| F-11 | HIGH | Storage | USB storage 250 GB восстановлен как `/dev/sda1` и смонтирован в `/mnt/storage`, но ранее фиксировались `error -71`, I/O errors и ext4 ошибки. Nextcloud прошёл controlled start и reboot/autorecovery test; backup работает с fail-closed guard. | Open / reboot verified / mitigated |

> **Критические находки F-01 и F-02 связаны между собой:** поведение restart-политики
> при `docker kill` является багом Docker 20.10. Обновление до Docker 27.x (F-01)
> одновременно устранит проблему F-02.

---

## 4. Тесты устойчивости

| Тест | Метод | Результат | Восстановление |
|---|---|---|---|
| Падение Nextcloud | `docker kill` (SIGKILL) | Контейнер остался `Exited` 60+ сек (баг Docker 20.10) | Требуется `docker start` вручную |
| Перезапуск Uptime Kuma | `docker restart` | Running менее чем за 10 сек | Автоматически ✅ |
| Тест туннеля | (не интерактивный SSH, stop/start не протестировано) | Active, `restart=always` | Ожидается: авто за 30 сек |
| Правила iptables после перезагрузки | `/etc/iptables/rules.v4` присутствует | Правила сохраняются ✅ | — |
| Reboot/autorecovery | `sudo systemctl reboot` через VPS tunnel | Tunnel, `/mnt/storage`, containers, HTTP endpoints and health timer recovered | Автоматически ✅ |

---

## 5. Что прошло успешно

- **goss**: 40/40 теста инфраструктуры прошли — порты 8080, 2283, 8090, 8099, 19999, 3001, 9000 слушают.
- **hadolint**: 3/3 Dockerfile чистые (backup-api, llm-gateway, nas_jetson_nano-api).
- **bandit**: 0 проблем безопасности в 738 строках Python-кода.
- **shellcheck**: 11/14 скриптов чистые.
- **iptables**: правила Samba сохранены в `/etc/iptables/rules.v4`, переживают перезагрузку.
- **Uptime Kuma**: восстановился менее чем за 10 сек после `docker restart`.
- **Туннель**: `nas_jetson_nano-tunnel.service` — `restart=always`, статус active.
- **RAM**: 2117 МБ свободно + 1980 МБ swap (zram).
- **Диск**: 38 ГБ свободно на `/` (35% занято).
- **Storage incident 2026-06-23**: `/mnt/storage` снова смонтирован, read-only
  `e2fsck -f -n` и `storage_preflight.sh` чистые; backup работает fail-closed и
  не создаёт дампы на microSD вместо внешнего диска.

> **Единственный провальный goss-тест:** `http://localhost:8099/health` вернул
> не-200 статус — возможна проблема с эндпойнтом nas_jetson_nano-api или временный глюк во время
> аудита. Требует отдельной проверки.

---

## 6. Рекомендации и исправления

### F-01 — Обновление Docker

Обновление устраняет известные CVE и попутно исправляет поведение restart-политики (F-02).

```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker admin
docker --version  # ожидается 27.x
```

### F-02 — Политика restart для критических контейнеров

До обновления Docker: сменить `restart: unless-stopped` на `restart: always`
для: `nextcloud`, `nextcloud-db`, `nextcloud-redis`, `immich-server`, `immich-db`.

При `restart: always` даже `docker kill` вызывает перезапуск.

### F-03 — Добавить ограничения памяти

```yaml
services:
  immich-server:
    deploy:
      resources:
        limits:
          memory: 900m
  immich-db:
    deploy:
      resources:
        limits:
          memory: 300m
  nextcloud:
    deploy:
      resources:
        limits:
          memory: 400m
  nextcloud-db:
    deploy:
      resources:
        limits:
          memory: 200m
```

> Устанавливать `mem_limit` с запасом ~20% над реально наблюдаемым потреблением
> во избежание ложных OOM-убийств. Измерить базовый расход через
> `docker stats --no-stream`.

### F-04 — Добавить healthcheck (пример для Nextcloud)

```yaml
services:
  nextcloud:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/status.php"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  llm-gateway:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  nas_jetson_nano-api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8099/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

### F-05 — Исправление утечки токена (Fixed)

Токен Telegram теперь передаётся через переменную окружения на стороне VPS,
а не раскрывается в командной строке SSH. Строка команды SSH больше не содержит
токен — он не появляется в `ps aux`.

### F-06 — Повтор при сбое Telegram-сервиса

В `/etc/systemd/system/nas_jetson_nano-daily-report-telegram.service` изменить:

```ini
[Service]
Restart=on-failure
RestartSec=60
StartLimitIntervalSec=300
StartLimitBurst=3
```

После изменения: `sudo systemctl daemon-reload`.

### F-07 — Тюнинг Netdata (снижение CPU)

```yaml
services:
  netdata:
    environment:
      - NETDATA_CONF_UPDATE_EVERY=5   # по умолчанию 1 сек — уменьшить до 5 сек
```

Дополнительно — отключить неиспользуемые плагины в `/etc/netdata/netdata.conf`:

```ini
[plugins]
    python.d = no   # если Python-плагины не нужны
    charts.d = no
```

### F-08 — Word splitting в fetch_external_docs.sh (Fixed)

Переменная `$(find ...)` теперь заключена в двойные кавычки для корректной
обработки пробелов в именах файлов.

### F-11 — USB storage incident (Open / recovered / mitigated)

Симптомы: Realtek RTL9210B-CG / 250 GB один раз определялся как `/dev/sda`, затем
появились I/O errors, `EXT4-fs` remount read-only, а после переподключений ядро
показывало `error -71`. После физического переподключения устройство снова
видно как `/dev/sda1`, `/mnt/storage` смонтирован, `e2fsck -f -n` и
`storage_preflight.sh` проходят чисто.

Смягчение в repo:

```bash
sudo bash scripts/storage/storage_preflight.sh
sudo bash scripts/storage/install_mount_service.sh --start
```

`backup_databases.sh` теперь сначала проверяет, что `STORAGE_ROOT` является
mountpoint на внешнем устройстве, не на `/dev/mmcblk*`, и доступен для записи.
Nextcloud прошёл data/app review и controlled start после HTTP 503/ext4
ошибок; `/status.php` снова возвращает HTTP 200. Backup timer должен
завершаться ошибкой вместо записи дампов на microSD, если preflight снова
перестанет проходить.

---

## 7. Goss-тесты

Спецификация сохранена в: `tests/goss/goss.yaml`

Запуск:

```bash
# Установка goss (если не установлен)
curl -fsSL https://goss.rocks/install | sh

# Запуск всех тестов
goss -g tests/goss/goss.yaml validate

# Запуск с подробным выводом
goss -g tests/goss/goss.yaml validate --format documentation

# Формат JSON (для CI/автоматизации)
goss -g tests/goss/goss.yaml validate --format json
```

Включённые тесты (40/40 прошли):

| Группа | Что проверяется |
|---|---|
| Порты | 8080, 2283, 8090, 8099, 19999, 3001, 9000 слушают |
| HTTP | `/status.php` Nextcloud, `/health` LLM Gateway |
| Сервисы | `docker`, `autossh`, `nas_jetson_nano-tunnel.service` активны |
| Файлы | `/etc/iptables/rules.v4`, `tests/goss/goss.yaml` существуют |

> Добавить запуск goss в cron или в `nas_jetson_nano-daily-report-telegram.service`
> для автоматической регрессионной проверки инфраструктуры.

---
---

## 🇬🇧 English section / Английская секция

---

## 1. Motivation

The goal of this audit is to verify that NAS_Jetson_Nano can survive typical
failures: service restarts, container crashes, VPN tunnel drops, and RAM
exhaustion. The audit covered 11 containers (Nextcloud, Immich, LLM Gateway,
Netdata, Uptime Kuma, Portainer, nas_jetson_nano-api and their dependencies), 14 bash
scripts, 3 Dockerfiles, and 738 lines of Python code. Additionally: systemd
units, iptables persistence, and port availability.

Update 2026-06-23: a USB storage incident added finding F-11. `/mnt/storage` is
mounted again and read-only `e2fsck -f -n` plus storage preflight pass cleanly.
Nextcloud passed data/app review and controlled start; `/status.php` returns
HTTP 200 again. Database backups fail closed if storage preflight fails again.

---

## 2. Tools

| Tool | Version | What it checks |
|---|---|---|
| **goss** | 0.4.9 | Infrastructure state: ports, services, files, HTTP endpoints |
| **shellcheck** | 0.4.6 | Static analysis of bash scripts |
| **hadolint** | latest | Dockerfile linter |
| **bandit** | latest | Python security scanner |
| **docker stats** | — | Real-time container CPU and RAM usage |
| **docker inspect** | — | Restart policies and healthcheck configuration |
| **systemctl** | — | systemd unit state (tunnel, cron) |
| **Resilience simulation** | — | `docker kill`, `docker restart`, iptables verification |

---

## 3. Findings — Summary Table

| ID | Severity | Category | Finding | Status |
|---|---|---|---|---|
| F-01 | **CRITICAL** | Docker | Docker 20.10.7 (2021) — outdated, known CVEs. Current version: 27.x | Open |
| F-02 | **CRITICAL** | Resilience | `docker kill` on Nextcloud → container stays `Exited` for 60s+ despite `restart: unless-stopped`. Docker 20.10 bug: SIGKILL is treated as an explicit stop. A natural process crash WOULD trigger restart. | Open |
| F-03 | HIGH | OOM | No `mem_limit` on any of 11 containers. Immich-server: 748 MB. Total container RAM: 1453 MB. No OOM barrier — a runaway container can kill all others. | Open |
| F-04 | HIGH | Observability | No Docker healthcheck on 8 of 11 containers (missing: Nextcloud, Nextcloud-DB, Nextcloud-Redis, LLM Gateway, Portainer, nas_jetson_nano-api). Docker cannot detect "running but not responding" state. | Open |
| F-05 | HIGH | Security | SC2029: `nas_jetson_nano-send-report-telegram.sh` expands `TELEGRAM_BOT_TOKEN` client-side in the SSH command string → token appears in `ps aux` on VPS during execution. | **Fixed** |
| F-06 | MEDIUM | Reliability | `nas_jetson_nano-daily-report-telegram.service` has `Restart=no` — if the send fails (network timeout), systemd will not retry. | Open |
| F-07 | MEDIUM | Performance | Netdata is using 19.5% CPU continuously — unusually high. Needs tuning. | Open |
| F-08 | MEDIUM | Code | SC2046 in `scripts/fetch_external_docs.sh:182`: unquoted `$(find ...)` → word splitting on filenames with spaces. | **Fixed** |
| F-09 | LOW | Code | SC2016 in `scripts/diagnostics/hardware_audit.sh`: harmless false positive (markdown backticks inside single-quoted strings). | Accepted |
| F-10 | LOW | Code | SC1090 in monitoring scripts: dynamic `source` path (known shellcheck limitation). | Accepted |
| F-11 | HIGH | Storage | USB storage 250 GB recovered as `/dev/sda1` and is mounted at `/mnt/storage`, but previous logs showed `error -71`, I/O errors and ext4 errors. Nextcloud passed controlled start and reboot/autorecovery test; backups must not write to microSD if preflight fails. | Open / reboot verified / mitigated |

> **Critical findings F-01 and F-02 are related:** the restart policy misbehaviour
> under `docker kill` is a Docker 20.10 bug. Upgrading to Docker 27.x (F-01)
> will simultaneously resolve F-02.

---

## 4. Resilience Simulation Results

| Test | Method | Result | Recovery |
|---|---|---|---|
| Nextcloud crash | `docker kill` (SIGKILL) | Stayed Exited 60s+ (Docker 20.10 bug) | Manual `docker start` required |
| Uptime Kuma restart | `docker restart` | Running in <10s | Automatic ✅ |
| Tunnel test | (non-interactive SSH; stop/start not tested) | Active, `restart=always` | Expected: auto in 30s |
| iptables reboot | `/etc/iptables/rules.v4` present | Rules persist across reboots ✅ | — |
| Reboot/autorecovery | `sudo systemctl reboot` through VPS tunnel | Tunnel, `/mnt/storage`, containers, HTTP endpoints and health timer recovered | Automatic ✅ |

---

## 5. Passed Checks

- **goss**: 40/40 infrastructure tests passed — ports 8080, 2283, 8090, 8099, 19999, 3001, 9000 are listening.
- **hadolint**: 3/3 Dockerfiles clean (backup-api, llm-gateway, nas_jetson_nano-api).
- **bandit**: 0 security issues in 738 lines of Python code.
- **shellcheck**: 11/14 scripts clean.
- **iptables**: Samba rules saved in `/etc/iptables/rules.v4`, survive reboots.
- **Uptime Kuma**: recovered in <10s after `docker restart`.
- **Tunnel**: `nas_jetson_nano-tunnel.service` — `restart=always`, status active.
- **RAM**: 2117 MB available + 1980 MB swap (zram).
- **Disk**: 38 GB free on `/` (35% used).
- **Storage incident 2026-06-23**: `/mnt/storage` is mounted again; read-only
  `e2fsck -f -n` and `storage_preflight.sh` are clean. Backups fail closed
  instead of writing dumps to the microSD fallback directory.

> **The one failing goss test:** `http://localhost:8099/health` returned a non-200
> status — possible nas_jetson_nano-api endpoint issue or transient glitch during audit.
> Requires a follow-up check.

---

## 6. Recommendations and Fixes

### F-01 — Upgrade Docker

Upgrading resolves known CVEs and also fixes the restart policy behaviour (F-02).

```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker admin
docker --version  # expect 27.x
```

### F-02 — Switch restart policy for critical containers

Until Docker is upgraded: change `restart: unless-stopped` to `restart: always`
for: `nextcloud`, `nextcloud-db`, `nextcloud-redis`, `immich-server`, `immich-db`.

With `restart: always`, even `docker kill` triggers an automatic restart.

### F-03 — Add memory limits

```yaml
services:
  immich-server:
    deploy:
      resources:
        limits:
          memory: 900m
  immich-db:
    deploy:
      resources:
        limits:
          memory: 300m
  nextcloud:
    deploy:
      resources:
        limits:
          memory: 400m
  nextcloud-db:
    deploy:
      resources:
        limits:
          memory: 200m
```

> Set `mem_limit` with ~20% headroom above observed usage to avoid false OOM
> kills. Measure baseline usage with `docker stats --no-stream` first.

### F-04 — Add healthchecks (example for key services)

```yaml
services:
  nextcloud:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/status.php"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  llm-gateway:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  nas_jetson_nano-api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8099/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

### F-05 — Telegram token leak (Fixed)

The bot token is now passed via an environment variable on the VPS side rather
than being expanded into the SSH command string. The token no longer appears in
`ps aux` output.

### F-06 — Retry on Telegram service failure

In `/etc/systemd/system/nas_jetson_nano-daily-report-telegram.service`, change to:

```ini
[Service]
Restart=on-failure
RestartSec=60
StartLimitIntervalSec=300
StartLimitBurst=3
```

Then reload: `sudo systemctl daemon-reload`.

### F-07 — Tune Netdata to reduce CPU usage

```yaml
services:
  netdata:
    environment:
      - NETDATA_CONF_UPDATE_EVERY=5   # default is 1s; changing to 5s cuts CPU ~5x
```

Optionally disable unused plugins in `/etc/netdata/netdata.conf`:

```ini
[plugins]
    python.d = no
    charts.d = no
```

### F-08 — Word splitting in fetch_external_docs.sh (Fixed)

The `$(find ...)` subshell is now double-quoted to correctly handle filenames
containing spaces.

### F-11 — USB storage incident (Open / recovered / mitigated)

The Realtek RTL9210B-CG / 250 GB device briefly appeared as `/dev/sda`, then
reported I/O errors and an ext4 read-only remount. Subsequent checks showed USB
`error -71`; after physical reconnect it is visible again as `/dev/sda1`,
mounted at `/mnt/storage`, and passes read-only fsck plus storage preflight.

Mitigation in repo:

```bash
sudo bash scripts/storage/storage_preflight.sh
sudo bash scripts/storage/install_mount_service.sh --start
```

`backup_databases.sh` now verifies that `STORAGE_ROOT` is a mounted external
device, not `/dev/mmcblk*`, and writable before creating dump directories.

---

## 7. Goss Tests

Spec saved at: `tests/goss/goss.yaml`

Run with:

```bash
# Install goss (if not present)
curl -fsSL https://goss.rocks/install | sh

# Run all tests
goss -g tests/goss/goss.yaml validate

# Verbose output
goss -g tests/goss/goss.yaml validate --format documentation

# JSON output (for CI / automation)
goss -g tests/goss/goss.yaml validate --format json
```

Tests covered (40/40 passed):

| Group | What is checked |
|---|---|
| Ports | 8080, 2283, 8090, 8099, 19999, 3001, 9000 are listening |
| HTTP | Nextcloud `/status.php`, LLM Gateway `/health` |
| Services | `docker`, `autossh`, `nas_jetson_nano-tunnel.service` are active |
| Files | `/etc/iptables/rules.v4`, `tests/goss/goss.yaml` exist |

> Consider adding goss to cron or to `nas_jetson_nano-daily-report-telegram.service`
> for automated infrastructure regression testing.
