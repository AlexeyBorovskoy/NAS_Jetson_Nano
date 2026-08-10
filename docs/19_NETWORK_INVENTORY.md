# 19. Network Inventory / Инвентаризация сети

> 🇬🇧 This document records the home network layout for the NAS_Jetson_Nano test stand. It is a sanitized public inventory: real Wi-Fi passwords, router serial numbers, router MAC addresses, and private credentials must stay in `config/.env` (gitignored).
>
> 🇷🇺 Документ фиксирует сетевую топологию тестового стенда NAS_Jetson_Nano. Публичная версия: реальные пароли Wi-Fi, серийные номера, MAC-адреса и учётные данные хранятся только в `config/.env` (gitignored).
>
> Updated / Обновлено: 2026-08-10.

## 1а. Current measured state / Текущее измеренное состояние (2026-08-10)

| Параметр | Значение | Как получено |
|---|---|---|
| Шлюз | TP-Link / Aginet **EC220-G5**, `192.168.0.1`, гигабит | web UI |
| Подсеть | `192.168.0.0/24` | `ip route` на Jetson |
| Jetson eth0 | `192.168.0.50`, **1000 Мбит/с Full**, 0 ошибок RX/TX | `ethtool eth0` |
| Jetson MAC | `00:04:4b:e6:88:dc` | `ip link` |
| SSID | `TP-Link_828C` (2.4) и `TP-Link_828C_5G` (5) — **разные имена** | `netsh wlan` |
| Рабочая станция | 802.11ac, 5 ГГц, канал 48, сигнал **48 %** | `netsh wlan` |
| Wi-Fi → NAS, реально | **17.6 МБ/с (141 Мбит/с)**, 400 МБ за 23.8 с | HTTP-загрузка с Jetson |
| Диски NAS | SSD 250 МБ/с запись; HDD 106 МБ/с чтение | `dd` |

**Вывод:** узкое место сегодня — Wi-Fi, а не диски и не Ethernet (141 Мбит/с против 800+,
которые способны отдать диски). Сигнал 48 % означает, что одна точка квартиру не покрывает.

### 🔴 Смена внешнего IP (2026-08-07)

Прежний адрес VPS `193.8.215.130` **заблокирован российскими ISP** — per-IP stateful-блок:
новые потоки (TCP и UDP, любой порт) дропаются, уже установленные продолжают работать.
Рабочий адрес — **`95.163.176.103`**; дополнительно поднят IPv6 `2a12:5940:665a::2/48`.

Практическое следствие для доступа:

| Путь | Когда использовать |
|---|---|
| `95.163.176.103` | обычный, работает |
| `172.29.172.1` (внутренний адрес VPS в VPN-туннеле) | если публичный IP снова заблокируют |

Хост туннеля на Jetson правится в **root-owned** `/opt/nasa/config/.env` (`VPS_HOST=`),
а не в `~/nasa/config/.env`. После правки — `systemctl restart nasa-tunnel`.

### Периметр (проверено 2026-08-10)

Наружу на VPS открыты только **22/tcp** (нужен для реверс-туннелей), **443/tcp** (XRay)
и **40568/udp** (AmneziaWG). Все сервисные порты (8080/8443/2283/2443/8090/9443/8099/8091)
доступны только с `172.29.172.0/24` и `10.8.1.0/24`, то есть через VPN.

⚠️ **Внутри домашней LAN сегментации нет:** Nextcloud, Immich, Portainer, admin-API `:8099`
и Samba открыты любому, кто знает пароль Wi-Fi. Это остаточный риск, а не закрытый пункт.

Scope of this step:

1. Observe current network state.
2. Record target topology for Jetson + USB HDD.
3. Keep router, firewall, VPN, DHCP, and Wi-Fi settings unchanged.
4. Mark items that still require router UI verification.

## 2. Safety Boundaries

- Do not change router DHCP, firewall, port forwarding, VPN, Wi-Fi, or ISP
  settings during inventory.
- Do not expose Nextcloud, Immich, LLM Gateway, Samba, or SSH directly to the
  internet via port forwarding on the home router.
- Do not touch the Amnezia VPN containers on VPS 95.163.176.103 through SSH or
  `wg set` — serves ~25 clients.
