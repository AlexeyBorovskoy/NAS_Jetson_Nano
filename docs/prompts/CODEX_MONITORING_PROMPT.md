# CODEX_MONITORING_PROMPT

Ты агент Codex в проекте NAS_Jetson_Nano (Jetson Nano, ARM64, 4 GB RAM, без swap).
Работай малыми шагами. Не используй реальные секреты. Перед destructive-командами
запроси подтверждение. Не открывай сервисы наружу. После каждого шага дай
проверку и rollback.

## Цель шага

Развернуть мониторинг-стек Stage 1 по `docker/compose/docker-compose.monitoring.yml`:

- **Netdata** — системный мониторинг, Docker stats, температура (порт 19999)
- **Uptime Kuma** — HTTP uptime + Telegram-уведомления (порт 3001)
- **Portainer** — Docker management UI (порт 9000)

Полное описание выбора инструментов: `docs/17_MONITORING_OBSERVABILITY.md`.

## Предусловия

1. Stage 1 запущен и стабилен:

```bash
docker compose -f docker/compose/docker-compose.stage1.yml ps
# Все сервисы: Up (healthy или running)
```

2. Сеть `homecloud_internal` существует:

```bash
docker network ls | grep homecloud_internal
```

3. Docker socket доступен:

```bash
ls -la /var/run/docker.sock
```

4. Свободно не менее 250 MB RAM перед запуском мониторинга:

```bash
free -h
```

5. Файл конфигурации `config/.env` заполнен (переменная `TZ` обязательна).

## Команды развёртывания

### Шаг 1. Проверить compose-файл

```bash
cd /path/to/NAS_Jetson_Nano
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env config
```

Убедиться, что нет ошибок парсинга и все переменные разрешены.

### Шаг 2. Запустить мониторинг-стек

```bash
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env up -d
```

### Шаг 3. Проверить запуск контейнеров

```bash
docker compose -f docker/compose/docker-compose.monitoring.yml ps
```

Ожидаемый результат:

```
NAME                      STATUS
homecloud_netdata         Up
homecloud_uptime_kuma     Up
homecloud_portainer       Up
```

### Шаг 4. Проверить логи на ошибки

```bash
docker logs homecloud_netdata    --tail=30
docker logs homecloud_uptime_kuma --tail=30
docker logs homecloud_portainer  --tail=30
```

### Шаг 5. Проверить RAM после запуска

```bash
docker stats --no-stream
free -h
```

Мониторинг-стек в сумме не должен превышать ~300 MB.

## Проверка результата

### Netdata

Открыть в браузере: `http://<jetson-ip>:19999`

Убедиться:
- Отображаются графики CPU, RAM, диска
- Секция **Docker** показывает контейнеры Stage 1
- Точка монтирования `/mnt/storage` отображается в Disk Space

### Uptime Kuma

Открыть в браузере: `http://<jetson-ip>:3001`

При первом входе создать учётную запись администратора.

Добавить мониторы:

| Имя | Тип | URL | Интервал |
|---|---|---|---|
| Nextcloud | HTTP(s) | `http://192.168.0.50:8080` | 60 сек |
| Immich | HTTP(s) | `http://192.168.0.50:2283` | 60 сек |
| LLM Gateway | HTTP(s) | `http://192.168.0.50:8090/health` | 60 сек |

Настроить уведомления (Settings → Notifications):
- Тип: Telegram
- Bot Token: получить через `@BotFather` в Telegram
- Chat ID: получить через `@userinfobot`

### Portainer

Открыть в браузере: `http://<jetson-ip>:9000`

При первом входе создать учётную запись администратора.
Выбрать: **Get Started → local** (Docker Socket).

Убедиться, что все контейнеры Stage 1 + мониторинга видны в списке.

## Настройка Telegram-уведомлений в Netdata

```bash
# Войти в контейнер Netdata
docker exec -it homecloud_netdata bash

# Отредактировать конфигурацию уведомлений
/etc/netdata/edit-config health_alarm_notify.conf
```

Найти и заполнить:

```bash
SEND_TELEGRAM="YES"
TELEGRAM_BOT_TOKEN="your_bot_token_here"
TELEGRAM_CHAT_ID="your_chat_id_here"
```

Проверить (тест уведомления):

```bash
/usr/libexec/netdata/plugins.d/alarm-notify.sh test telegram
```

## Rollback

Если мониторинг-стек вызывает OOM или нестабильность Stage 1:

```bash
# Остановить мониторинг-стек
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env down

# Проверить, что Stage 1 восстановился
docker compose -f docker/compose/docker-compose.stage1.yml ps
free -h
```

