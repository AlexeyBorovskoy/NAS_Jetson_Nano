# Runtime: сервисы, процессы, Docker, порты, старт / Services, processes, Docker, ports, startup

**Дата замера / Measured:** 2026-08-30, устройство `admin@192.168.0.50`, read-only, без sudo.

## 1. Docker-контейнеры / Docker containers

`docker ps -a` → **13 контейнеров `homecloud_*`**, все `Up`, `RestartCount=0`, `OOMKilled=false` у всех. 12 из 13 — `healthy`; **`homecloud_portainer` не имеет healthcheck вовсе** (не «нездоров» — просто не проверяется, единственное исключение из общего паттерна).

Restart policy: `always` у всех 13 (проверено `docker inspect`).

## 2. Систем-сервисы (устройство, реальные имена) / Systemd services (device, real names)

`systemctl --type=service --state=running` — 36 юнитов, из проектных: `nasa-tunnel.service`, `nasa-usb-monitor.service`, `beszel-agent.service` (Go-бинарник, не контейнер).

Enabled unit-files (проектные, 8): `jetson-nas-health.timer`, `nasa-backup.timer`, `nasa-daily-report-telegram.timer`, `nasa-hdd2tb-selftest.timer`, `nasa-jms583-health.timer`, `nasa-talk-alert.timer`, `nasa-usb-watchdog.timer`, `nasa-usb-preboot.service`.

## 3. Слушающие порты / Listening ports

`ss -lntup`, внешне значимые (не loopback):

| Порт | Сервис |
|---|---|
| 22 | SSH |
| 111 | rpcbind (штатно ядра, не проект) |
| 445, udp 137/138 | Samba |
| 2283 | Immich |
| 3001 | Uptime Kuma |
| 8080 | Nextcloud |
| 8090 | LLM Gateway |
| 8099 | nasa-api |
| 9000/9443 | Portainer |
| 19999 | Netdata |
| 45876 | Beszel Agent |

Loopback/bridge-only: `62322`/`62323` (autossh control), `172.17.0.1:11435` — обратный туннель к Ollama на рабочей станции (подтверждает работающую схему `GatewayPorts clientspecified`).

**Соответствие правилу №4 CLAUDE.md**: наружу в интернет с Jetson ничего не публикуется напрямую — весь список выше LAN-only, внешний доступ идёт только через VPS/VPN.

## 4. Startup chain / Цепочка старта

```
boot → systemd → docker.service (enabled)
              → docker-контейнеры (restart: always в compose)
              → nasa-tunnel.service (After=docker.service, Wants=network-online.target)
              → nasa-usb-preboot.service / udev(sda1) → nasa-ssd-recovery.service
                    → mount → storage_preflight.sh → docker compose up
```

Критичные сервисы явно объявляют `After=docker.service`+`network-online.target` — явных гонок в конфигурации не найдено. `nasa-talk-alert.timer`: `OnBootSec=10min`, `OnUnitActiveSec=15min`, `Persistent=true` — догоняет пропущенные срабатывания после простоя.

🔴 **Не перепроверено в этом заходе**: реальный тест «выдернуть SSD / перезагрузить и посмотреть» — деструктивный, не входил в read-only периметр (уже отмечено как несделанное в CLAUDE.md).

## 5. Docker network / privileged / mounts

| Контейнер | Privileged | NetworkMode | docker.sock | Обоснование |
|---|---|---|---|---|
| `homecloud_samba` | false | **host** | нет | NetBIOS/автообнаружение SMB не проходит через Docker NAT |
| `homecloud_portainer` | false | bridge | да, **ro** | UI управления Docker |
| `homecloud_nasa_api` | false | bridge | да, **ro** | читает статус контейнеров/логи для API |
| `homecloud_netdata` | false | bridge | да, **ro** | `CAP_SYS_ADMIN`/`CAP_SYS_PTRACE`, `/proc`,`/sys` (ro) — типовой набор для системного мониторинга |
| `homecloud_nextcloud` | false | bridge | нет | прямой доступ к `/mnt/hdd2tb` (external storage) |
| `docker-compose.coturn.yml` (не развёрнут) | false | **host** | нет | широкий диапазон UDP для WebRTC — обоснованно для TURN, но контейнер фактически не поднят на VPS |

Ни один контейнер не `Privileged=true`, смонтированных `/dev` нет ни у одного. Три контейнера держат Docker-сокет (`ro`) — стандартный принятый риск для UI/мониторинга, зафиксирован, не новая находка.

## 6. Ресурсы в моменте замера / Resource snapshot

- RAM: 2.0–2.1 ГБ занято из 3.9 ГБ, доступно 1.4–1.5 ГБ.
- ZRAM: 4×495.5М (итого 1.98Г), lzo, ~485М данных → ~194М на диске (≈2.5×).
- `load average`: 2.52/1.56/1.42 (4 ядра) — умеренная нагрузка.
- Температуры: CPU 44–47.5°C, GPU 43–44.5°C, PMIC 50°C — далеко от порога троттлинга Tegra X1 (~90-97°C). **Throttling не обнаружен.**
- Power mode: **MAXN** (`nvpmodel -q`) — максимальная производительность, без power-cap.
- `GR3D_FREQ` (загрузка GPU) — **0% на всех замерах** (15 точек, `tegrastats` за 15с). GPU полностью простаивает — см. `AI_STACK.md`.

## 7. Диски / Storage utilization

| Раздел | Размер | Занято | Свободно |
|---|---|---|---|
| `/` (SD-карта) | 60G | 24G (41%) | 34G |
| `/mnt/storage` (SSD) | 229G | 13G (6%) | 204G |
| `/mnt/hdd2tb` (HDD) | 1.9T | 1.4T (76%) | 462G |

`/mnt/storage/immich` = 12G из 13G занятых на SSD — основной потребитель.

🟠 **Находка**: `/mnt/hdd2tb/$RECYCLE.BIN` = **27 ГБ** (частичный обход, полный `du` по HDD не завершился за 90с из-за медленного NTFS-3g/FUSE на 1.4 ТБ) — похоже на корзину Windows, перенесённую вместе с данными и никогда не очищавшуюся. Кандидат на ручную проверку, вне read-only периметра этого аудита.

`/var/log` = 142М (`journal` 81М из лимита 200М — риска нет; `nasa-monitor` 61М).
