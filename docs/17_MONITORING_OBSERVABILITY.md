# 17. Мониторинг и наблюдаемость / Monitoring & Observability

> 🇷🇺 Документ описывает выбор инструментов мониторинга для NAS_Jetson_Nano на Jetson Nano (ARM64, 4 GB RAM) и стратегию их поэтапного развёртывания. Актуализировано: 2026-06-27.
>
> 🇬🇧 This document describes monitoring tool selection for NAS_Jetson_Nano on Jetson Nano (ARM64, 4 GB RAM) and phased deployment strategy. Updated: 2026-06-27.
>
> Compose-файл / Compose file: `docker/compose/docker-compose.monitoring.yml`.
> Промпт агента / Agent prompt: `docs/prompts/CODEX_MONITORING_PROMPT.md`.

---

## 🇷🇺 Русская секция / Russian section

---

## 1. Контекст и ограничения

### Аппаратная платформа

| Параметр | Значение |
|---|---|
| Устройство | NVIDIA Jetson Nano 4GB |
| Архитектура | ARM64 (aarch64) |
| RAM | 4 GB (разделена между CPU и GPU, без swap) |
| Хранилище | USB HDD `/mnt/storage` |
| ОС | Ubuntu 18.04 LTS (JetPack) |

### Текущая загрузка RAM — Stage 1

| Сервис | Примерный расход RAM |
|---|---|
| Nextcloud (apache) | ~150–200 MB |
| nextcloud-db (PostgreSQL 16-alpine) | ~80–120 MB |
| nextcloud-redis | ~10–20 MB |
| immich-server | ~200–300 MB |
| immich-microservices | ~150–250 MB |
| immich-db (pgvecto-rs) | ~100–200 MB |
| immich-redis | ~10–20 MB |
| llm-gateway (FastAPI) | ~80–120 MB |
| **Итого Stage 1** | **~780 MB – 1.23 GB** |
| ОС + ядро + системные процессы | ~400–600 MB |
| **Итого занято** | **~1.2 – 1.8 GB** |
| **Свободно** | **~2.2 – 2.8 GB** |

**Бюджет для мониторинга:** ~500 MB – 1 GB RAM без риска OOM.

### Критическое ограничение

Jetson Nano **не имеет swap по умолчанию**. При нехватке RAM ядро убивает
процессы (OOM killer). Это означает, что мониторинг-стек не должен в сумме
превышать ~600–700 MB. При Stage 1 добавление тяжёлого Zabbix + СУБД создаёт
реальный риск OOM для production-сервисов.

---

## 2. Анализ инструментов

### Сводная таблица

| Инструмент | RAM | ARM64 | Сложность | СУБД | Рекомендация |
|---|---|---|---|---|---|
| **Netdata** | 80–120 MB | Первоклассная | Низкая | Нет (rolling buffer) | **РЕКОМЕНДОВАН — Stage 1** |
| **Uptime Kuma** | 50–70 MB | Да | Низкая | SQLite (встроен) | **РЕКОМЕНДОВАН — Stage 1** |
| **Portainer CE** | 50–80 MB | Полная | Низкая | Нет | Рекомендован (удобно) |
| Prometheus | 100–200 MB | Полная | Средняя | Нет (TSDB) | Stage 2 |
| Node Exporter | 5 MB | Полная | Низкая | Нет | Stage 2 (с Prometheus) |
| cAdvisor | 30 MB | Да | Низкая | Нет | Stage 2 (с Prometheus) |
| Grafana | 150–200 MB | Да | Средняя | Нет (встроен) | Stage 2 (с Prometheus) |
| VictoriaMetrics | 50–100 MB | Да | Средняя | Нет (TSDB) | Альтернатива Prometheus |
| Alertmanager | 30–50 MB | Да | Средняя | Нет | Stage 2 |
| **Zabbix** | **300–800 MB** | Ограниченная | Высокая | **Требуется** | **НЕ РЕКОМЕНДОВАН** |