- External access implemented via VPS reverse SSH tunnel (ADR-0005). Tailscale
  is archival/alternative documentation only.
- Treat router photos, SSIDs, passwords, MAC addresses, serial numbers, and
  admin credentials as secrets.

## 3. Target Topology

```text
Internet / ISP
    |
    v
Home router: TP-Link / Aginet EC220-G5
LAN: 192.168.0.0/24
Gateway: 192.168.0.1
    |
    +-- Windows laptop / admin workstation
    |      Wi-Fi client, current observed IP: 192.168.0.106
    |
    +-- Jetson Nano
    |      eth0: nas_jetson_nano-lan, static 192.168.0.50/24
    |      gateway: 192.168.0.1
    |      services: LAN-only
    |      |
    |      +-- USB storage
    |             data disk attached directly to Jetson over USB
    |             not a network device
    |
    +-- Keenetic Omni KN-1410 (planned, not configured)
           target mode: Wi-Fi Extender / Repeater
           management: DHCP address from the home router
           DHCP/NAT: disabled in additional mode

External access (implemented 2026-06-21):

Internet / mobile client
    |
    v (HTTP)
VPS 95.163.176.103 — nginx (network_mode: host)
    :8080 Nextcloud, :2283 Immich,
    :8090 LLM GW
    |
    v (SSH reverse tunnel, autossh)
Jetson Nano 192.168.0.50
    Tunnel: nas_jetson_nano-tunnel.service (enabled, autostart)
    SSH management from VPS: ssh -p 10022 admin@127.0.0.1

VPS:
    IP: 95.163.176.103 (Vienna, AEZA GROUP)
    SSH: ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103
    Caution: Amnezia VPN containers — DO NOT TOUCH.
```

## 4. Network Settings Table

