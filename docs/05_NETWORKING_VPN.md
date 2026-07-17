# 05. Сеть и VPN / Networking & VPN

## 1. LAN-схема / LAN layout

```text
Домашний роутер / Home router: TP-Link EC220-G5
├── 192.168.0.1       роутер / router (gateway/admin UI)
├── 192.168.0.50      Jetson Nano, статический IP / static IP
├── 192.168.0.x       телефоны / phones
└── 192.168.0.x       ноутбуки / laptops
```

> 🇷🇺 Gateway `192.168.0.1` и модель роутера подтверждены инвентаризацией. Jetson использует профиль `nas_jetson_nano-lan` со статикой `192.168.0.50/24`; профиль не удалять.
>
> 🇬🇧 Gateway `192.168.0.1` and router model confirmed by current inventory. Jetson uses the `nas_jetson_nano-lan` profile with static `192.168.0.50/24`; do not remove this profile.

## 1.1. Stage 0 — прямое подключение / Direct link

> 🇷🇺 Первичная настройка свежего Jetson Nano в headless-режиме идёт через **serial console по Micro-USB** (`/dev/ttyACM0`, скорость `115200`). Только после этого Jetson доступен по сети.
>
> 🇬🇧 Initial headless setup of a fresh Jetson Nano goes through the **Micro-USB serial console** (`/dev/ttyACM0`, speed `115200`). Only after that is Jetson accessible over the network.

🇷🇺 Для аппаратного аудита и SSH после first-boot используется прямое подключение Jetson к ноутбуку по Ethernet:
🇬🇧 For hardware audit and SSH after first-boot, Jetson is connected directly to the laptop via Ethernet:

```text
Ноутбук / Laptop
├── обычный интернет/LAN интерфейс / normal internet/LAN interface
└── USB-Ethernet adapter, ens37, 192.168.1.2/24
        |
        └── Jetson Nano, временный IP / temporary IP in 192.168.1.0/24
```

🇷🇺 Домашний роутер в Stage 0 не используется. Эта схема нужна для bootstrap, SSH и диагностики.
🇬🇧 The home router is not used in Stage 0. This scheme is for bootstrap, SSH and diagnostics only.

```bash
ip -br addr
lsusb
ip neigh show dev ens37
nmap -sn 192.168.1.0/24
ssh <user>@<jetson-direct-link-ip>
```

## 1.2. USB device-mode доступ с Windows / USB device-mode access from Windows (recovery/admin)

> 🇷🇺 Проверено 2026-06-13. Если Jetson подключён по micro-USB к Windows-хосту, L4T device mode поднимает 4 интерфейса одновременно.
>
> 🇬🇧 Verified 2026-06-13. When Jetson is connected via micro-USB to a Windows host, L4T device mode brings up 4 interfaces simultaneously.

- RNDIS Ethernet — в `Get-NetAdapter` / in `Get-NetAdapter`
- NCM Ethernet — второй / second Ethernet
- USB-serial (`COMx`, `VID_0955` NVIDIA) — консоль / console
- USB Mass Storage (`L4T-README`)

🇷🇺 На стороне Jetson все интерфейсы объединены в бридж `l4tbr0` (`192.168.55.1/24`).
**IPv4 `192.168.55.1` обычно недоступен с Windows-хоста** — рабочий вариант — **IPv6 link-local**:

🇬🇧 On Jetson side all interfaces are bridged as `l4tbr0` (`192.168.55.1/24`).
**IPv4 `192.168.55.1` is usually unreachable from Windows** — working approach is **IPv6 link-local**:

```powershell
Get-NetAdapter                                   # найти ifIndex / find ifIndex of RNDIS adapter
ping -6 fe80::1%<ifIndex>
Test-NetConnection -ComputerName "fe80::1%<ifIndex>" -Port 22
ssh admin@fe80::1%<ifIndex>
```

🇷🇺 `<ifIndex>` меняется между подключениями USB — каждый раз смотреть в `Get-NetAdapter`.

🇬🇧 `<ifIndex>` changes between USB connections — always check `Get-NetAdapter` first.

🇷🇺 Настройка SSH-ключа (на Windows нет `ssh-copy-id`) / SSH key setup (no `ssh-copy-id` on Windows):

```powershell
Get-Content ~/.ssh/id_ed25519.pub | ssh admin@fe80::1%<ifIndex> `
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo DONE"
```

## 2. Правило публикации сервисов / Service publication rule

🇷🇺 Прямой публичный port forwarding на домашнем роутере отсутствует. Внешний доступ — через обратный SSH-тоннель от Jetson к VPS.
🇬🇧 No direct public port forwarding on the home router. External access is via reverse SSH tunnel from Jetson to VPS.

| Сервис / Service | Jetson порт / Port | Внешний доступ / External access |
|---|---|---|
| Nextcloud | 8080 | `http://193.8.215.130:8080/` (VPS nginx) |
| Immich | 2283 | `http://193.8.215.130:2283/` (VPS nginx) |
| LLM Gateway | 8090 | `http://193.8.215.130:8090/` (VPS nginx) |
| SSH управление / SSH management | 22 | `ssh -p 10022 admin@127.0.0.1` с VPS / from VPS |
| Samba | 445/139 | **LAN only** — iptables 192.168.0.0/24 |

## 3. VPN-варианты / VPN options (overview)