### 2.1 Zabbix

**Описание:** Enterprise-уровень, мощный мониторинг с агентами, шаблонами,
триггерами и дашбордами. Стандарт в корпоративных средах.

**Технические параметры:**
- Zabbix Server: ~300–500 MB RAM
- Zabbix Database (PostgreSQL или MySQL): ~100–300 MB RAM дополнительно
- Zabbix Web Frontend: ~50–100 MB RAM
- Zabbix Agent: ~10 MB (устанавливается на каждый сервер)
- ARM64: образы доступны, но поддержка менее зрелая; периодические проблемы с
  зависимостями на JetPack 18.04

**Проблемы для Jetson Nano:**
1. Требует отдельную СУБД (PostgreSQL или MySQL) именно для сервера Zabbix —
   это третья PostgreSQL в системе (уже есть две: для Nextcloud и Immich).
2. Суммарный расход: ~450–900 MB RAM только на Zabbix-стек.
3. На Jetson с 4 GB при Stage 1 это риск OOM для production-контейнеров.
4. Настройка шаблонов, триггеров и агентов требует значительного времени.
5. Избыточно для 8 контейнеров домашнего облака.

**Когда Zabbix имеет смысл:** Если в LAN есть отдельный сервер (старый ПК,
ноутбук) с 4+ GB RAM, куда можно установить Zabbix-сервер и СУБД, а на Jetson
поставить только лёгкий Zabbix-агент (~10 MB). В этом случае Jetson платит
только 10 MB RAM.

**Вывод: не рекомендован для Jetson в качестве сервера мониторинга.**

---

### 2.2 Prometheus + Node Exporter + cAdvisor

**Описание:** Де-факто стандарт метрик в современной облачной инфраструктуре.
Pull-модель: Prometheus опрашивает экспортёры по HTTP.

**Технические параметры:**
- Prometheus Server: ~100–200 MB RAM (зависит от числа метрик и retention)
- Node Exporter: ~5 MB (метрики хоста: CPU, RAM, диск, сеть)
- cAdvisor: ~30 MB (метрики Docker контейнеров)
- ARM64: полная поддержка для всех трёх компонентов
- Нет встроенного дашборда — нужен Grafana

**Плюсы:**
- Экосистема правил алертов (Alertmanager)
- Интеграция с Grafana
- Хранение метрик с retention (по умолчанию 15 дней)
- Большое сообщество, готовые дашборды

**Минусы для Stage 1:**
- Prometheus сам по себе без Grafana не даёт UI
- Суммарно: Prometheus + cAdvisor + Grafana = ~280–430 MB RAM
- Настройка scrape-конфигов требует времени

**Вывод: рекомендован для Stage 2 вместе с Grafana.**

---

### 2.3 Grafana

**Описание:** Дашборды и визуализация для временных рядов. Работает как фронтенд
для Prometheus, VictoriaMetrics, InfluxDB и других источников.

**Технические параметры:**
- RAM: ~150–200 MB
- ARM64: `grafana/grafana:latest` поддерживает arm64
- Встроенная алертинговая система (Grafana Alerting)
- Порт: 3000 по умолчанию

**Вывод: рекомендован в связке с Prometheus на Stage 2. На Stage 1 избыточен —
Netdata уже даёт полноценный встроенный UI.**

---

### 2.4 Netdata

**Описание:** All-in-one мониторинг реального времени, разработан специально для
SBC (Raspberry Pi, Jetson, Orange Pi). Встроенный веб-интерфейс, автообнаружение
сервисов и Docker-контейнеров.

**Технические параметры:**
- RAM: ~80–120 MB
- ARM64: первоклассная поддержка (нативные пакеты и Docker-образ)
- Нет внешней СУБД — rolling buffer в памяти (rolling window ~1 час по умолчанию,
  настраивается)
- Долгосрочное хранение: опционально через Prometheus remote_write или
  netdata-cloud
