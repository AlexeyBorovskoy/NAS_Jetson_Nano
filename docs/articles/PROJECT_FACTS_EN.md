# PROJECT FACTS — verified source of truth (for the English article)
# Проверенная фактура для англоязычной статьи

> 🇬🇧 Attach this file to the web session together with `docs/prompts/prompt-project-audit-v2.md`.
> Every figure below was collected **read-only** from the live system on **2026-08-01** via an SSH jump
> (`VPS → Jetson`). Secrets are masked. Items marked `TODO` still need a measurement — do not invent them.
>
> 🇷🇺 Приложи этот файл в web-сессию вместе с промтом v2. Все числа сняты read-only с живой системы 2026-08-01.
> Секреты замаскированы. `TODO` = ещё не измерено, не выдумывать.

## 0. Naming / attribution caveat
- Repo name: **NAS_Jetson_Nano**. Live device still runs the **pre-rename** layout: repo dir `~/nasa`,
  containers `homecloud_*`, systemd units `nasa-*`. Attribute live facts to those real names.

## 1. Platform (Jetson) — `uname`, `nv_tegra_release`, `nvpmodel`, `free`, `tegrastats` @ 2026-08-01
| Fact | Value | Source |
|---|---|---|
| Board | NVIDIA Jetson Nano Developer Kit, 4 GB, ARM64, Maxwell 128-core GPU | label / `cat /proc/device-tree/model` |
| OS / L4T | Ubuntu 18.04, **L4T R32.7.1** (JetPack 4.6.x) — **EOL, no upgrade path** | `/etc/nv_tegra_release` |
| CUDA | **10.2.300** (too old for modern Immich ML GPU images, which need CUDA 11/12) | `/usr/local/cuda/version.txt` |
| Power mode | **MAXN** (unrestricted; not the 5 W cap) | `nvpmodel -q` |
| Uptime | **23 days** (continuous) | `uptime` |
| RAM | 3.9 GB total · **~2.0 GB used** · ~531 MB free · ~1.4 GB available | `free -h` / `tegrastats` (RAM 2193/3964MB) |
| Swap (zram) | 4× zram ≈ **2.0 GB total**, ~712 MB used (no disk swap) | `tegrastats` (SWAP 712/1982MB) |
| GPU load | **0%** (idle — GPU is unused; this is the core "GPU sits idle" point) | `tegrastats` (GR3D_FREQ 0%) |
| Temps (idle) | CPU 43.5 °C · GPU 42 °C · PMIC 50 °C | `tegrastats` / thermal zones |
| Power draw (W) | `TODO: not measured` — this L4T `tegrastats` build did not print POM_5V_IN; needs a wattmeter or a build that exposes the INA3221 rail | — |

## 2. Storage — `lsblk`, `df`, quirks @ 2026-08-01
| Fact | Value | Source |
|---|---|---|
| Data disk | USB SSD in a **JMS583** enclosure (152d:a583), USB 3.0 (5 Gbps) → `/dev/sda1`, **229 GB ext4** | `lsblk` / `lsusb` |
| Data usage | **9.6 GB used of 229 GB (5%)**, mounted `rw,noatime` at `/mnt/storage` | `df -h /mnt/storage` |
| System disk | microSD 64 GB → `/`, **23 GB used of 60 GB (40%)** | `df -h /` |
| USB mode | **UAS disabled** via `usb-storage.quirks=...,152d:a583:u` + `usbcore.autosuspend=-1` (kernel) → usb-storage BOT | `/proc/cmdline` |
| Sequential write | **~250 MB/s** (prior measurement, CLAUDE.md) — `TODO: re-verify with fio` | historical |

## 3. Services — 13 containers, all `homecloud_*`, `docker stats --no-stream` @ 2026-08-01
| Container | Mem used / limit | App version |
|---|---|---|
| homecloud_nextcloud | 184 MiB / 512 MiB | **Nextcloud 33.0.4** (`occ status`) |
| homecloud_nextcloud_db | 53 MiB / 256 MiB | PostgreSQL |
| homecloud_nextcloud_redis | 10.5 MiB / 64 MiB | Redis 7 |
| homecloud_immich_server | 421 MiB / 1 GiB | **Immich 2.7.5** (`/api/server/version`) |
| homecloud_immich_microservices | 366 MiB / 512 MiB | Immich |
| homecloud_immich_db | 106 MiB / 384 MiB | PostgreSQL + pgvecto-rs |
| homecloud_immich_redis | 21.5 MiB / 64 MiB | Redis 7 |
| homecloud_llm_gateway | 50 MiB / 256 MiB | FastAPI (DeepSeek shim) |
| homecloud_nasa_api | 55 MiB / 128 MiB | FastAPI admin API v0.6.0 |
| homecloud_samba | 59 MiB / 3.87 GiB | Samba (SMB2+) |
| homecloud_netdata | 225 MiB / 256 MiB | Netdata |
| homecloud_uptime_kuma | 124 MiB / 128 MiB | Uptime Kuma |
| homecloud_portainer | 26 MiB / 128 MiB | Portainer CE |
| **Total container RAM** | **~1.7 GB** | sum of above |

