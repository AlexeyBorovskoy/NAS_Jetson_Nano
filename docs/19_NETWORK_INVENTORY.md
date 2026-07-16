# 19. Network Inventory / Инвентаризация сети

> 🇬🇧 This document records the home network layout for the NAS_Jetson_Nano test stand. It is a sanitized public inventory: real Wi-Fi passwords, router serial numbers, router MAC addresses, and private credentials must stay in `config/.env` (gitignored).
>
> 🇷🇺 Документ фиксирует сетевую топологию тестового стенда NAS_Jetson_Nano. Публичная версия: реальные пароли Wi-Fi, серийные номера, MAC-адреса и учётные данные хранятся только в `config/.env` (gitignored).
>
> Updated / Обновлено: 2026-06-27.

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
- Do not touch the Amnezia VPN containers on VPS 193.8.215.130 through SSH or
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
           eth0: nas_jetson_nano-lan, static 192.168.0.50/24
           gateway: 192.168.0.1
           services: LAN-only
           |
           +-- USB storage
                  data disk attached directly to Jetson over USB
                  not a network device

External access (implemented 2026-06-21):

Internet / mobile client
    |
    v (HTTP)
VPS 193.8.215.130 — nginx (network_mode: host)
    :8080 Nextcloud, :2283 Immich,
    :8090 LLM GW
    |
    v (SSH reverse tunnel, autossh)
Jetson Nano 192.168.0.50
    Tunnel: nas_jetson_nano-tunnel.service (enabled, autostart)
    SSH management from VPS: ssh -p 10022 admin@127.0.0.1

VPS:
    IP: 193.8.215.130 (Vienna, AEZA GROUP)
    SSH: ssh -i ~/.ssh/borovskoy_new_ed25519 root@193.8.215.130
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
| External access | Implemented path | VPS 193.8.215.130 + autossh | ADR-0005 | ✅ Live |
| VPS | Host | 193.8.215.130 (Vienna, AEZA) | observed | ✅ Active |
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

## 6. Validation Commands

From Windows admin workstation:

```powershell
Get-NetIPConfiguration
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
| External access | ✅ Implemented via VPS reverse tunnel (ADR-0005) | — |

## 8. Rollback

This inventory step does not change router or Jetson network settings.

If a future router UI session accidentally opens an edit form, leave the page
without saving. If a future Jetson LAN change breaks access, use USB recovery:

```powershell
ssh admin@fe80::1%<ifIndex>
```
