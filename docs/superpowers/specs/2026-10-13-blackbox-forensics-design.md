# Jetson "Black Box" (OBS-1) — Specification

[Русский](2026-10-13-blackbox-forensics-design.ru.md) · [Owner goals plan](../../plans/DEVELOPMENT_PLAN_2026-10_OWNER_GOALS.md)

> **Date:** 2026-10-13 · **Status:** the design was approved by the owner piecemeal on 13.10, the specification is under review ·
> **Task:** OBS-1 · **Basis:** the owner's request of 13.10 and the incident analyses (below)

## 1. Why

The owner (13.10): "I want a solution running on the Jetson that writes every single detailed log,
and you could always reconstruct the causes of various abnormal situations" (original: «Хочу, чтобы на Jetson работало решение, которое пишет полностью все подробные логи,
и ты мог всегда восстановить причины различных нештатных ситуаций»).

What has failed us so far (all — from the project's logs):

| Case | What was missing |
|---|---|
| The resets of 17.08 and 18.09 | No way to distinguish a power loss from the PMIC watchdog — recorded as "unknown" |
| The three shutdowns of 29.09–11.10 | We learned the owner had shut it down only by asking the owner |
| The `ntfs-3g` hang of 20.09 | No snapshot of the hung processes and no history of disk operations |
| The Immich microservices restart of 13.10 03:20 | Understood only because the lead was around and reading Docker events at that very minute |
| Disk letters changing after boot on 12.10 | Discovered by chance; there is no snapshot of "which disk has which letter" at boot |

**Success criterion:** for each failure class (section 6), a single `nas-why` command outputs a timeline
and a verdict with a confidence label — or an honest "no data"; verified on mock data and by acceptance on the Jetson (section 9).

## 2. Owner's decisions (13.10)

1. Everything is stored **on the device**, nothing goes outside (neither the VPS nor the workstation).
2. Retention is **tiered:** full detail — the last few days on the SSD, everything else — one year.
3. **Everything on the SSD**; once a week — an archive to the HDD, so that the SSD does not fill up with history.
4. **Approach A:** our own lightweight collector + the `nas-why` command (not an off-the-shelf stack, not Grafana/Loki/Prometheus).
5. **Logs of all containers** — in full, for a year; for the family containers — with Russian text cut out.

## 3. What already exists (measured 13.10) and the facts the design builds on

- systemd journal: `Storage=persistent`, `SystemMaxUse=200M` on the SD — full (212 MB), depth ≈ 25 days (5 boots).
  rsyslog duplicates it into `/var/log` (336 MB on the SD).
- Docker: `json-file` **with no size limit**; per day all containers write ≈ 6.5 MB (Nextcloud 4.2).
  In the API and gateway logs there is **not a single line with Cyrillic** per day (99 % — health checks); speech recognition has 1.
- The INA3221 power sensor (`/sys/bus/i2c/drivers/ina3221x/6-0040/iio:device0`, three channels) is readable
  **only by root**.
- ramoops/pstore: registered in the kernel (`Registered ramoops as persistent store backend`), `/sys/fs/pstore` is empty —
  there was no kernel panic during the previous resets.
- `/dev/watchdog` exists, `RuntimeWatchdogSec` is not configured in systemd.
- Disk letters change between boots (REL-11): the key is `/dev/disk/by-id`, not `sda`/`sdb`.
- Host: Python 3.6.9, SQLite 3.22, systemd 237 (unit rules — `tests/unit/test_systemd237_units.py`).
- Free: SSD ≈ 190 GB, HDD ≈ 396 GB, SD ≈ 33 GB; RAM — ≈ 1 GB in normal mode.

## 4. Composition

```
            ┌───────────────────── nas_jetson_nano-blackbox.service (root, sandboxed) ─────────────────────┐
 sysfs/proc │ fast (1 s) ─► sample          procs (10/60 s) ─► proc_snapshot     heartbeat (10 s, fsync)    │
 Docker API │ events (stream) ─► event (+ container log tail)   logs (60 s) ─► containers/*.log.gz          │
 journald   │ journal (5 min) ─► journal.log              probes (60 s) ─► event (network, mounts)          │
            └───────────────► /mnt/storage/blackbox/hot/<day>/  +  catalog.db  ◄── nas-why ───────────────┘
 boot:      nas_jetson_nano-blackbox-boot.service ─► boots/<boot_id>/ + previous boot verdict ─► D2 alert
 week:      nas_jetson_nano-blackbox-archive.timer ─► /mnt/hdd2tb/backups/blackbox/<year>/blackbox-YYYY-Wnn.tar.xz
```

### 4.1. The collector `nas-blackbox` (one service, one Python 3.6 process, standard library only)

| Loop | Frequency | What it writes |
|---|---|---|
| fast | 1 s | Power: voltage, current, power of the three INA3221 channels; temperatures of all zones; CPU load and frequency; `MemAvailable`, swap, ZRAM; `loadavg`; per disk (by-id key): read/write operations, sectors, busy; `eth0`/`docker0` bytes |
| procs | 60 s; **10 s under anomaly** | Top 10 processes by CPU and by RSS (name, container, command up to 90 characters), **all processes in D-state** with `wchan`. Anomaly: any D-state, or `MemAvailable` < 300 MB, or `load1` > 6, or swap growing > 50 MB/min |
| heartbeat | 10 s | The `heartbeat` file (boot_id, time, last power sample): write to a temporary file + `fsync` + `rename` + `fsync` of the directory |
| events | stream | Docker events via the `/var/run/docker.sock` socket (no separate `docker` process): `die`, `oom`, `kill`, `stop`, `start`, `restart`, `health_status` — with exit code and attributes. On `die`/`oom`/`unhealthy` — the last 200 lines of the container log (with masking, 4.3) |
| logs | 60 s | Tailing the `json-file` files of all containers from a remembered position (inode + offset; rotation and truncation — from the start of the new file). Health checks (`GET /health`, `/healthcheck`, `/status.php` with code 200) — not as lines, but as a counter per minute |
| journal | 5 min | `journalctl --after-cursor=<c> --show-cursor -o short-iso-precise` → append to the day's `journal.log`, the cursor — into `catalog.db` |
| probes | 60 s | Gateway (`ping -c1 -W1`), DNS (resolution with a timeout), VPS tunnel (`nasa-tunnel` active + an established connection to the VPS via `/proc/net/tcp`), Telegram proxy (TCP 172.17.0.1:1080), SSD/HDD mounts (`timeout 5 stat -f`) |
| rollup | 60 s | Per-minute min/avg/max of key values → `catalog.db` |
| guard | 60 min | The "hot" limit on the SSD (section 5.3) |

The HDD mount check runs **only in a separate process with a timeout**, and a new one is not started until the previous one has
returned: a hung `ntfs-3g` keeps a process in D-state forever, and otherwise they would pile up one per minute.
The event "mount not responding since HH:MM" is written once.

### 4.2. Boot-time snapshot `nas-blackbox-boot` (oneshot)

`After=local-fs.target docker.service`, `Wants=` (not `Requires=`) for the SSD mount: if the SSD did not come up, the snapshot
is written to a fallback directory on the SD (5.4). Contents of `boots/<boot_id>/`:
`uname -a`, `/etc/nv_tegra_release`, full `dmesg`, the `PMC reset source` line, `lsblk` with models, serials and UUIDs,
`ls -l /dev/disk/by-id`, `lsusb -t`, `/proc/mounts`, copies of the `/sys/fs/pstore/*` files, the last 300 lines of the previous
boot's journal, `docker ps -a` (names, images, status — **not** `docker inspect`), and the **previous boot verdict** (section 6).

### 4.3. Masking

- **All containers and the journal:** tokens and keys (`token=`, `Authorization:`, `password=`, `api_key`, `Bearer …`,
  strings of the form `<tenant>:<keyId>`) → `<скрыто>` (`<hidden>`); the same patterns as in `scripts/security/check_no_secrets.sh`.
- **Family containers** (`homecloud_nasa_api`, `homecloud_llm_gateway`, `homecloud_stt` — the list is in the config):
  runs of consecutive Russian words of three characters or more → `<текст скрыт>` (`<text hidden>`).
- Never stored: the contents of `.env`, `docker inspect` output, HTTP request bodies.

### 4.4. `nas-why` (command)

```
nas-why --boot -1 [--short]           # how the previous boot ended (--short — for the alert, ≤ 6 lines)
nas-why --since "2026-10-13 03:15" [--until …]
nas-why --container homecloud_immich_microservices [--since …]
```
Reads the "hot" data on the SSD and `catalog.db`; for older days it unpacks the needed days from the HDD archive into
`/mnt/storage/blackbox/tmp/` itself (with a timeout) and deletes them after answering. Output: a timeline (source, time, line) +
verdicts (section 6) with the confidence **fact / probable / unknown**.

### 4.5. Interfaces with what exists

- **D2 alert** (`nas_jetson_nano-boot-alert`): adds the output of `nas-why --boot -1 --short` (timeout 60 s;
  on error — the previous text). The reference to `CLAUDE.md` and the question "did you shut it down yourself?" are removed
  (a leftover from REL-1/REL-10).
- **OPS-1 watchdog:** checks the freshness of `heartbeat` — older than 2 min while the service is running → alert "black box is silent"
  (no more than once an hour).
- Host paths — via `/etc/nas-layout.env` (like `scripts/lib/layout.sh`), with no literal `/home/admin` (SD-2).

## 5. Storage

### 5.1. Layout

```
/mnt/storage/blackbox/                     (SSD)
  hot/<YYYY-MM-DD>/metrics.db              per-second samples of the day (sample, disk_sample)
  hot/<YYYY-MM-DD>/procs.db                process snapshots
  hot/<YYYY-MM-DD>/containers/<name>.log.gz container logs (gzip, appended blocks)
  hot/<YYYY-MM-DD>/journal.log(.xz)        copy of the systemd journal
  boots/<boot_id>/                         boot snapshots (one year)
  catalog.db                               per-minute rollups, events, boots, archives (one year)
  heartbeat                                the last "alive" mark
  staging/, tmp/                           building the archive, unpacking for nas-why
/var/lib/nas-blackbox/fallback/            (SD) only if there is no SSD, ≤ 20 MB
/mnt/hdd2tb/backups/blackbox/<YYYY>/       (HDD) weekly archives + .sha256, one year
```
Days are counted in UTC. The day "closes" at 00:00 UTC: `journal.log` is compressed to `.xz`, the day's files are no longer modified.

### 5.2. Data (SQLite, WAL, batch write every 10 s)

| Table | Where | Fields (brief) |
|---|---|---|
| `sample` | metrics.db | `ts` (PK), `vin_mv`, `vin_ma`, `cpu_mw`, `gpu_mw`, `t_cpu`…`t_pmic` (×10 °C), `cpu_pct`, `freq_mhz`, `mem_avail_mb`, `swap_mb`, `zram_mb`, `load1×100`, `net_rx`, `net_tx` |
| `disk_sample` | metrics.db | `ts`, `disk_id` (by-id), `rios`, `wios`, `rsect`, `wsect`, `busy_ms` |
| `proc_snapshot` | procs.db | `ts`, `pid`, `comm`, `owner`, `cmd`, `state`, `wchan`, `cpu_pct`, `rss_mb` |
| `minute` | catalog.db | `ts`, min/avg/max: `vin_mv`, `cpu_pct`, `mem_avail_mb`, `swap_mb`, `t_cpu`; disk-operation sums; health-check counters per container |
| `event` | catalog.db | `ts`, `source` (docker/probe/kernel/archiver/guard/boot), `kind`, `subject`, `severity`, `detail` (JSON) |
| `boot` | catalog.db | `boot_id`, `start`, `end`, `clean`, `last_heartbeat`, `reset_source`, `pstore`, `verdict`, `confidence` |
| `archive` | catalog.db | `week`, `path`, `sha256`, `first_day`, `last_day`, `created`, `verified` |

Volume estimate: per-second ≈ 20–35 MB/day, processes ≈ 5–10, container and system logs (compressed) ≈ 2 →
"hot" for 14 days ≤ 0.7 GB; `catalog.db` ≈ 200 MB/year; the HDD archive ≈ 50–80 MB/week (≈ 3–4 GB/year).
The figures will be refined by the first week of operation.

### 5.3. Weekly archive to the HDD (`nas-blackbox-archive`, Sunday 05:30 UTC + a daily retry if there is a backlog)

1. The candidate is an ISO week whose last day is older than 7 days; so on the SSD data lives from 7 to 14 days.
2. Does not start if `nas_jetson_nano-immich-hdd-copy`, `nas_jetson_nano-config-backup`, `nasa-backup` or a
   `restic` process is active, or the HDD is not responding (`timeout 5 stat -f`) — postpones until the next day.
3. `tar` + `xz` into `staging/` with `nice`/`ionice -c3`, sha256.
4. The copy to the HDD **as a single file**: `timeout 1800 cp` to a temporary name → `sync` → `rename`; then
   `timeout 600 sha256sum` from the HDD and comparison.
5. Only if they match — delete the week's days from the SSD and record `archive` in `catalog.db`; otherwise — delete nothing,
   event + alert; retry tomorrow.
6. Delete archives older than 365 days from the HDD.
7. **SSD fuse** (every hour, in the collector): "hot" > 1 GB → delete the oldest `metrics.db`
   (per-second), then `procs.db`; **logs and events — never**; event + alert.
8. Two missed weeks in a row → alert "the archive is not going to the HDD".

### 5.4. If there is no SSD

The collector writes to `/var/lib/nas-blackbox/fallback/` on the SD: the boot snapshot, `heartbeat` every 60 s, per-minute rollups,
events; the limit is 20 MB (ring). When the SSD appears — it moves what has accumulated into `catalog.db` and `boots/`.

## 6. Verdict rules

| Class | Signs → verdict |
|---|---|
| Abnormal boot | No clean shutdown in the previous boot. `pstore` present → **fact:** kernel panic (+ excerpt). Before the last `heartbeat`, the 5 V input < 4.75 V or current at the limit → **probable:** power supply. Power steady until the last second → **probable:** sudden power loss or hardware reset (there is no way to tell them apart — so that is what gets written). A "shutdown by command" event (REL-10) present → clean. Before death, D-states / zero I/O / `MemAvailable` < 150 MB were accumulating → **probable:** a hang, then a reset. Always — the `PMC reset source` and the time of the last sign of life |
| Container crashed or restarted | Who: the OPS-1 watchdog (a line in its log within ±2 min), the `restart` policy, `compose up` (a `create` event before `start`). Code: 137 — killed (OOM if flagged), 143 — SIGTERM, otherwise — an application error. The health-check log, the tail of the container log |
| Disk hang | D-state with `wchan` from the `fuse`/`request_wait_answer` family, zero operations on that disk ≥ 60 s, the mount probe did not return |
| Lack of memory | Minimum `MemAvailable`, swap growth, `oom-kill`/`Killed process` in the kernel log, the process with the largest RSS growth |
| Network and tunnel | Which probe failed: gateway → home network; DNS; VPS tunnel → the provider or an address block; proxy → Telegram |
| Overheating | Temperatures at the thresholds, frequency throttling |
| USB and disks | `error -71`, `I/O error`, `uas_eh`, reconnection; a mismatch of "letter ↔ by-id" with the previous boot's snapshot |

Thresholds (4.75 V, 150/300 MB, 60 s) — in the config; 4.75 V = 5 V −5 % (to be refined from the first week's baseline).
No data for the window → **unknown: no data for <interval>** (never a guess).

## 7. Security and budget

- The service runs as root (the power sensor, `/var/lib/docker/containers`, `wchan`), but: `ProtectSystem=strict`,
  `ReadWritePaths=/mnt/storage/blackbox /var/lib/nas-blackbox`, `ProtectHome=read-only`, `NoNewPrivileges=yes`,
  `PrivateTmp=yes`, `MemoryLimit=64M`, `CPUQuota=10%`, `Nice=10`, `IOSchedulingClass=idle`;
  `Type=simple`, `Restart=on-failure`, `StartLimit*` in `[Unit]` (systemd 237).
- Budget: RSS ≤ 40 MB (limit 64), CPU ≤ 5 % on average, writes to the SSD ≤ 60 MB/day, to the SD in normal mode — zero.
- A collector crash affects nothing; its silence is seen by OPS-1 (4.5).
- Files — `root:adm`, `0640`; `nas-why` — as root or a member of `adm`.

## 8. Out of scope

Sending off the device; a web interface; replacing netdata; changing the Docker log driver and `json-file` rotation
(requires a `dockerd` restart — a separate maintenance window); automatic remediation (diagnosis and alert only).

## 9. Testing and acceptance

**Before deployment (in git):** `tests/blackbox/` tests (pytest) on mock data: the INA3221 and thermal-zone sysfs tree,
`/proc/*` (stat, diskstats, meminfo), the Docker event stream, `json-file` files with rotation and truncation, `journalctl`
output with a cursor, masking (tokens; Russian text for the family containers and not for the others), the archiver
(sha256 comparison, refusal while an HDD job is active, deleting nothing on error, the SSD fuse) and **every rule of
section 6 on a synthetic timeline**. Gates: Python 3.6 (`vermin`), the ratchet (new functions ≤ 40 lines, CC ≤ 10),
systemd 237 rules; `tests/blackbox` is added to the service test section of `preflight.sh`.

**Acceptance on the Jetson (on the owner's word):**
1. One hour of operation: RSS ≤ 64 MB, CPU ≤ 10 % (measured with `scripts/quality/cpp1_probe.py`).
2. `docker restart` of a harmless container → `nas-why --container …` names the manual restart, code 143.
3. Stopping the collector for 3 min → the gap in `heartbeat` is visible, OPS-1 has sent an alert.
4. The archiver on a test week → the archive is on the HDD, sha256 matched, the days have left the SSD.
5. The first real abnormal boot → the verdict in the D2 alert.
An artificial power cut — not here, but in the REL-4 trials.

## 10. Deployment and rollback

Deployment: files + units per the runbook, `systemd-analyze verify`, enabling the services, a "the new code is running" check (rule #14).
Rollback: `systemctl disable --now` of the two services and the timer; the previous D2 text from the backup copy. The `/mnt/storage/blackbox`
data is deleted only by the owner's decision.

## 11. Implementers

The lead — the specification, the plan, review, deployment and acceptance. Sonnet — the collector, the boot snapshot, the archiver, `nas-why`.
DeepSeek — tests, English document pairs. Secrets — to nobody.

## 12. Open questions (to be closed during implementation)

1. The INA3221 channel names on this module (expected: `POM_5V_IN`, `POM_5V_GPU`, `POM_5V_CPU`) — read as root.
2. Whether `admin` is a member of the `adm` group (otherwise `nas-why` via sudo).
3. The power threshold — from the first week's baseline.
