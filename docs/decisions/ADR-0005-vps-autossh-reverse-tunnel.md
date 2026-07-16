# ADR-0005: VPS + autossh reverse SSH tunnel для внешнего доступа
# ADR-0005: VPS + autossh Reverse SSH Tunnel for External Access

## Статус / Status

🇷🇺 **Реализовано** (2026-06-21). / 🇬🇧 **Implemented** (2026-06-21).

## Контекст / Context

🇷🇺 Jetson Nano находится за CGNAT — прямой port forwarding невозможен. Amnezia VPN на VPS не трогать (~25 клиентов). Требования: CGNAT-proof, без Amnezia, автостарт, SSH-управление Jetson с VPS.
🇬🇧 Jetson Nano is behind CGNAT — direct port forwarding is impossible. Amnezia VPN on VPS must not be touched (~25 clients). Requirements: CGNAT-proof, no Amnezia impact, autostart, SSH management of Jetson from VPS.

## Рассмотренные варианты / Options considered

| Вариант / Option | CGNAT | Без Amnezia / No Amnezia | Сложность / Complexity | Решение / Decision |
|---|---|---|---|---|
| WireGuard через VPS / via VPS | ✗ (DKMS, L4T 4.9) | да / yes | высокая / high | ❌ откачено / rolled back (ADR-0003) |
| Tailscale | ✓ DERP-relay | да / yes | низкая / low | ❌ третья сторона / third party |
| ngrok / cloudflared | ✓ | да / yes | очень низкая / very low | ❌ чужой сервер / foreign server |
| **Reverse SSH + autossh** | ✓ | да / yes | средняя / medium | ✅ **выбрано / chosen** |

## Решение / Decision

🇷🇺 Jetson инициирует исходящее SSH-соединение к VPS. CGNAT не блокирует исходящие. VPS sshd держит reverse-порты на `127.0.0.1`. nginx на VPS проксирует публичные запросы на эти порты.
🇬🇧 Jetson initiates an outgoing SSH connection to VPS. CGNAT doesn't block outgoing connections. VPS sshd holds reverse ports at `127.0.0.1`. nginx on VPS proxies public requests to these ports.

```
Internet → VPS:8080 → nginx → 127.0.0.1:18080 → SSH tunnel → Jetson:8080
Internet → VPS:2283 → nginx → 127.0.0.1:12283 → SSH tunnel → Jetson:2283
Internet → VPS:8090 → nginx → 127.0.0.1:18090 → SSH tunnel → Jetson:8090
VPS → ssh -p 10022 admin@127.0.0.1 → SSH tunnel → Jetson:22
```

## Реализация / Implementation

**На Jetson / On Jetson:**

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

# /opt/nas_jetson_nano/config/.env
VPS_HOST=193.8.215.130
VPS_USER=root
VPS_SSH_KEY=/home/admin/.ssh/id_ed25519

# systemd
sudo cp systemd/nas_jetson_nano-tunnel.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now nas_jetson_nano-tunnel.service
```

**nas_jetson_nano-tunnel.service:**
```ini
[Service]
ExecStart=/usr/bin/autossh -N \
    -R 18080:localhost:8080 \
    -R 12283:localhost:2283 \
    -R 18090:localhost:8090 \
    -R 10022:localhost:22 \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -o StrictHostKeyChecking=accept-new \
    -i "${VPS_SSH_KEY}" \
    "${VPS_USER}@${VPS_HOST}"
Restart=always
RestartSec=10
```

> 🇷🇺 **Важно:** nginx на VPS должен работать в `network_mode: host` — иначе `127.0.0.1` внутри контейнера — это loopback контейнера, а не хоста.
>
> 🇬🇧 **Important:** nginx on VPS must run in `network_mode: host` — otherwise `127.0.0.1` inside the container is the container's loopback, not the host where the SSH tunnel listens.

## Последствия / Consequences

- 🇷🇺 VPS публично открыт на портах 8080/2283/8090 (HTTP) и 8443/2443/9443 (HTTPS, self-signed). / 🇬🇧 VPS publicly open on ports 8080/2283/8090 (HTTP) and 8443/2443/9443 (HTTPS, self-signed).
- 🇷🇺 При изменении IP VPS: обновить `VPS_HOST` в `.env` на Jetson, перезапустить `nas_jetson_nano-tunnel.service`. / 🇬🇧 If VPS IP changes: update `VPS_HOST` in `.env` on Jetson, restart `nas_jetson_nano-tunnel.service`.
- 🇷🇺 Amnezia VPN не затронут (работает на своих портах). / 🇬🇧 Amnezia VPN not affected (runs on its own ports).
- 🇷🇺 Управление Jetson из любой точки мира: `ssh -p 10022 admin@127.0.0.1` с VPS. / 🇬🇧 Jetson management from anywhere: `ssh -p 10022 admin@127.0.0.1` from VPS.