- Порт: 19999 (HTTP, рекомендуется ограничить через `bind to = 127.0.0.1` или
  сетевым firewall)

**Что мониторит автоматически (out-of-the-box):**
- CPU: общая загрузка, per-core, softirq, iowait
- RAM: используемая, кэш, буферы, swapless warning
- Диск: I/O, latency, заполненность всех точек монтирования
- Сеть: throughput, packets, errors per interface
- Docker: состояние, CPU%, RAM%, I/O каждого контейнера (через docker.sock)
- PostgreSQL: соединения, latency, deadlocks (через netdata postgresql plugin)
- Redis: память, команды, hit rate
- Системные процессы, температура (Jetson thermal zones через `/sys/class/thermal`)

**Jetson Nano специфика:**
- Температурные зоны `/sys/class/thermal/thermal_zone*` показываются в Netdata
  автоматически
- `tegrastats` данные доступны через `/proc` и `/sys` — Netdata их читает

**Алерты:** Netdata имеет встроенную систему алертов с уведомлениями через
email, Slack, Telegram, PagerDuty и другие. Конфиги алертов: `/etc/netdata/health.d/`.

**Вывод: РЕКОМЕНДОВАН для Stage 1. Лучший выбор для SBC — минимум конфигурации,
максимум метрик из коробки.**

---

### 2.5 Uptime Kuma

**Описание:** Простой self-hosted uptime monitor с красивым UI и уведомлениями.
Аналог UptimeRobot, но локальный. Мониторит HTTP-эндпойнты, TCP-порты, DNS.

**Технические параметры:**
- RAM: ~50–70 MB
- ARM64: официальный образ `louislam/uptime-kuma:latest` поддерживает arm64
- База данных: SQLite (встроена, отдельная СУБД не нужна)
- Порт: 3001 (HTTP, с авторизацией из коробки)

**Что умеет:**
- HTTP/HTTPS: статус-код, время отклика, проверка SSL
- TCP port check
- Ping
- DNS lookup
- Уведомления: Telegram, Email (SMTP), Slack, Discord, Webhook и 90+ интеграций
- История uptime, SLA-статистика, статус-страница

**Для NAS_Jetson_Nano:** Мониторинг Nextcloud (:8080), Immich (:2283),
LLM Gateway (:8090) с уведомлением в Telegram при недоступности.

**Вывод: РЕКОМЕНДОВАН для Stage 1. Telegram-уведомление за 5 минут настройки.**

---

### 2.6 Portainer CE

**Описание:** Docker management UI — управление контейнерами, образами,
сетями, volumes и стеками через браузер.

**Технические параметры:**
- RAM: ~50–80 MB
- ARM64: полная поддержка (`portainer/portainer-ce:latest`)
- Порты: 9000 (HTTP), 9443 (HTTPS)

**Что даёт:**
- Просмотр всех контейнеров, их статусов, логов, stats в реальном времени
- Запуск/остановка/перезапуск контейнеров через UI
- Просмотр и редактирование compose-стеков
- Статистика CPU%, RAM% для каждого контейнера

**Вывод: рекомендован как удобный инструмент, но не обязателен.**

---

### 2.7 cAdvisor (самостоятельно)

**Описание:** Container Advisor от Google — экспортирует метрики Docker
контейнеров в формате Prometheus.

**Технические параметры:**
- RAM: ~30 MB
- ARM64: поддерживается (`gcr.io/cadvisor/cadvisor:latest`)
- Порт: 8080 (конфликт с Nextcloud — нужен иной host-порт или bind IP)

**Вывод: добавить в Stage 2 в связке с Prometheus. На Stage 1 Netdata уже
собирает Docker-метрики через docker.sock без отдельного cAdvisor.**

---

### 2.8 VictoriaMetrics

**Описание:** Высокопроизводительная и компактная альтернатива Prometheus.
Совместима с Prometheus API, принимает данные от Node Exporter и cAdvisor.

