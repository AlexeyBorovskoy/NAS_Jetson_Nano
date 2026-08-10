# План: интеграция VPS в NAS_Jetson_Nano / VPS Integration Plan

> 🇷🇺 Завершено 2026-06-21. Реализован VPS reverse SSH tunnel (ADR-0005).
> 🇬🇧 Completed 2026-06-21. VPS reverse SSH tunnel implemented (ADR-0005).

**Статус / Status:** ✅ **Завершено / Completed (2026-06-21)**  
**VPS:** 95.163.176.103 (hostname: borovskoy-new.ptr.network)  
**Расположение:** Вена, Австрия (AEZA GROUP)  
**Важно:** IP-адрес VPS может измениться — при смене обновить `VPS_HOST` в `/opt/nas_jetson_nano/config/.env` на Jetson и перезапустить `nas_jetson_nano-tunnel.service`.

Архитектурное решение: [docs/decisions/ADR-0005-vps-autossh-reverse-tunnel.md](../decisions/ADR-0005-vps-autossh-reverse-tunnel.md)

---

## Что работает на VPS (обновлено 2026-06-23)

- `nas_jetson_nano_nginx` контейнер: `network_mode: host`, порты 8080/2283/8090 публичные
- Nextcloud: `http://95.163.176.103:8080/status.php` → HTTP 200 ✅
- Immich: `http://95.163.176.103:2283/` → HTTP 200 ✅
- LLM Gateway: `http://95.163.176.103:8090/health` → HTTP 200 ✅
- SSH управление Jetson: `ssh -p 10022 admin@127.0.0.1` с VPS ✅

Если Nextcloud снова вернёт 502/503, сначала проверять upstream container и
storage preflight на Jetson; tunnel/nginx уже подтверждены рабочими.

**Критичный параметр nginx:** `network_mode: host` обязателен.
В bridge-режиме `127.0.0.1:18080` — это loopback контейнера, а не хоста,
и proxy_pass до туннеля не работает.

---

## Что уже есть на VPS (история, 2026-06-20)

- Ubuntu 24.04.4 LTS, 1 vCPU (AMD Ryzen 9 7950X3D), 2GB RAM, 30GB диск
- Docker 29.1.3 + Docker Compose v5.1.4 (установлен)
- 4 контейнера Amnezia VPN (НЕ ТРОГАТЬ): amnezia-openvpn, amnezia-xray, amnezia-wireguard, amnezia-awg2
- UFW активен (настроен 2026-06-20)
- Директория `/opt/nas_jetson_nano/` создана
- Nginx конфиги в `/opt/nas_jetson_nano/nginx/conf.d/`
- Docker Compose для nginx: `/opt/nas_jetson_nano/docker-compose.yml`

## ⚠️ Что НЕ делать

> Amnezia VPN-контейнеры в `/opt/amnezia/` — не трогать, не рестартовать,
> не менять их конфиги. Они обслуживают семейный VPN ~25 клиентов.
> Любое вмешательство = потеря интернета у всех клиентов.
> Подробнее: ADR-0003.

---

## Архитектура: Reverse SSH Tunnel

```
Телефон/браузер
    |
    v (internet)
VPS: 95.163.176.103
    |  nginx :8080 → 127.0.0.1:18080
    |  nginx :2283 → 127.0.0.1:12283
    |  nginx :8090 → 127.0.0.1:18090
    |
    | (SSH tunnel, инициирован Jetson → пробивает CGNAT)
    v
Jetson Nano (192.168.0.50, LAN)
    |  :8080 Nextcloud
    |  :2283 Immich
    |  :8090 LLM Gateway
```

Jetson инициирует исходящее SSH-соединение к VPS (CGNAT не блокирует исходящие).
VPS получает соединение и форвардит через nginx.

---

## Этапы настройки

### Шаг 1: На этом Windows-хосте — добавить SSH-ключ Jetson в VPS (после настройки Jetson)

Когда Jetson будет настроен:
```bash
# Получить публичный ключ Jetson
ssh admin@192.168.0.50 "cat ~/.ssh/id_ed25519.pub"

# Добавить в VPS authorized_keys
echo "JETSON_PUB_KEY" >> /root/.ssh/authorized_keys   # на VPS
```

