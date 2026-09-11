# Dell Inspiron N5110 — домашний кандидатный узел / home candidate node

> **Статус:** inventory only (2026-09-11). Железо **пока неисправно**, в прод не введено.  
> **Источник:** наклейка днища (фото владельца). Живой `lscpu`/`lspci` — после ремонта.

## Identification / Идентификация

| Field | Value |
|-------|--------|
| Model | **Dell Inspiron N5110** |
| Dell Model No | `5110-8477` |
| Colour | RED |
| Country | RU |
| Service Tag | `6M60JR1` |
| Express Service Code (label) | `14401053181` |
| Era | ~2011, Sandy Bridge generation |

## Expected class (not live-measured)

Typical N5110 class (confirm after boot):

- CPU: Intel Core i3/i5 2xxx (2C/4T class)
- RAM: DDR3, often 4–8 GB max practical
- GPU: Intel HD 3000 and/or **NVIDIA GT 525M** (Optimus) — **Fermi**, not Immich CUDA 11/12
- Storage: 2.5" HDD era; SSD upgrade recommended if revived
- Network: 100/1000 Ethernet + old Wi‑Fi

## Role in NAS_Jetson_Nano (planned, not active)

| Role | Verdict |
|------|---------|
| Home LAN always-on helper (`192.168.0.0/24`) | ✅ candidate after repair |
| Immich ML **CUDA** (`*-cuda` image) | ❌ no — GPU/driver too old |
| Immich ML **CPU** batch overnight | 🟠 optional experiment only if ROG unavailable |
| Local LLM | ❌ no |
| Primary NAS / Jetson replacement | ❌ no |
| cold storage / restic receive / watchdog | ✅ good fit if disk+PSU stable |

**Suggested LAN IP (reserve, not assigned):** `192.168.0.60/24` — only after live DHCP check and HOST-style note; do not conflict with Jetson `.50`, router `.1`, mesh plans.

## Relation to other nodes

| Node | Place | Role |
|------|-------|------|
| Jetson `.50` | home | SoR Immich/NC |
| ROG Strix G17 | home (when on) | free Immich ML CUDA pilot |
| Vostro `.153` | **corp** | bastion + work services — not this laptop |
| **N5110** | **home** (planned) | old-hardware helper |
| Cloud.ru | edge | paid ML / S3 later |

## Commissioning gate (before any service)

1. POST / charge / no thermal shutdown  
2. Live Linux (Mint/Debian) + SSH on home LAN  
3. Record: CPU model, RAM, `lspci -nn \| grep -iE 'vga\|3d'`, disk health  
4. Update this doc + `docs/19_NETWORK_INVENTORY.md` with **measured** facts  
5. One small role only (e.g. watchdog ping Jetson) — not Immich CUDA  

## Safety

- No secrets on this host until disk wiped/reinstalled.  
- Do not expose ports to WAN.  
- Do not touch Amnezia/VPS for this node until role is approved.  

## Related

- Immich ROG pilot: `docs/plans/IMMICH_ML_ROG_FREE_PILOT.md`  
- Old hardware positioning: `docs/plans/OLD_HARDWARE_PROJECT_PROMOTION_PLAN.md`  
- Network inventory: `docs/19_NETWORK_INVENTORY.md`  