**Технические параметры:**
- RAM: ~50–100 MB (значительно меньше Prometheus при том же объёме данных)
- ARM64: поддерживается
- Single-binary режим: один бинарь заменяет Prometheus + Alertmanager
- Долгосрочное хранение без деградации производительности

**Вывод: сильная альтернатива Prometheus на Stage 2. Рассмотреть если
Prometheus окажется слишком тяжёлым на Jetson.**

---

## 3. Рекомендованная стратегия развёртывания

### Stage 1 — минимальный мониторинг (сейчас)

**Цель:** видеть состояние системы, получать алерты, управлять контейнерами.

| Инструмент | RAM | Назначение |
|---|---|---|
| Netdata | ~100 MB | Системный мониторинг + Docker stats + температура |
| Uptime Kuma | ~60 MB | Uptime HTTP-эндпойнтов + Telegram-уведомления |
| Portainer CE | ~60 MB | Docker management UI (опционально) |
| **Итого** | **~220 MB** | |

Compose-файл: `docker/compose/docker-compose.monitoring.yml`

Порты доступа:
- Netdata: `http://192.168.0.50:19999`
- Uptime Kuma: `http://192.168.0.50:3001`
- Portainer: `http://192.168.0.50:9000`

### Stage 2 — полноценная observability (будущее)

**Цель:** долгосрочное хранение метрик, умные алерты, дашборды.

| Инструмент | RAM | Назначение |
|---|---|---|
| Netdata | ~100 MB | Системный мониторинг (оставить) |
| Prometheus | ~150 MB | TSDB для долгосрочных метрик |
| Node Exporter | ~5 MB | Метрики хоста для Prometheus |
| cAdvisor | ~30 MB | Docker-метрики для Prometheus |
| Grafana | ~180 MB | Дашборды |
| Alertmanager | ~40 MB | Умные алерты с группировкой |
| **Итого Stage 2 добавит** | **~405–505 MB** | |

**Альтернатива:** заменить Prometheus + Alertmanager на VictoriaMetrics
single-binary (~100 MB вместо ~190 MB).

### Почему Zabbix не подходит для Jetson

1. **RAM:** Zabbix-сервер + его СУБД = ~400–800 MB. Это съедает весь бюджет
   мониторинга плюс часть запаса production-сервисов.
2. **Третья PostgreSQL:** В Stage 1 уже есть два инстанса PostgreSQL
   (Nextcloud + Immich). Добавление третьего только ради Zabbix нецелесообразно.
3. **Сложность:** Настройка шаблонов, триггеров, items в Zabbix требует
   значительного времени для 8 контейнеров домашнего стека.
4. **OOM риск:** Без swap на Jetson Nano при OOM убиваются production-контейнеры,
   а не мониторинг. Тяжёлый стек мониторинга увеличивает этот риск.

**Единственный сценарий Zabbix:** отдельный Zabbix-сервер на старом ПК в LAN,
Zabbix-агент на Jetson (~10 MB RAM). В этом случае Jetson не несёт нагрузки
от сервера мониторинга.

---

## 4. Метрики для мониторинга в контексте NAS_Jetson_Nano

### Критические метрики

| Метрика | Источник | Порог алерта |
|---|---|---|
| RAM utilization % | Netdata → system.ram | > 90% в течение 2+ мин |
| Disk usage `/mnt/storage` % | Netdata → disk_space | > 85% |
| Disk usage `/` % | Netdata → disk_space | > 90% |
| Container health: любой stopped | Netdata → docker / Portainer | Сразу |
| CPU load (1min avg) | Netdata → system.load | > 3.0 (75% × 4 cores) |

### HTTP uptime метрики (Uptime Kuma)

| Сервис | URL | Ожидаемый статус |
|---|---|---|
| Nextcloud | `http://192.168.0.50:8080` | HTTP 200 |
| Immich | `http://192.168.0.50:2283` | HTTP 200 |
| LLM Gateway | `http://192.168.0.50:8090/health` | HTTP 200 |

