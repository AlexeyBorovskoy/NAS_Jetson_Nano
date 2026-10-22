# OBS-1 deployment and acceptance

Status October 22, 2026: **installed, hour acceptance passed; longer-term budget open**.
October 21 14:11:59–15:11:59 UTC: CPU 2.604%, VmHWM 20.875 MiB, cgroup peak
28.0195 MiB, heartbeat ≤11 s; 3491 fast / 59 minute / 82 process snapshots;
PID 4991, no restarts. Observer succeeded: 61 samples over 3600.058 s.
The same process was running October 22 morning, current RSS 24.06 MiB, but
VmHWM **43.89 MiB** exceeded the 40 MiB target; cgroup peak **64 MiB**. Process
write_bytes **632,123,392 bytes** over 16 h 37 min, file tree **45,500,462 bytes**:
the SSD ≤60 MB/day budget remains unverified. These metrics differ; physical
NAND writes and the peak cause are unknown. Next block: memory/writes; the
accepted hour does not establish the longer-term budget.
Zero normal-operation SD writes are also unverified; `fallback=0` does not measure that.
Runtime source is locally committed as `2f4edaa`; all 39 installed source hashes
are checked separately. Device Git HEAD was preserved with its prior edits;
no `git pull`/checkout was used. The owner explicitly authorized sudo.

Live acceptance found quadratic long-log redaction and oversized read batches,
then sleep-after-work sampling drift. Completeness checks also found missing
process snapshots: a guarded `snapshot(None, ...)` TypeError prevented baseline
updates. These issues are fixed, and actual process/power/temperature rows now
grow. Active state or heartbeat alone does not prove observation completeness.

Full preflight and metrics ratchet pass without exceptions; the sole full-run
warning is unavailable local ShellCheck. Windows blackbox: 314 passed, 5 skipped.
Linux blackbox/container-watchdog: 329 passed before the final one-line fix,
followed by 16 targeted process tests. Actual Python 3.6.9 / SQLite 3.22 passed
32 synthetic assertions. All three databases passed read-only quick checks;
current boot/snapshot linkage and four installed units were verified. Hour
acceptance also checks distinct process snapshots and reported memory peaks.

Boot service is enabled and successfully exited. Isolated synthetic SSD→HDD
archive, immutable retry and copy-failure checks passed before archive-timer
activation; scheduled invocation succeeded October 22 05:30 UTC; next trigger is October 23 05:30 UTC.
Service success alone does not prove an archive was created when no week was eligible. First previous-boot diagnosis
honestly returns unknown because pre-install history is absent. Reboot, power
interruption and actual delivery of the new D2 section were not induced;
stale-heartbeat/cooldown checks were synthetic without sending messages.
Daily write volume and thresholds need subsequent observation.