### Шаг 2: На Jetson — установить autossh

```bash
sudo apt install -y autossh
```

### Шаг 3: На Jetson — запустить туннель (тест)

```bash
VPS_HOST="95.163.176.103"   # обновить если IP изменился
autossh -N \
  -R 18080:localhost:8080 \
  -R 12283:localhost:2283 \
  -R 18090:localhost:8090 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  root@${VPS_HOST}
```

### Шаг 4: На VPS — запустить nginx

```bash
cd /opt/nas_jetson_nano
docker compose up -d
```

### Шаг 5: Проверка

С телефона (мобильный интернет, не Wi-Fi):
```
http://95.163.176.103:8080   → Nextcloud
http://95.163.176.103:2283   → Immich
http://95.163.176.103:8090   → LLM Gateway
```

### Шаг 6: На Jetson — systemd-сервис для автозапуска туннеля

```ini
# /etc/systemd/system/nas_jetson_nano-tunnel.service
[Unit]
Description=NAS_Jetson_Nano reverse SSH tunnel to VPS
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=admin
ExecStart=/usr/bin/autossh -N \
  -R 18080:localhost:8080 \
  -R 12283:localhost:2283 \
  -R 18090:localhost:8090 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  root@VPS_HOST
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nas_jetson_nano-tunnel.service
sudo systemctl status nas_jetson_nano-tunnel.service
```

---

## Другие возможности VPS

### Offsite restic backup (рекомендовано Stage 1)

Хранить restic-репозиторий на VPS:
```bash
# В config/.env
RESTIC_REPOSITORY="sftp:root@95.163.176.103:/opt/nas_jetson_nano/backups/restic-repo"
```

Плюсы: 25GB свободно, offsite (VPS в другой стране), SFTP встроен.

### Мониторинг-агрегатор (Stage 2)

Netdata на Jetson → Netdata Cloud или Netdata parent на VPS.

---

## UFW на VPS (настроено 2026-06-20)

| Порт | Протокол | Назначение |
|------|----------|-----------|
| 22 | TCP | SSH |
| 443 | TCP | Amnezia xray |
| 36571 | TCP | Amnezia OpenVPN |
| 37238 | UDP | Amnezia WireGuard |
| 40568 | UDP | Amnezia AWG2 |
| 8080 | TCP | NAS_Jetson_Nano reverse-tunnel Nextcloud |
| 2283 | TCP | NAS_Jetson_Nano reverse-tunnel Immich |
| 8090 | TCP | NAS_Jetson_Nano reverse-tunnel LLM Gateway |
| 9443 | TCP | Portainer HTTPS (резерв) |

---

## Обновление конфига при смене IP VPS

VPS IP может меняться. При смене:
1. Обновить `VPS_HOST` в `config/.env` на Jetson
2. Обновить `nas_jetson_nano-tunnel.service` на Jetson (`systemctl daemon-reload && systemctl restart nas_jetson_nano-tunnel`)
3. Обновить SSH config на Windows-хосте если нужно
4. Проверить что Amnezia клиенты на телефонах переключились автоматически (обычно да)

---

## / VPS Integration Plan (English)

**Status:** Implemented (2026-06-21), Nextcloud recovered after 2026-06-23 USB incident
**VPS:** 95.163.176.103, Vienna Austria (AEZA GROUP) — IP may change  

### Architecture: Reverse SSH Tunnel

Jetson Nano initiates an outbound SSH connection to the VPS, creating reverse port
forwards. nginx on the VPS listens on public ports and proxies to the tunnel endpoints.
This bypasses CGNAT without requiring Tailscale or any inbound connectivity to Jetson.

### ⚠️ Do NOT touch Amnezia containers on VPS

`/opt/amnezia/` — 4 containers serving family VPN (~25 clients). See ADR-0003.

### VPS resources available for NAS_Jetson_Nano

- RAM: ~1.5 GB free (total 2 GB)
- Disk: ~25 GB free (total 30 GB)
- Docker Compose v5.1.4 installed
- UFW configured and active
- `/opt/nas_jetson_nano/` directory created with nginx configs and compose file
