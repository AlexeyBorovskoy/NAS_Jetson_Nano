# 25. Keenetic Omni KN-1410 extender inventory and runbook

> RU: Карточка физического устройства, план безопасного ввода в сеть и процедура
> настройки в роли усилителя Wi-Fi.
>
> EN: Physical-device inventory, safe network-introduction plan, and Wi-Fi
> extender configuration runbook.
>
> Updated / Обновлено: 2026-08-10.

## 0. ⛔ План закрыт / Plan closed (2026-08-10)

🇷🇺 **Ввод Keenetic Omni KN-1410 в сеть отменён.** Куплен комплект TP-Link Deco E4,
который решает ту же задачу лучше: бесшовный роуминг вместо простого репитера, единый
SSID, гостевая сеть, резервирование адресов. Более того, EC220-G5, к которому этот план
предполагал подключать усилитель, **выводится из эксплуатации** — Deco становится
основным роутером. См. [`27_HOME_NETWORK_MESH.md`](27_HOME_NETWORK_MESH.md).

🇬🇧 **Commissioning of the Keenetic Omni KN-1410 is cancelled.** A TP-Link Deco E4 mesh
kit was purchased and covers the same need better. The EC220-G5 this plan attached to is
being decommissioned. See [`27_HOME_NETWORK_MESH.md`](27_HOME_NETWORK_MESH.md).

**Судьба устройства:** остаётся холодным резервом, в сеть не вводится. Документ сохранён
как карточка железа и на случай, если резерв понадобится.

**Что остаётся в силе:** правило безопасности — при любом будущем вводе подключать
изолированно к workstation, не вводить в production LAN с активным DHCP и не делать
factory reset без явного подтверждения (правило №9 в `CLAUDE.md`).

## 1. Current status / Текущий статус

| Field / Поле | Value / Значение |
|---|---|
| Inventory state | Observed from label photo on 2026-07-17 |
| Operational state | ⛔ **Cancelled 2026-08-10; cold spare, will not be commissioned** |
| Intended role | ~~Wi-Fi repeater/extender~~ — superseded by TP-Link Deco E4 mesh |
| Main router | ~~TP-Link / Aginet EC220-G5, `192.168.0.1`~~ — being decommissioned; Deco E4 becomes the router |
| Target LAN | `192.168.0.0/24`; DHCP remains on the main router |
| Public exposure | Forbidden; management must remain LAN-only |
| Change authority | Factory reset and mode changes require explicit user confirmation |

The label photograph itself is not stored in the repository because it exposes
device credentials and unique hardware identifiers.

## 2. Device identity / Идентификация устройства

| Field / Поле | Public inventory value | Source / Источник |
|---|---|---|
| Manufacturer | Keenetic | Device label |
| Product family | Omni | Device label |
| Model | `KN-1410` | Device label and official quick-start guide |
| Country of manufacture | China / КНР | Device label |
| Power input | `12 V DC, 1 A` | Device label and official quick-start guide |
| Default management name | `my.keenetic.net` | Device label |
| Hardware mode selector | Two-position `A/B`; `B` is Extender mode | Official model guide |
| Wi-Fi bands | 2.4 GHz and 5 GHz | Official model-specific extender guide |
| Wi-Fi antennas | Two printed antennas, 5 dBi | Official quick-start guide |
| Network ports | Ports `0`, `1`, `2`, `3`, `4` | Official quick-start guide |
| USB | One universal USB port | Official quick-start guide |
| WPS | Wi-Fi control button; short press only | Official quick-start guide |
| Support status | End of Support; no further KeeneticOS updates | Official Keenetic support page |

Do not assume Gigabit Ethernet or a particular installed KeeneticOS build until
the live device reports its negotiated link speed and firmware version.

## 3. Sensitive label data / Чувствительные данные с наклейки

The following values were visible in the source photo but are intentionally not
copied into Git-tracked files:

| Label field | Local placeholder | Handling rule |
|---|---|---|
| Factory SSID | `KEENETIC_OMNI_FACTORY_SSID` | Local secret only; rotate during setup |
| Factory Wi-Fi password | `KEENETIC_OMNI_FACTORY_WIFI_PASSWORD` | Local secret only; **must be changed** |
| Service code | `KEENETIC_OMNI_SERVICE_CODE` | Unique device identifier; local only |
| Serial number | `KEENETIC_OMNI_SERIAL` | Unique device identifier; local only |
| WAN MAC address | `KEENETIC_OMNI_WAN_MAC` | Unique device identifier; local only |
| New admin password | `KEENETIC_OMNI_ADMIN_PASSWORD` | Generate during setup; local only |
| Assigned LAN address | `KEENETIC_OMNI_LAN_IP` | Record after DHCP discovery |

The source photo exposed the factory Wi-Fi password. Treat that password as
compromised and never reuse it after the device is commissioned.

## 4. Target network role / Целевая роль в сети

```text
Internet / ISP
    |
    v
TP-Link / Aginet EC220-G5 (main router)
gateway + DHCP: 192.168.0.1, LAN 192.168.0.0/24
    |
    +-- Jetson Nano: 192.168.0.50/24
    |
    +-- Keenetic Omni KN-1410
           mode: Extender / Repeater
           uplink: Wi-Fi to the main router
           DHCP/NAT: disabled in additional mode
           management: DHCP address from the main router
           fallback service address while isolated: 192.168.1.3
           clients: Wi-Fi and Ethernet
```

