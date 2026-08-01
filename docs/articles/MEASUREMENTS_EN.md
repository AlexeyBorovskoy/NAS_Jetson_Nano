# MEASUREMENTS — verified benchmarks & audit (v3 session)

> All figures collected **read-only** on **2026-08-01** via an SSH jump (`VPS → Jetson`), unless noted.
> Secrets masked. Privileged reads used a sudo helper that sources the password from the project `.env`
> on the device (never transmitted or printed). Load test = 4× `yes` on all cores (synthetic CPU saturation).

## 0. Status table

| Block | Item | Status | Value |
|---|---|---|---|
| A | Board power (idle / load) | ✅ measured | **2.30 W idle**, **4.17 W load** (INA3221 rail0) |
| B | Immich assets | ✅ measured | 7,098 = 6,686 photos + 412 videos; 8.9 GB on disk |
| B | Nextcloud users / data | ✅ measured | 5 users; data 254 MB, DBs 349 MB (both on SSD) |
| B | Contacts / calendars | ⬜ pending | not captured |
| C | API endpoints | ✅ measured | 21 (15 GET + 6 POST) |
| D | Tunnel latency | ✅ measured | +~190 ms vs local |
| D | Tunnel throughput (100 MB) | ⬜ pending | needs a test file + run |
| E | Stability | ✅ measured | 0 OOM / 0 container restarts in 30 d; uptime 23 d |
| E | Backups | ⚠️ measured — ISSUE | newest dump 2026-07-24 (8 days stale) |
| F1 | External exposure | ✅ resolved | services publicly exposed on VPS (rule #4 violated) |
| F2 | Immich architecture | ✅ resolved | one `:release` image run twice (legacy split) |
| F3 | Memory overcommit | ✅ measured | limits ≈ 94% of RAM + unbounded samba |
| F4 | Memory pressure | ✅ measured | swapped (~714 MB) but not thrashing at idle |
| G | Disk `fio` | ⬜ pending | authorized; run in a window |
| G | SSD temperature | 🔴 blocked | SAT passthrough gives no temp attribute |

## A. Power (INA3221 rail0 = total board input; sysfs, root; 1 s interval)
- **Idle:** 120 samples → **avg 2.30 W** (2,305 mW), min 1.33 W, max 4.36 W.
- **Load (4× `yes`, all 4 cores, MAXN):** 25 samples → **avg 4.17 W**, min 4.13 W, max 4.32 W.
- The external USB SSD draw is **not** included (separate rail). Adding a typical SATA-SSD-in-USB-enclosure
  (~1–2.5 W) → rough full-build estimate **~3.5–4.5 W idle**, **~5.5–6.5 W under CPU load**.
- Board-only energy ≈ **~20 kWh/year** at ~2.3 W average idle (the device is idle most of the time).
- `tegrastats` on this L4T build does **not** print POM_5V_IN; values read from
  `…/6-0040/iio:device0/in_power0_input`.

## B. Content
- Immich: **6,686 photos + 412 videos = 7,098 assets** (`select type,count(*) from asset`), **8.9 GB** on `/mnt/storage/immich`.
- Nextcloud: **5 users** (`occ user:list`); user data **254 MB**, Postgres DBs **349 MB** — both on the SSD (root `du`).
- Storage total: **9.6 GB used / 229 GB** (4%).
- vs the published article (~6,710 photos): now **6,686 photos** — consistent.
- Contacts / calendars counts: `pending`.

## C. API — 21 endpoints
- 15 GET + 6 POST across 9 routers (actions, auth, health, logs, photos, storage, system, talk, talk_bot).
- Verified two ways: `grep '@router.*'` on the source AND `/openapi.json` — **both = 21**. (Article said "20".)

## D. Latency & cost of the tunnel (`curl -w`, 3 samples)
| Path | Nextcloud `/status.php` | Immich `/api/server/ping` |
|---|---|---|
| On the Jetson (no tunnel) | ~45 ms | ~7 ms |
| Via reverse tunnel (VPS → Jetson) | ~230 ms | ~220 ms |
| Public HTTPS on VPS `:8443` (incl. TLS) | ~260 ms | — |
- **Tunnel cost ≈ +185–210 ms round-trip**, dominated by the geographic RTT to the VPS (Vienna), not the Jetson.
- Throughput (100 MB WebDAV up/down, LAN vs tunnel): `pending`.

## E. Stability (30-day window, `journalctl` / `docker inspect`)
- Uptime **23 days**; **0 OOM events** (`journalctl -k`); **all 13 containers RestartCount = 0**.
- `nasa-tunnel` service restarts: **6**; ~**160** autossh reconnect/disconnect log lines (self-healing tunnel).
- `nasa-ssd-recovery` fired **1×**; `nasa-usb-monitor` **2×**; `nasa-usb-watchdog` timer ~11,209 checks (cadence, not failures).
- **⚠️ Backups appear STALE:** newest dump `*_20260724_*` — **8 days old** on 2026-08-01. 14 files = a 7-day rotation
  spanning Jul 18–24, then nothing. The timer shows ~daily starts, so writes seem to have stopped ~Jul 24. **Needs investigation.**
- Restore tested: no evidence → `pending`.
- The article's "three USB failures" is consistent with the recovery/monitor counts + the incident logs.

## F. Contradictions resolved
1. **External exposure (rule #4).** On the **VPS**, `ss -tuln` shows public `0.0.0.0` listeners: Nextcloud (8080/8443),
   Immich (2283/2443), LLM Gateway (8090/9443), **nasa-api (8099)**, Beszel (8091), plus 22/443. So services **are**
   reachable from the internet via the VPS. Nextcloud/Immich have app-level login, but **nasa-api :8099 and the LLM
   gateway :8090 being publicly exposed is a real gap.** The "nothing exposed beyond the tunnel" claim is **false**;
   the reader criticism about open ports is **correct**. (The Jetson itself only listens on the LAN.)
2. **Immich architecture.** `homecloud_immich_server` and `homecloud_immich_microservices` run the **same image**
   `ghcr.io/immich-app/immich-server:release`, differing only by command (`start.sh` vs `start.sh microservices`).
   So it is Immich **2.7.5 deployed with the legacy two-container topology** (a separate microservices worker that
   newer Immich folds into the server). The `:release` tag is **unpinned** — a reproducibility/security concern.
3. **Memory overcommit.** Sum of explicit `mem_limit` ≈ **3,712 MB of 3,964 MB physical (~94%)**, and
   `homecloud_samba` has **no limit** (`HostConfig.Memory=0`; the "3.87 GiB" in `docker stats` is the total-RAM
   display, not a cap). Limits + unbounded samba exceed physical RAM. Actual live usage is ~1.7 GB, so it works, but
   the configuration overcommits.
4. **Memory pressure.** No PSI on this kernel (`/proc/pressure` absent, L4T 4.9). zram: 4×495 MB, ~2.4× compression
   (~465 MB data → ~190 MB). `vmstat` at idle: **si/so = 0** (not thrashing), ~514 MB free, 714 MB parked in swap.
   Verdict: the system has swapped but is **stable at idle**; there is **little headroom** for a heavy new workload
   on the Jetson (reinforcing the case for offloading ML to the Vostro node).

## G. Disk & thermals
- `fio` on `/mnt/storage`: **pending** (authorized; run in a low-traffic window; compare to the historical ~250 MB/s).
- **SSD temperature: blocked** — `smartctl -d sat -A /dev/sda` returns no temperature attribute (JMS583 SAT
  passthrough is limited; smartmontools 6.6 is old). The comment-thread "overheating" claim stays **unverifiable by
  on-board sensors**. SoC temps are low (CPU 43.5 °C idle).
- Power mode **MAXN**; throttling inconclusive (30 `dmesg` lines match `throttl|soctherm`, likely boot-time init;
  no throttling seen during the 25 s load test, temps stayed low).