| Вариант / Option | Назначение / Purpose | Оценка / Assessment |
|---|---|---|
| **Reverse SSH + autossh** | CGNAT-proof, свой VPS / own VPS | ✅ **Реализовано / Implemented (ADR-0005)** |
| Tailscale | быстрый старт / quick start without white IP | ❌ Заменён / Replaced by ADR-0005 |
| ZeroTier | mesh-сеть / mesh network | не рассматривался / not evaluated |
| WireGuard через VPS / via VPS | контролируемая схема / controlled scheme | ❌ DKMS проблемы / issues on L4T 4.9 (ADR-0003) |
| AmneziaVPN | уже используется для семейного VPN / family VPN | ⚠️ НЕ ТРОГАТЬ / DO NOT TOUCH |

## 3.4. Реализованная схема / Active scheme: VPS + autossh reverse tunnel (2026-06-21)

🇷🇺 Выбранное и работающее решение. Обоснование: [ADR-0005](decisions/ADR-0005-vps-autossh-reverse-tunnel.md)
🇬🇧 Chosen and operational solution. Details: [ADR-0005](decisions/ADR-0005-vps-autossh-reverse-tunnel.md)

```
Jetson (CGNAT) ──────────────────────────────→ VPS 193.8.215.130
autossh -R 18080:localhost:8080                  sshd: 127.0.0.1:18080
        -R 12283:localhost:2283                       127.0.0.1:12283
        -R 18090:localhost:8090                       127.0.0.1:18090
        -R 10022:localhost:22                         127.0.0.1:10022
                                                nginx (host network):
                                                  :8080 → 127.0.0.1:18080
                                                  :2283 → 127.0.0.1:12283
                                                  :8090 → 127.0.0.1:18090
```

🇷🇺 Статус (2026-06-27): `nas_jetson_nano-tunnel.service` — active (running), enabled.
🇬🇧 Status (2026-06-27): `nas_jetson_nano-tunnel.service` — active (running), enabled.

🇷🇺 Что нельзя менять / What must not be changed:
- **Amnezia-контейнеры на VPS** — не трогать (семейный VPN ~25 клиентов) / do not touch (family VPN ~25 clients)
- **`nas_jetson_nano-lan` профиль** на Jetson (eth0, 192.168.0.50/24) — не удалять / do not remove

## 3.1. WireGuard контур (исторический референс) / WireGuard circuit (historical reference)

```text
Yandex VM                 WireGuard                 EU VPS
wg-eu 10.210.0.1/30  <-------------------->  wg-yandex 10.210.0.2/30
```

🇷🇺 Возможно использование для NAS_Jetson_Nano позже как controlled admin path. Не открывать без отдельного risk-документа.
🇬🇧 Could be used for NAS_Jetson_Nano later as a controlled admin path. Do not use without a separate risk document.

## 3.2. EU VPS — VPN-endpoint

| Параметр / Parameter | Значение / Value |
|---|---|
| Роль / Role | Внешний VPN/WireGuard endpoint (admin path) |
| Публичный IP / Public IP | `45.95.2.49` |
| SSH-пользователь / user | `sshadmin` |
| SOCKS5-прокси / proxy | `45.95.2.49:40099` |
| WireGuard-порт / port | `51830/udp` |
| Туннельная подсеть / Tunnel subnet | `10.210.0.0/30` |

> 🇷🇺 Секреты вне репозитория. SSH-ключ и WireGuard ключи в git не хранятся.
> 🇬🇧 Secrets outside repository. SSH key and WireGuard keys are not in git.

## 3.3. wg-nas_jetson_nano (тест 2026-05-31, откачено / rolled back)

> ⚠️ 🇷🇺 Статус: откачено 2026-06-13 из-за нестабильности через CGNAT. Раздел оставлен для истории.
> ⚠️ 🇬🇧 Status: rolled back 2026-06-13 due to CGNAT instability. Section kept for reference.

## 4. DNS внутри сети / Internal DNS

🇷🇺 Минимально: доступ по IP. Расширенно:
🇬🇧 Minimum: IP access. Extended:

```text
cloud.home.arpa  -> 192.168.0.50
photos.home.arpa -> 192.168.0.50
llm.home.arpa    -> 192.168.0.50
```

## 5. Роутер / Router

🇷🇺 На домашнем роутере выполнить:
🇬🇧 On the home router:

1. 🇷🇺 Найти Jetson в DHCP-клиентах / 🇬🇧 Find Jetson in DHCP clients
2. 🇷🇺 Закрепить IP `192.168.0.50` / 🇬🇧 Reserve IP `192.168.0.50`
3. 🇷🇺 Проверить ping из LAN / 🇬🇧 Verify ping from LAN
4. 🇷🇺 Не включать port forwarding на первом этапе / 🇬🇧 Do not enable port forwarding in Stage 1

### 5.1. Планируемый усилитель Wi-Fi / Planned Wi-Fi extender

🇷🇺 Физическое устройство Keenetic Omni KN-1410 добавлено в инвентаризацию
2026-07-17, но ещё не подключено и не настроено. Целевая роль — дополнительный
узел `Extender / Repeater` в существующей сети `192.168.0.0/24`; DHCP, gateway,
firewall и NAT остаются на основном TP-Link / Aginet EC220-G5.

🇬🇧 A physical Keenetic Omni KN-1410 was added to inventory on 2026-07-17 but
has not yet been connected or configured. Its target role is an additional
`Extender / Repeater` node in the existing `192.168.0.0/24` LAN; DHCP, gateway,
firewall, and NAT remain on the TP-Link / Aginet EC220-G5 main router.

Полная карточка, safety gate, проверка и rollback / Full device card, safety
gate, validation, and rollback:
[`25_KEENETIC_OMNI_KN1410.md`](25_KEENETIC_OMNI_KN1410.md).