### Дополнительные метрики (Netdata автоматически)

- **PostgreSQL:** active connections, transactions/sec, latency, deadlocks
- **Redis:** used_memory, connected_clients, hit rate
- **Температура Jetson:** thermal_zone0 (CPU), thermal_zone1 (GPU)
  — алерт при > 85°C
- **Сеть:** bytes in/out per interface, errors, drops

---

## 5. Алерты — что важно настроить

### Uptime Kuma (HTTP мониторинг)

| Алерт | Условие | Действие |
|---|---|---|
| Nextcloud недоступен | HTTP != 200 дольше 2 мин | Telegram notification |
| Immich недоступен | HTTP != 200 дольше 2 мин | Telegram notification |
| LLM Gateway недоступен | HTTP != 200 дольше 2 мин | Telegram notification |

### Netdata (системные алерты)

Файлы конфигурации алертов: `/etc/netdata/health.d/` (внутри контейнера).

| Алерт | Условие |
|---|---|
| `disk_space_usage` | `/mnt/storage` > 85% → warning; > 95% → critical |
| `ram_in_use` | RAM > 90% в течение 5 мин |
| `cpu_usage` | CPU > 90% в течение 5 мин |
| `docker_container_state` | любой контейнер не running |
| `temperature` | thermal_zone > 85°C |

### Настройка Telegram для Netdata

```bash
# Монтируется через volume в /etc/netdata/health_alarm_notify.conf
SEND_TELEGRAM="YES"
TELEGRAM_BOT_TOKEN="ваш_токен_бота"
TELEGRAM_CHAT_ID="ваш_chat_id"
```

---

## 6. Файлы и ресурсы

| Файл | Назначение |
|---|---|
| `docker/compose/docker-compose.monitoring.yml` | Compose Stage 1 мониторинга |
| `docs/prompts/CODEX_MONITORING_PROMPT.md` | Промпт агента для развёртывания |
| `docs/13_MONITORING_RUNBOOK.md` | Runbook: ежедневные проверки и экстренные действия |

---
---

## 🇬🇧 English section / Английская секция

---

## 1. Context and Constraints

### Hardware Platform

| Parameter | Value |
|---|---|
| Device | NVIDIA Jetson Nano 4GB |
| Architecture | ARM64 (aarch64) |
| RAM | 4 GB (shared between CPU and GPU, no swap) |
| Storage | USB HDD at `/mnt/storage` |
| OS | Ubuntu 18.04 LTS (JetPack) |

### Current RAM Usage — Stage 1

| Service | Approximate RAM |
|---|---|
| Nextcloud (apache) | ~150–200 MB |
| nextcloud-db (PostgreSQL 16-alpine) | ~80–120 MB |
| nextcloud-redis | ~10–20 MB |
| immich-server | ~200–300 MB |
| immich-microservices | ~150–250 MB |
| immich-db (pgvecto-rs) | ~100–200 MB |
| immich-redis | ~10–20 MB |
| llm-gateway (FastAPI) | ~80–120 MB |
| **Stage 1 total** | **~780 MB – 1.23 GB** |
| OS + kernel + system processes | ~400–600 MB |
| **Total in use** | **~1.2 – 1.8 GB** |
| **Available** | **~2.2 – 2.8 GB** |

**Monitoring budget:** ~500 MB – 1 GB RAM without OOM risk.

### Critical Constraint

Jetson Nano has **no swap by default**. When RAM runs out, the kernel OOM-kills
processes. The monitoring stack must not exceed ~600–700 MB total. Adding a
heavy Zabbix + database stack on top of Stage 1 creates a real OOM risk for
production services.

---

## 2. Tool Analysis

### Comparison Table