| Component | Setting | Value | Source | Status |
|---|---|---|---|---|
| Home router | Vendor | TP-Link / Aginet | Router label photo | Observed |
| Home router | Model | EC220-G5 / EC220-G5(RU) | Router label photo + login page tab title | Observed |
| Home router | Hardware version | 2.20 | Router label photo | Observed |
| Home router | Admin URL | `http://192.168.0.1` | Router label photo + HTTP check | Verified reachable |
| Home router | HTTPS admin UI | `443/tcp` closed | `Test-NetConnection` | Observed |
| Home router | LAN gateway | `192.168.0.1` | Windows network config | Observed |
| Home router | LAN CIDR | `192.168.0.0/24` | Existing ADR + observed client IP | Accepted |
| Home router | Admin username | `HOME_ROUTER_ADMIN_USERNAME` | Local secret only | Assumed / needs confirmation |
| Home router | Admin password | `HOME_ROUTER_ADMIN_PASSWORD` | Local secret only | Missing / user input needed |
| Home router | MAC address | `HOME_ROUTER_MAC` | Router label photo | Secret, stored locally |
| Home router | Serial number | `HOME_ROUTER_SERIAL` | Router label photo | Secret, stored locally |
| Wi-Fi 2.4 GHz | SSID | `HOME_WIFI_SSID_2G` | Router label photo | Secret, stored locally |
| Wi-Fi 5 GHz | SSID | `HOME_WIFI_SSID_5G` | Router label photo | Secret, stored locally |
| Wi-Fi | Password / PIN | `HOME_WIFI_PASSWORD` | Router label photo | Secret, stored locally |
| Planned extender | Vendor / model | Keenetic Omni `KN-1410` | Device label photo + official guide | Observed |
| Planned extender | Intended role | Wi-Fi Extender / Repeater | User request | Planned; not configured |
| Planned extender | Mode selector | `A/B`; target `B` | Official model guide | Verify physically before change |
| Planned extender | Management name | `my.keenetic.net` in Router mode | Device label | Observed; not live-verified |
| Planned extender | Isolated service IP | `192.168.1.3` in additional mode without DHCP | Official guide | Recovery path only |
| Planned extender | Target LAN IP | `KEENETIC_OMNI_LAN_IP` from main-router DHCP | Local secret inventory | Pending |
| Planned extender | Factory SSID | `KEENETIC_OMNI_FACTORY_SSID` | Device label photo | Secret; do not commit |
| Planned extender | Factory Wi-Fi password | `KEENETIC_OMNI_FACTORY_WIFI_PASSWORD` | Device label photo | Exposed; rotate during setup |
| Planned extender | Service code | `KEENETIC_OMNI_SERVICE_CODE` | Device label photo | Secret; do not commit |
| Planned extender | Serial number | `KEENETIC_OMNI_SERIAL` | Device label photo | Secret; do not commit |
| Planned extender | WAN MAC | `KEENETIC_OMNI_WAN_MAC` | Device label photo | Secret; do not commit |
| Planned extender | Power | `12 V DC, 1 A` | Device label + official guide | Observed |
| Planned extender | Support status | End of Support; no updates | Official Keenetic support | Accepted risk; LAN-only |
| Admin workstation | Current Wi-Fi IP | `192.168.0.106` | Windows network config | Observed |
| Jetson Nano | LAN profile | `nas_jetson_nano-lan` | ADR-0003 | Accepted, do not delete |
| Jetson Nano | LAN IP | `192.168.0.50/24` | ADR-0003 + local secrets | Target / needs LAN re-check |
| Jetson Nano | Gateway | `192.168.0.1` | ADR-0003 | Target / needs LAN re-check |
| Jetson Nano | USB recovery SSH | `admin@fe80::1%<ifIndex>` | Verified USB device-mode flow | Verified pattern |
| Jetson Nano | LAN SSH | `admin@192.168.0.50` | Target LAN path | Pending; currently not verified |
| USB HDD | Attachment | USB to Jetson Nano | User-confirmed target topology | Accepted |
| USB HDD | Network role | none | Storage architecture | Local block device only |
| USB HDD | Working mount | `/mnt/storage` | ADR-0002 + 2026-06-23 incident | Mounted; preflight clean |
| USB HDD | Existing-data intake mount | `/mnt/hdd-check` read-only | Storage design | Use before migration |
| USB HDD | Current incident | Realtek RTL9210B-CG / 250 GB recovered as `/dev/sda1`; prior kernel `error -71` and ext4 errors remain hardware risk | Live check 2026-06-23 | Open / recovered |
| Nextcloud | LAN port | `8080/tcp` | Compose/docs | Live after controlled start |
| Immich | LAN port | `2283/tcp` | Compose/docs | Live |
| LLM Gateway | LAN port | `8090/tcp` | Compose/docs | LAN-only |
| Samba | LAN port | `445/tcp` | Samba design | LAN-only |
| SSH | LAN port | `22/tcp` | Jetson admin | LAN/VPN-only |
| VPS | Host | `VPS_HOST` | `config/.env` | Secret/local operational value |
| VPS | User | `VPS_USER` | `config/.env` | Secret/local operational value |
| VPS | SSH key | `VPS_SSH_KEY` | `config/.env` | Secret/local operational value |
| External access | Implemented path | VPS 95.163.176.103 + autossh | ADR-0005 | ✅ Live |
| VPS | Host | 95.163.176.103 (Vienna, AEZA) | observed | ✅ Active |
| VPS nginx | Public ports | 8080/2283/8090 (HTTP) | docker/vps/ | ✅ Active; Nextcloud upstream live |
| SSH tunnel | nas_jetson_nano-tunnel.service | -R 18080/12283/18090/10022 | systemd/nas_jetson_nano-tunnel.service | ✅ Active |
| Public port forwarding | Home router | none for Stage 1 | ADR-0003 | Required safe default |

## 5. Router UI Status

The router web UI is reachable at `http://192.168.0.1` and returns the TP-Link
login page. The current screenshot shows a password-only login form. The page
uses client-side encryption before submitting login data.

Current limitation:

- `HOME_ROUTER_ADMIN_USERNAME` is recorded locally as an assumption, not as a
  router-UI-verified value.
- `HOME_ROUTER_ADMIN_PASSWORD` is not known yet.
- The Wi-Fi password/PIN from the label must not be assumed to be the router
  admin password unless confirmed by the user.

Router UI verification is therefore pending. When the admin password is
available, inspect only these read-only pages:

1. LAN IP/subnet.
2. DHCP server enabled/disabled and DHCP range.
3. DHCP reservation/static lease for Jetson `192.168.0.50`.
4. Connected clients list.
5. Port forwarding / virtual servers list.
6. UPnP state.
7. Firewall remote management state.
8. Wi-Fi SSIDs/security mode.