Данные сохраняются в именованных volumes. После повторного `up -d` история
Uptime Kuma и настройки Portainer восстановятся.

Для полного удаления volumes (сброс данных мониторинга):

```bash
# ВНИМАНИЕ: удаляет всю историю мониторинга и настройки
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env down -v
```

---

---

# CODEX_MONITORING_PROMPT (English)

You are a Codex agent in the NAS_Jetson_Nano project (Jetson Nano, ARM64,
4 GB RAM, no swap). Work in small steps. Do not use real secrets. Ask for
confirmation before destructive commands. Do not expose services to the internet.
After each step provide a verification check and a rollback procedure.

## Goal

Deploy the Stage 1 monitoring stack from
`docker/compose/docker-compose.monitoring.yml`:

- **Netdata** — system monitoring, Docker stats, temperature (port 19999)
- **Uptime Kuma** — HTTP uptime + Telegram notifications (port 3001)
- **Portainer** — Docker management UI (port 9000)

Full tool selection rationale: `docs/17_MONITORING_OBSERVABILITY.md`.

## Prerequisites

1. Stage 1 is running and stable:

```bash
docker compose -f docker/compose/docker-compose.stage1.yml ps
# All services: Up (healthy or running)
```

2. The `homecloud_internal` network exists:

```bash
docker network ls | grep homecloud_internal
```

3. Docker socket is accessible:

```bash
ls -la /var/run/docker.sock
```

4. At least 250 MB RAM is free before starting the monitoring stack:

```bash
free -h
```

5. `config/.env` is filled in (`TZ` variable is required).

## Deployment Commands

### Step 1. Validate the compose file

```bash
cd /path/to/NAS_Jetson_Nano
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env config
```

Ensure no parse errors and all variables resolve.

### Step 2. Start the monitoring stack

```bash
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env up -d
```

### Step 3. Check container startup

```bash
docker compose -f docker/compose/docker-compose.monitoring.yml ps
```

Expected output:

```
NAME                      STATUS
homecloud_netdata         Up
homecloud_uptime_kuma     Up
homecloud_portainer       Up
```

### Step 4. Check logs for errors

```bash
docker logs homecloud_netdata    --tail=30
docker logs homecloud_uptime_kuma --tail=30
docker logs homecloud_portainer  --tail=30
```

### Step 5. Check RAM after startup

```bash
docker stats --no-stream
free -h
```

The monitoring stack combined should not exceed ~300 MB RAM.

## Verification

### Netdata

Open in browser: `http://<jetson-ip>:19999`

Verify:
- CPU, RAM, disk graphs are displayed
- **Docker** section shows Stage 1 containers
- `/mnt/storage` mount point appears in Disk Space

### Uptime Kuma

Open in browser: `http://<jetson-ip>:3001`

On first login, create an admin account.

Add monitors:

| Name | Type | URL | Interval |
|---|---|---|---|
| Nextcloud | HTTP(s) | `http://192.168.0.50:8080` | 60 sec |
| Immich | HTTP(s) | `http://192.168.0.50:2283` | 60 sec |
| LLM Gateway | HTTP(s) | `http://192.168.0.50:8090/health` | 60 sec |

Configure notifications (Settings → Notifications):
- Type: Telegram
- Bot Token: obtain via `@BotFather` in Telegram
- Chat ID: obtain via `@userinfobot`

### Portainer

Open in browser: `http://<jetson-ip>:9000`

On first login, create an admin account.
Select: **Get Started → local** (Docker Socket).

Verify all Stage 1 + monitoring containers are visible.

## Telegram Alert Setup in Netdata

```bash
# Enter the Netdata container
docker exec -it homecloud_netdata bash

# Edit notification config
/etc/netdata/edit-config health_alarm_notify.conf
```

Find and fill in:

```bash
SEND_TELEGRAM="YES"
TELEGRAM_BOT_TOKEN="your_bot_token_here"
TELEGRAM_CHAT_ID="your_chat_id_here"
```

Test notification:

```bash
/usr/libexec/netdata/plugins.d/alarm-notify.sh test telegram
```

## Rollback

If the monitoring stack causes OOM or destabilises Stage 1:

```bash
# Stop the monitoring stack
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env down

# Verify Stage 1 has recovered
docker compose -f docker/compose/docker-compose.stage1.yml ps
free -h
```

Data is stored in named volumes. After re-running `up -d`, Uptime Kuma history
and Portainer settings are restored.

To fully remove volumes (reset all monitoring data):

```bash
# WARNING: deletes all monitoring history and settings
docker compose -f docker/compose/docker-compose.monitoring.yml \
               --env-file config/.env down -v
```