| Tool | RAM | ARM64 | Complexity | Database | Recommendation |
|---|---|---|---|---|---|
| **Netdata** | 80–120 MB | First-class | Low | None (rolling buffer) | **RECOMMENDED — Stage 1** |
| **Uptime Kuma** | 50–70 MB | Yes | Low | SQLite (built-in) | **RECOMMENDED — Stage 1** |
| **Portainer CE** | 50–80 MB | Full | Low | None | Recommended (convenient) |
| Prometheus | 100–200 MB | Full | Medium | None (TSDB) | Stage 2 |
| Node Exporter | 5 MB | Full | Low | None | Stage 2 (with Prometheus) |
| cAdvisor | 30 MB | Yes | Low | None | Stage 2 (with Prometheus) |
| Grafana | 150–200 MB | Yes | Medium | None (built-in) | Stage 2 (with Prometheus) |
| VictoriaMetrics | 50–100 MB | Yes | Medium | None (TSDB) | Prometheus alternative |
| Alertmanager | 30–50 MB | Yes | Medium | None | Stage 2 |
| **Zabbix** | **300–800 MB** | Limited | High | **Required** | **NOT RECOMMENDED** |

### 2.1 Zabbix

Enterprise-grade monitoring platform with agents, templates, triggers, and
dashboards. Industry standard in corporate environments.

**Technical specs:**
- Zabbix Server: ~300–500 MB RAM
- Zabbix Database (PostgreSQL or MySQL): ~100–300 MB RAM additional
- Zabbix Agent: ~10 MB per monitored host
- ARM64: images available but less mature; occasional dependency issues on JetPack 18.04

**Issues for Jetson Nano:**
1. Requires a dedicated database for Zabbix — that is a third PostgreSQL
   instance (two already exist: Nextcloud and Immich).
2. Total Zabbix stack: ~450–900 MB RAM.
3. On a 4 GB Jetson with Stage 1 running, this creates real OOM risk.
4. Template, trigger, and agent configuration requires significant setup time.
5. Overkill for 8 containers in a home cloud.

**When Zabbix makes sense:** A separate LAN server (old PC) runs the Zabbix
server and database; only the lightweight Zabbix agent (~10 MB) is installed on
Jetson. In this case Jetson pays only 10 MB RAM for monitoring.

**Conclusion: not recommended as a monitoring server on Jetson.**

---

### 2.2 Prometheus + Node Exporter + cAdvisor

De-facto standard for metrics in modern cloud infrastructure. Pull model:
Prometheus scrapes exporters via HTTP.

**Technical specs:**
- Prometheus Server: ~100–200 MB RAM
- Node Exporter: ~5 MB (host metrics: CPU, RAM, disk, network)
- cAdvisor: ~30 MB (Docker container metrics)
- ARM64: full support for all three components
- No built-in dashboard — Grafana required

**Pros:** alert rules ecosystem (Alertmanager), Grafana integration, metric
retention (15 days default), large community, ready-made dashboards.

**Stage 1 cons:** Prometheus alone has no useful UI; combined with Grafana
total is ~280–430 MB RAM; scrape config setup takes time.

**Conclusion: recommended for Stage 2 together with Grafana.**

---

### 2.3 Grafana

Dashboard and visualization frontend for Prometheus, VictoriaMetrics, InfluxDB,
and other sources.

- RAM: ~150–200 MB
- ARM64: `grafana/grafana:latest` supports arm64
- Built-in alerting (Grafana Alerting)
- Default port: 3000

**Conclusion: recommended alongside Prometheus on Stage 2. On Stage 1 it is
redundant — Netdata already provides a full built-in UI.**

---

### 2.4 Netdata

All-in-one real-time monitoring, built specifically for SBCs (Raspberry Pi,
Jetson, Orange Pi). Built-in web UI, auto-discovery of services and Docker
containers.

- RAM: ~80–120 MB
- ARM64: first-class support (native packages and Docker image)
- No external database — rolling buffer in memory (~1 hour window by default)
- Long-term storage: optional via Prometheus remote_write or netdata-cloud
- Port: 19999