Do not save or apply any router setting changes during this inventory.

### 5.1 Planned Keenetic extender

The Keenetic Omni KN-1410 was inventoried from its label photo on 2026-07-17.
It has not yet been connected, reset, or configured. Its full sanitized device
card and controlled commissioning procedure are in
[`25_KEENETIC_OMNI_KN1410.md`](25_KEENETIC_OMNI_KN1410.md).

The source photo exposed a factory Wi-Fi password plus unique device identifiers.
Those values must remain outside Git and the factory Wi-Fi password must be
rotated during commissioning.

## 6. Validation Commands

From Windows admin workstation:

```powershell
Get-NetIPConfiguration
Get-NetAdapter
Get-NetRoute -DestinationPrefix 0.0.0.0/0
Test-NetConnection 192.168.0.1 -Port 80
Test-NetConnection 192.168.0.1 -Port 443
Test-NetConnection 192.168.0.50 -Port 22
arp -a
```

From Windows USB recovery path to Jetson:

```powershell
Get-NetAdapter
ping -6 fe80::1%<ifIndex>
Test-NetConnection -ComputerName "fe80::1%<ifIndex>" -Port 22
ssh admin@fe80::1%<ifIndex>
```

From Jetson after LAN cable is connected:

```bash
ip -br addr show eth0
ip route
nmcli connection show nas_jetson_nano-lan
ping -c 3 192.168.0.1
```

Storage check after USB storage is attached to Jetson:

```bash
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,TRAN,RO
mountpoint /mnt/storage || echo "/mnt/storage is not mounted"
sudo dmesg -T | grep -i -E "usb|uas|reset|I/O error|error -71" | tail -n 80
sudo bash scripts/storage/storage_preflight.sh
```

## 7. Current Open Items

| Item | Why it matters | Next safe action |
|---|---|---|
| Router admin password missing | DHCP range and static lease cannot be verified from UI | User provides password; inspect only |
| Jetson LAN SSH | ✅ Verified: `admin@192.168.0.50:22` works | — |
| VPS external access | ✅ Live: nginx+tunnel, ports 8080/2283/8090 | — |
| USB storage incident | 250 GB device recovered as `/dev/sda1` and mounted at `/mnt/storage`, but prior `error -71`/ext4 errors show hardware risk | Keep preflight/boot guard; replace suspect cable/enclosure/power if errors return |
| HDD partition | Target ext4 partition for NAS is active: label `nas_jetson_nano-storage`, UUID tracked in fstab | Keep read-only fsck path for future incidents; destructive format only with explicit confirmation |
| External access | ✅ Implemented via VPS reverse tunnel (ADR-0005), now pointing at `95.163.176.103` | — |
| Service ports exposed to internet | ✅ Closed 2026-08-07: ufw allows service ports only from `172.29.172.0/24` and `10.8.1.0/24` | — |
| VPS IP blocked from RU ISPs | Old `193.8.215.130` unreachable; migrated to `95.163.176.103` | Keep `172.29.172.1` (in-tunnel) as the fallback path |
| No LAN segmentation | Every service is reachable by anyone with the Wi-Fi password | Guest network during the home-network rebuild (`26_DECO_E4_NETWORK.md`) |
| Keenetic Omni KN-1410 extender | Physical device observed; firmware, current IP, link speed, and mode not yet verified | Connect in isolation by LAN; inspect read-only; configure only after safety gate |
| TP-Link Deco E4 mesh (2 units) | Purchased 2026-08; **100 Mbit Ethernet ports** — Jetson must stay on the EC220-G5 gigabit port | Decision pending; plan in [`26_DECO_E4_NETWORK.md`](26_DECO_E4_NETWORK.md). Access Point mode only |

## 8. Rollback

This inventory step does not change router or Jetson network settings.

The Keenetic inventory addition is documentation-only. If a future extender
session causes a conflict, disconnect it from the production LAN first and
restore the Windows adapter to automatic DHCP/DNS before any further action.

If a future router UI session accidentally opens an edit form, leave the page
without saving. If a future Jetson LAN change breaks access, use USB recovery:

```powershell
ssh admin@fe80::1%<ifIndex>
```