- **Immich ML: DISABLED** — `IMMICH_DISABLE_MACHINE_LEARNING=true`, no `immich-machine-learning` container exists.
  This is the single biggest reader criticism of Part 1.
- **API endpoints: 21** (15 GET + 6 POST) across 9 router modules (actions, auth, health, logs, photos, storage,
  system, talk, talk_bot). Verified two ways on 2026-08-01: source grep of `@router.*` AND `/openapi.json` — both = 21.
  (Part 1 said "20 operations"; the live API v0.6.0 has 21.)
- **Immich library: 7,098 assets = 6,686 photos + 412 videos** (`select type,count(*) from asset`, 2026-08-01;
  DB role `immich`). The Part 1 draft cited ~6,710 photos; the live count is now 7,098.
- **Nextcloud users: 5** (`occ user:list`; the "family" group). Files count: `TODO`.

## 4. systemd units (device, `nasa-*`)
`nasa-tunnel` (autossh reverse SSH), `nasa-usb-preboot`, `nasa-usb-monitor`, `nasa-usb-watchdog.timer`,
`nasa-ssd-recovery`, `nasa-jms583-health.timer`, `nasa-backup.timer`, `nasa-daily-report-telegram.timer`.
- Tunnel restarts in 30 days: `TODO: journalctl`.
- Backup duration / size / last success / restore-tested: `TODO`.

## 5. Network / external access
- Jetson LAN `192.168.0.50`, behind **CGNAT**. External access only via **autossh reverse tunnel** to VPS `<VPS_IP>`.
- VPS nginx (Docker, host network) port map → tunnel → Jetson: `:8080/:8443` Nextcloud · `:2283/:2443` Immich ·
  `:8090/:9443` LLM Gateway · `:10022` SSH. **Self-signed TLS (10-year)**.
- Samba is LAN-only (iptables 192.168.0.0/24 → 445/139). Nothing exposed beyond the tunnel: `TODO: confirm ss -tulpn`.

### 5a. Latency & the cost of the tunnel (`curl -w time_total`, 3 samples each, 2026-08-01)
| Path | Nextcloud (`/status.php`) | Immich (`/api/server/ping`) |
|---|---|---|
| On the Jetson (no tunnel) | **~45 ms** | **~7 ms** |
| Via reverse tunnel (VPS → Jetson) | **~230 ms** (140–290) | **~220 ms** (210–230) |
| Public HTTPS on VPS `:8443` (incl. TLS) | **~260 ms** (250–280) | — |
- **Cost of the tunnel ≈ +185–210 ms round-trip**, dominated by the geographic RTT to the VPS (Vienna) — not by the
  Jetson. Local service latency itself is low (Immich 7 ms, Nextcloud 45 ms). Good honest number for the article.

## 6. Step 2 — second node (Dell Vostro 15 3568), confirmed by Dell service tag `H7YB9L2`
| Fact | Value |
|---|---|
| Model | Dell **Vostro 15 3568** (budget 3000-series), MFG 2018 |
| CPU | Intel **Core i3-6006U** — Skylake, **2 cores / 4 threads**, 2.0 GHz, **no turbo** |
| RAM | **4 GB** DDR4-2400 (1 stick; 1 free slot, max 16 GB) |
| GPU | AMD **Radeon 520** 2 GB + Intel HD 520 — **no CUDA** (GPU-accelerated Immich ML impossible) |
| Storage | **1 TB HDD 5400 rpm** (not an SSD) |
| Planned role | **CPU-only** Immich ML node (4 GB dedicated to ML alone) + **restic backup target** (1 TB HDD); IP `192.168.0.60` |
| Honest limit | 4 GB (same as the Jetson) + 2 cores + no CUDA + slow HDD → ML works only slowly, backlog over nights |

## 7. The honest angle for the English article
- "Old hardware should live": the whole project uses only idle gear (a forgotten Jetson, a son's USB board, and
  now a 2016 budget laptop). No purchases.
- Reader feedback from Part 1 (Immich without ML) was **correct**; the fix is an offload node, not a GPU purchase —
  but the offload node is honestly weak (i3-6006U, 4 GB, no CUDA). That honesty is the story, not a spec flex.
- Credible measurements still missing (power, disk fio, tunnel cost, ML throughput) — see the `TODO`s; the article
  should either include them or state clearly they are pending.

## 8. Do-not-do reminders for the writer
- Do NOT re-open "rename the project" (already done: NASA → NAS_Jetson_Nano).
- Do NOT present Part 1 draft numbers as published figures without reconciling.
- Do NOT claim GPU acceleration anywhere (neither Jetson CUDA 10.2 nor Vostro AMD GPU supports it).
- Do NOT expose `<VPS_IP>`, Telegram tokens, family names, or the Talk room ID.
