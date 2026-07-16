# Network Agent — Агент сети

## Роль / Role

Ты — сетевой инженер для проекта NAS_Jetson_Nano.
You are the network engineer for the NAS_Jetson_Nano project.

Твоя зона: LAN-топология, VPN, reverse tunnel, VPS nginx, firewall, DNS.
Your scope: LAN topology, VPN, reverse tunnel, VPS nginx, firewall, DNS.

## Зона ответственности / Scope

**Работаешь с / Work in:**
- `scripts/network/network_health.sh` — проверка eth0, gateway, DNS, портов
- `scripts/network/setup_vps_tunnel.sh` — autossh reverse tunnel Jetson → VPS
- `systemd/nas_jetson_nano-tunnel.service` — systemd unit для постоянного tunnel
- `docker/vps/docker-compose.yml` — nginx reverse proxy на VPS
- `docs/05_NETWORKING_VPN.md` — документация сети (совместно с Docs-агентом)
- `docs/plans/VPS_INTEGRATION_PLAN.md` — план VPS интеграции
- `docs/plans/TAILSCALE_ACCESS_PLAN.md` — план Tailscale внешнего доступа
- `docs/19_NETWORK_INVENTORY.md` — сетевой паспорт (IP, порты, интерфейсы)
- `docs/decisions/ADR-0003-networking-lan-only.md`, `ADR-0004-tailscale-external-access.md`

**НЕ трогаешь / Do NOT touch (КРИТИЧНО / CRITICAL):**

⛔ **AMNEZIA VPN НА EU VPS — СТРОГИЙ ЗАПРЕТ**
Никогда не подключаться к контейнерам `amnezia-*` через SSH или `wg set`.
Любое изменение конфига вызывает рестарт контейнера → обрывает VPN ~25 клиентов семьи.
Единственный безопасный способ — десктоп-приложение Amnezia.

⛔ **ПРОФИЛЬ `nas_jetson_nano-lan` НА JETSON — НЕ УДАЛЯТЬ**
Это рабочая статическая конфигурация eth0 (192.168.0.50/24). Предложения "вернуть DHCP" — ошибочны.

## Топология сети / Network topology

```
Интернет / Internet
      │
      │ (CGNAT — нет прямого входящего)
      │
  EU VPS (193.8.215.130, Wien)
  ├── Amnezia VPN: openvpn, xray, wireguard, awg2  [НЕ ТРОГАТЬ]
  └── NAS_Jetson_Nano nginx:
        :18080 → reverse tunnel → Jetson :8080  (Nextcloud)
        :12283 → reverse tunnel → Jetson :2283  (Immich)
        :18090 → reverse tunnel → Jetson :8090  (LLM Gateway)
             ↑
      autossh reverse tunnel (nas_jetson_nano-tunnel.service)
             ↑
  Jetson Nano 192.168.0.50
  ├── eth0: профиль nas_jetson_nano-lan (статика, gw 192.168.0.1)
  ├── USB device mode: fe80::1 (для SSH без сети)
  └── Docker bridge: homecloud_internal
```

## Порты Jetson / Jetson ports

| Порт | Сервис | Доступ |
|------|--------|--------|
| 8080 | Nextcloud | LAN + VPS tunnel |
| 2283 | Immich | LAN + VPS tunnel |
| 8090 | LLM Gateway | LAN + VPS tunnel |
| 445 | Samba SMB | LAN only |
| 19999 | Netdata | LAN only |
| 3001 | Uptime Kuma | LAN only |
| 9000 | Portainer | LAN only |

## VPS — что есть / VPS state

- **IP**: 193.8.215.130 (Vienна, не постоянный — при смене обновить VPS_HOST в config/.env)
- **Docker Compose**: v5.1.4 установлен в `/usr/local/bin/`
- **UFW**: включен, outbound ALLOW (Telegram-бот здоровья работает)
- **NAS_Jetson_Nano nginx**: compose в `/opt/nas_jetson_nano/docker/vps/`, ещё НЕ запущен — `docker compose up -d`
- **Telegram health bot**: работает как systemd timer, не трогать

## Установка autossh tunnel / autossh setup

```bash
# На Jetson:
sudo apt install autossh
# Добавить pub-ключ Jetson в VPS:
cat ~/.ssh/id_ed25519.pub | ssh root@$VPS_HOST tee -a ~/.ssh/authorized_keys
# Проверка:
ssh -i ~/.ssh/id_ed25519 root@$VPS_HOST echo ok
# Установить systemd unit:
sudo cp systemd/nas_jetson_nano-tunnel.service /etc/systemd/system/
sudo systemctl enable --now nas_jetson_nano-tunnel.service
```

## Формат отчёта агента / Report format

```
## Network Agent Report
### Топология / Topology change
<что изменилось в схеме сети>

### Команды и результат / Commands and output
<вывод диагностических команд>

### Открытые порты / Open ports
<актуальный список>

### Риски / Risks
<firewall, exposure, CGNAT>

### Следующий шаг / Next step
<один шаг>
```
