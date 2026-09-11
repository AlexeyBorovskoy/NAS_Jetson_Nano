# Checkpoint 2026-09-11 — session end / конец сессии

> Owner shutting down workstation. Snapshot for next agent/session.  
> HEAD at write time: see git log below after commit.

## Git (main)

| Commit | Summary |
|--------|---------|
| `65b7229` | Immich ML ROG free pilot (compose, scripts, runbook, env URL wiring) |
| `79e8833` | Vostro bastion docs (VPS `:10222`, Amnezia untouched) |
| `16f29f2` | Home Wi‑Fi bastion path + inventory |
| `a2aa4c3` | Dell Inspiron N5110 inventory |
| *(this)* | checkpoint file |

Remotes: `origin` GitHub + `gitverse` main/master — keep in sync after this commit.

## Done today (live)

### Immich ML ROG (free, home LAN)
- Files in repo: `docker-compose.immich-ml-rog.yml`, `config/immich-ml-rog.env.example`, start/stop ps1, `IMMICH_ML_ROG_FREE_PILOT.md`
- Jetson compose/env.example: `IMMICH_MACHINE_LEARNING_URL`
- **Not run on device tonight** — runbook ready for home LAN pilot

### Vostro bastion (corp entry from home)
- Already live: `nas-offsite-tunnel.service` → VPS `127.0.0.1:10222`
- Verified: Windows / Jetson → Vostro; `rserver3:22`, gateways `8772/8774`
- Amnezia containers **not** modified
- SSH config: `vostro-bastion`, `jetson-via-vps` (Windows); Jetson key + config.d
- Docs: `VOSTRO_BASTION_HOME_ACCESS.md`, inventory updated
- Home Wi‑Fi **works** for bastion (VPS:22); Amnezia not required for SSH jump

### Inspiron N5110
- Inventory only: ST `6M60JR1`, model `5110-8477` RED — **faulty, not commissioned**
- Role: future home helper; **not** Immich CUDA
- Doc: `INSPIRON_N5110_HOME_NODE.md`

### Coordination board
- **m0126** answered **m0124**: VPS **1.9 GiB / 1 vCPU** — 8B model does **not** fit
- **m0127** fact: N5110 inventory
- Open asks to `nas`: none at checkpoint time
- `work` package: `shared/work/OPEN_ACCESS_FOR_NEIGHBORS.md` (updated 11.09)

## Must not touch
- Amnezia on VPS (`wg set` / container restart)
- Jetson profile `nas_jetson_nano-lan` / `.50`
- Deploy to Jetson without owner word «деплой»

## Open / next (priority)

1. **Home:** Immich ML ROG pilot — firewall `:3003` LAN-only → start script → Jetson `.env` URL → one album  
2. **Cloud.ru S3** L2 still blocked (tenant_id) — owner console  
3. **N5110** — repair then live audit (CPU/RAM/GPU) before any service  
4. Corp resources via bastion — use `vostro-bastion` + SOCKS/`-L` as needed; mutations ASUDD still forbidden (work policy)  
5. Optional: Habr Part 2 after ML pilot evidence  

## Canon entry points
- `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`
- `docs/plans/IMMICH_ML_ROG_FREE_PILOT.md`
- `docs/plans/VOSTRO_BASTION_HOME_ACCESS.md`
- `docs/plans/INSPIRON_N5110_HOME_NODE.md`
- `docs/19_NETWORK_INVENTORY.md`
- Board: `E:\agent_coordination\` · agent `nas`

## Untracked (not committed)
- `research/` — left local; review before add