**What it monitors out-of-the-box:**
- CPU: overall, per-core, softirq, iowait
- RAM: used, cache, buffers, swapless warning
- Disk: I/O, latency, fill level for all mount points
- Network: throughput, packets, errors per interface
- Docker: state, CPU%, RAM%, I/O per container (via docker.sock)
- PostgreSQL: connections, latency, deadlocks
- Redis: memory, commands, hit rate
- Thermal zones on Jetson via `/sys/class/thermal`

**Conclusion: RECOMMENDED for Stage 1. Best choice for SBCs — minimal
configuration, maximum metrics out-of-the-box.**

---

### 2.5 Uptime Kuma

Simple self-hosted uptime monitor with a clean UI and notifications. Self-hosted
alternative to UptimeRobot. Monitors HTTP endpoints, TCP ports, DNS.

- RAM: ~50–70 MB
- ARM64: `louislam/uptime-kuma:latest` supports arm64
- Database: SQLite (built-in, no separate DBMS needed)
- Port: 3001 (HTTP, built-in authentication)
- Notifications: Telegram, Email (SMTP), Slack, Discord, Webhook, 90+ integrations

**For NAS_Jetson_Nano:** monitors Nextcloud (:8080), Immich (:2283), LLM Gateway
(:8090/health) with Telegram notification on failure.

**Conclusion: RECOMMENDED for Stage 1. Telegram alert in 5 minutes of setup.**

---

### 2.6 Portainer CE

Docker management UI for containers, images, networks, volumes, and stacks via
browser.

- RAM: ~50–80 MB
- ARM64: full support (`portainer/portainer-ce:latest`)
- Ports: 9000 (HTTP), 9443 (HTTPS)
- Features: container logs, real-time stats, compose stack editor,
  start/stop/restart via UI

**Conclusion: recommended as a convenience tool, not required.**

---

### 2.7 cAdvisor (standalone)

Google's Container Advisor — exports Docker container metrics in Prometheus
format.

- RAM: ~30 MB
- ARM64: supported (`gcr.io/cadvisor/cadvisor:latest`)
- Port: 8080 (conflicts with Nextcloud — use a different host port)

**Standalone:** provides a basic web UI with container stats.
**With Prometheus + Grafana:** full container metric dashboards.

**Conclusion: add in Stage 2 with Prometheus. On Stage 1, Netdata already
collects Docker metrics via docker.sock.**

---

### 2.8 VictoriaMetrics

High-performance, compact alternative to Prometheus. Compatible with Prometheus
API; accepts data from Node Exporter and cAdvisor.

- RAM: ~50–100 MB (significantly less than Prometheus at equivalent data volume)
- ARM64: supported
- Single-binary mode: one binary replaces Prometheus + Alertmanager
- Long-term retention without performance degradation

**Conclusion: strong Prometheus alternative for Stage 2. Consider if Prometheus
turns out to be too heavy on Jetson.**

---

## 3. Recommended Deployment Strategy

### Stage 1 — Minimal Monitoring (Now)

**Goal:** see system state, receive alerts, manage containers.

| Tool | RAM | Purpose |
|---|---|---|
| Netdata | ~100 MB | System monitoring + Docker stats + temperature |
| Uptime Kuma | ~60 MB | HTTP endpoint uptime + Telegram alerts |
| Portainer CE | ~60 MB | Docker management UI (optional) |
| **Total** | **~220 MB** | |

Compose file: `docker/compose/docker-compose.monitoring.yml`

Access ports:
- Netdata: `http://192.168.0.50:19999`
- Uptime Kuma: `http://192.168.0.50:3001`
- Portainer: `http://192.168.0.50:9000`

### Stage 2 — Full Observability (Future)

**Goal:** long-term metric storage, intelligent alerts, dashboards.