The main router is not a Keenetic, so the safe target is a third-party-router
extender connection using WPS or manual wireless setup. Do not modify the main
router's DHCP, firewall, VPN, port forwarding, or existing Wi-Fi security unless
a separate reviewed step explicitly requires it.

## 5. Pre-change safety gate / Проверка перед изменением

Before connecting the device to the production LAN:

1. Confirm that the Keenetic is spare and its old router configuration is no
   longer needed, or save its `startup-config` backup first.
2. Keep the admin workstation online through a separate Wi-Fi/mobile/second-NIC
   path. Replacing its only Internet cable with the isolated Keenetic can break
   the remote Codex session.
3. Connect the workstation to a Keenetic home/LAN port, not to the main router.
4. Do not connect the Keenetic to the production LAN while it may still run its
   own DHCP server in Router mode.
5. Inspect current address, firmware, mode, configuration backup availability,
   and negotiated Ethernet link speed read-only first.
6. Obtain explicit confirmation immediately before a factory reset.

## 6. Planned setup procedure / План настройки

### 6.1 Preferred controlled path: LAN from the workstation

1. Power the Keenetic with the verified `12 V DC, 1 A` adapter.
2. Connect the Windows workstation by Ethernet to a Keenetic LAN/home port.
3. Discover the interface and address without changing any production route:

   ```powershell
   Get-NetAdapter
   Get-NetIPConfiguration
   arp -a
   Test-NetConnection 192.168.1.1 -Port 80
   ```

4. If the device is still in Router mode, try `http://my.keenetic.net` or
   `http://192.168.1.1`.
5. Save `startup-config` if the existing configuration has recovery value.
6. With explicit confirmation, move the hardware selector to `B`. The official
   model guide requires a factory reset when commissioning a selector-equipped
   device as an extender.
7. If the isolated extender does not receive DHCP, temporarily set the Windows
   Ethernet adapter to an unused address in `192.168.1.4`–`192.168.1.254/24`
   and open `http://192.168.1.3`.
8. Configure the uplink to the main router:
   - WPS: one short press for 2.4 GHz or two short presses for 5 GHz; or
   - manual SSID selection and local password entry in the web UI.
9. Do not send the main Wi-Fi password through chat or logs.
10. Return the Windows Ethernet adapter to DHCP after isolated setup.

### 6.2 Placement

Place the extender where it still receives a strong signal from the main
router, normally between the main router and the weak-coverage area. Do not put
it directly in the dead zone.

Wireless repeating shares radio airtime and may reduce useful throughput. If an
Ethernet cable can be installed between the routers, use the Keenetic as a wired
access point/extender for better performance and stability.

## 7. Acceptance checks / Проверка результата

Record the following only after live verification:

| Check | Acceptance criterion |
|---|---|
| Mode | Keenetic reports Extender/Repeater mode |
| DHCP | Clients receive `192.168.0.x` from the TP-Link main router |
| NAT/DHCP on Keenetic | Not active in additional mode |
| Management IP | New DHCP address recorded as `KEENETIC_OMNI_LAN_IP` locally |
| Main SSID | Expected network is repeated; no unintended open SSID |
| Security | New unique admin password; factory Wi-Fi password no longer active |
| Internet | DNS, HTTPS, and normal browsing work through the extender |
| LAN | Jetson `192.168.0.50` remains reachable; no gateway/subnet changes |
| VPN | Amnezia client behavior remains unchanged |
| Performance | Baseline signal, latency, download, and upload measured before/after |

Windows verification commands:

```powershell
Get-NetIPConfiguration
Get-NetRoute -DestinationPrefix 0.0.0.0/0
Test-NetConnection 192.168.0.1 -Port 80
Test-NetConnection 192.168.0.50 -Port 22
Resolve-DnsName example.com
```

## 8. Risks / Риски

- Factory reset deletes the old device configuration and administrator password.
- Connecting two active DHCP servers to the same LAN can disrupt all clients.
- The model is End of Support and no longer receives security updates. Keep its
  management interface LAN-only and do not expose it to the Internet.
- A wireless repeater can improve coverage while reducing peak throughput.
- WPS should be used only for enrolment and disabled on the main router afterward
  if the main router supports that workflow.
- The existing `nas_jetson_nano-lan` profile and Jetson static address must not be
  changed as part of this work.
- Amnezia VPN, VPS containers, and production router firewall rules are out of
  scope.

## 9. Rollback

If commissioning fails:

1. Disconnect the Keenetic from the production LAN.
2. Restore the Windows Ethernet adapter to automatic DHCP/DNS.
3. Return the hardware mode selector to `A` only if Router mode is intentionally
   required.
4. Restore a previously saved `startup-config` when appropriate.
5. Do not factory-reset again or change the main router without explicit approval.

The main TP-Link router and Jetson network remain the source of truth throughout
rollback.

## 10. Official sources / Официальные источники

- [Keenetic Omni KN-1410 quick-start guide](https://help.keenetic.com/hc/article_attachments/360005190260/KN-1410-qsg.pdf)
- [Connecting Omni KN-1410 as an extender](https://support.keenetic.com/tr/omni/kn-1410/en/15232-connecting-extenders-to-mesh-wi-fi-system.html)
- [Connecting an extender to a router from another vendor](https://support.keenetic.com/explorer/kn-1621/en/26896-connecting-extender-to-a-router-from-another-vendor.html)
- [Accessing the extender web interface](https://support.keenetic.com/speedster/kn-3012/en/22353-accessing-the-web-interface-of-the-extender.html)
- [KeeneticOS support status for Omni KN-1410](https://support.keenetic.com/ua/omni/kn-1410/en/6319-latest-development-release.html)