Startup without SSD uses an optional SSD `ReadWritePaths` entry; SD state remains
required, as supported by
[systemd 237](https://github.com/systemd/systemd/blob/v237/man/systemd.exec.xml#L821-L827).
Keep the HDD mountpoint directory present when disconnected.
RU: `DEPLOY_OBS1_BLACKBOX.ru.md`.

## Change and purpose

`services/blackbox/`, monitoring entrypoints/helpers and four blackbox systemd
units collect power/memory/process/container evidence. Boot snapshots associate
previous heartbeats with newly recovered pstore/journal. `nas-why` reports
evidence with confidence, D2 adds its short output, and OPS-1 detects stale
heartbeats. This does not promise a certain cause for every failure.

The installer saves previous units/CLI, verifies the units and reloads systemd.
It **never enables or starts services**. Failed installation restores the saved
files; directories and rollback copies remain. Unmanaged CLI files, symlink
targets and directories in place of unit files are rejected.

## Prerequisites and installation

Check target Git status/commit, preserve manual edits, prior units, timers,
crontab and aggregate free-space information. Do not pull over device edits or
lose the previous source files: before transferring the package, save commit,
local diffs and `scripts/monitoring/nas_jetson_nano-boot-alert.py`,
`nas_jetson_nano-container-watchdog.py`, `blackbox_alerts.py` (if present) under
private `.agent-work/archives/obs1-source-before-<UTC>/`; record absent paths.
Use this source backup for rollback, removing a new helper only when its prior
absence was recorded. Never
print environment secrets/family logs. Transfer only a reviewed package and
verify its diff/hashes. Validate `/etc/nas-layout.env`, the real SSD mount,
group `adm`, Python 3.6, systemd 237 and root access to INA3221 channels.
Missing readings are unknown, never zero power. Run full preflight first:

```sh
bash scripts/quality/preflight.sh
bash scripts/monitoring/install_blackbox.sh --check
sudo bash scripts/monitoring/install_blackbox.sh --apply
```

Linux verification is required: Windows skips three colon-containing sysfs
fixtures and may skip symlink cases. Syntax compatibility is not a target-host
test. The default roots are `/mnt/storage/blackbox`,
`/var/lib/nas-blackbox/fallback` and `/mnt/hdd2tb/backups/blackbox`.
Custom roots require coordinated configuration, unit `ReadWritePaths` and
OPS-1 settings. Never write beneath an unmounted SSD. The installer does not
touch HDD directories; the isolated archive worker creates them after checking
the real mount. Keep runtime observations local, out of external model inputs.

After package and capacity verification, enable boot and collector first:

```sh
sudo systemctl enable --now nas_jetson_nano-blackbox-boot.service
sudo systemctl enable --now nas_jetson_nano-blackbox.service
systemctl show nas_jetson_nano-blackbox.service -p ActiveState -p ActiveEnterTimestamp
stat scripts/monitoring/nas_jetson_nano-blackbox.py services/blackbox/blackbox/collector.py
```

Active-enter time must follow executable-code updates; restart deliberately
after updates and check import/process errors too. A timestamp alone does not
prove which modules were loaded. Initial installation cannot reconstruct missing
historical evidence. Backups are under `.agent-work/archives/blackbox-install-*`.
Enable the archive timer only after the isolated synthetic archive acceptance
passes:

```sh
sudo systemctl enable --now nas_jetson_nano-blackbox-archive.timer
```

## Acceptance

The October 21 14:11:59–15:11:59 UTC hour passed every criterion below
(`accepted=true`, observer exit 0), after all 32 target smoke assertions. Earlier
13:37/14:01 runs were interrupted and do not count. The October 22 overnight
snapshot exceeded target VmHWM and showed substantial process writes;
longer-term budget work remains open. For a repeated hour after fixes, require fast-sample delta
greater than 3000, at least 55 minute rows and 55 distinct process snapshots,
mean CPU at most 5%, `/proc` VmHWM at most 40 MiB, cgroup peak at most 64 MiB,
unchanged PID/restart count and a current-boot heartbeat no older than 120 s.
Record a result only after all thresholds pass across a complete hour. A recent
read-only quick check already found the three databases healthy and the current
boot/snapshot association valid. Do not induce a reboot or power loss for this
acceptance. The first
`sudo nas-why --boot -1 --short` result was `unknown` because historical
evidence was absent; it is not a root-cause diagnosis.

The isolated synthetic archive acceptance already passed: separate SSD/HDD test
destinations, hash and manifest verification, immutable retry and source
preservation on copy failure. It used synthetic data only; production records
were not archived by this test. Do not induce a collector stop, reboot, power
loss or notification for this acceptance, and do not restart family containers.
No such field event is claimed as verified. Tune thresholds after a week and
assess a real crash only if one naturally occurs.

The existing watchdog hook, HDD guard and SMART monitoring were preserved.
Source/system backups remain available for rollback.

Periodic log reads are limited to one container and 16 KiB per iteration. The
pending queue has at most 200 containers and is not reset on the next due time.
Initial-backlog and oversized-record omissions have explicit gap markers and
byte counters. Event tails are a separate path: at most 200 lines / 1 MiB read,
with at most 16 KiB retained after redaction.

All archive/runtime CLI HDD operations use isolated workers. Parents have bounded
poll deadlines and do not block while reaping D-state. Live-worker markers prevent
process accumulation. Fallback size is a steady-state target: WAL/VACUUM/atomic
replacement may need temporary extra space. An unreclaimable budget stops event/
minute writes; missing observations are not a successful result.

## Rollback

```sh
sudo systemctl disable --now nas_jetson_nano-blackbox-archive.timer
sudo systemctl disable --now nas_jetson_nano-blackbox.service
sudo systemctl disable --now nas_jetson_nano-blackbox-boot.service
```

Keep markers of live D-state workers; inspect PID/starttime through proc rather
than repeatedly spawning workers or restarting mount holders. Restore specific
saved unit/CLI files from the installation backup; remove only new files named
by its `absent`/`cli-absent` manifests, then run `sudo systemctl daemon-reload`.
Restore previous boot-alert/watchdog/helpers from the reviewed package backup.
Preserve observations, logs, archives, Docker volumes, mounts, VPN and originals.