| Tool | RAM | Purpose |
|---|---|---|
| Netdata | ~100 MB | System monitoring (keep) |
| Prometheus | ~150 MB | TSDB for long-term metrics |
| Node Exporter | ~5 MB | Host metrics for Prometheus |
| cAdvisor | ~30 MB | Docker metrics for Prometheus |
| Grafana | ~180 MB | Dashboards |
| Alertmanager | ~40 MB | Intelligent alerts with grouping |
| **Stage 2 adds** | **~405–505 MB** | |

**Alternative:** replace Prometheus + Alertmanager with VictoriaMetrics
single-binary (~100 MB instead of ~190 MB).

### Why Zabbix Does Not Fit Jetson

1. **RAM:** Zabbix server + database = ~400–800 MB. This consumes the entire
   monitoring budget plus part of the production service headroom.
2. **Third PostgreSQL:** Stage 1 already runs two PostgreSQL instances
   (Nextcloud + Immich). Adding a third solely for Zabbix is wasteful.
3. **Complexity:** Configuring templates, triggers, and items in Zabbix takes
   significant time for 8 containers in a home stack.
4. **OOM risk:** Without swap on Jetson Nano, the OOM killer targets production
   containers. A heavy monitoring stack increases this risk.

**The only valid Zabbix scenario:** a dedicated Zabbix server on an old PC in
the LAN, with only the Zabbix agent (~10 MB RAM) on Jetson.

---

## 4. Metrics to Monitor in the NAS_Jetson_Nano Context

### Critical Metrics

| Metric | Source | Alert Threshold |
|---|---|---|
| RAM utilization % | Netdata → system.ram | > 90% for 2+ min |
| Disk usage `/mnt/storage` % | Netdata → disk_space | > 85% |
| Disk usage `/` % | Netdata → disk_space | > 90% |
| Container health: any stopped | Netdata → docker / Portainer | Immediately |
| CPU load (1min avg) | Netdata → system.load | > 3.0 (75% × 4 cores) |

### HTTP Uptime Metrics (Uptime Kuma)

| Service | URL | Expected Status |
|---|---|---|
| Nextcloud | `http://192.168.0.50:8080` | HTTP 200 |
| Immich | `http://192.168.0.50:2283` | HTTP 200 |
| LLM Gateway | `http://192.168.0.50:8090/health` | HTTP 200 |

### Additional Metrics (Netdata automatic)

- **PostgreSQL:** active connections, transactions/sec, latency, deadlocks
- **Redis:** used_memory, connected_clients, hit rate
- **Jetson temperature:** thermal_zone0 (CPU), thermal_zone1 (GPU) — alert at > 85°C
- **Network:** bytes in/out per interface, errors, drops

---

## 5. Alerts — What to Configure

### Uptime Kuma (HTTP monitoring)

| Alert | Condition | Action |
|---|---|---|
| Nextcloud unavailable | HTTP != 200 for > 2 min | Telegram notification |
| Immich unavailable | HTTP != 200 for > 2 min | Telegram notification |
| LLM Gateway unavailable | HTTP != 200 for > 2 min | Telegram notification |

### Netdata (system alerts)

Alert config files: `/etc/netdata/health.d/` (inside the container).

| Alert | Condition |
|---|---|
| `disk_space_usage` | `/mnt/storage` > 85% → warning; > 95% → critical |
| `ram_in_use` | RAM > 90% for 5 min |
| `cpu_usage` | CPU > 90% for 5 min |
| `docker_container_state` | any container not running |
| `temperature` | thermal_zone > 85°C |

### Telegram Setup for Netdata

```bash
# Mount via volume into /etc/netdata/health_alarm_notify.conf
SEND_TELEGRAM="YES"
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"
```

---

## 6. Files and Resources

| File | Purpose |
|---|---|
| `docker/compose/docker-compose.monitoring.yml` | Stage 1 monitoring compose |
| `docs/prompts/CODEX_MONITORING_PROMPT.md` | Agent prompt for deployment |
| `docs/13_MONITORING_RUNBOOK.md` | Runbook: daily checks and emergency actions |
