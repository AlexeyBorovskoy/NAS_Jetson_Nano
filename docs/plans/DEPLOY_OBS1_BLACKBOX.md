# OBS-1 deployment and acceptance

Status October 22, 2026: **installed; two-hour resource acceptance passed; daily SSD budget remains open**.
The installed runtime is the originally accepted commit `b21b81c13e61d5254d7f73c724c6c8ab3e8be307`.
The feature was linearly rebased and integrated/pushed to GitHub `main` and
GitVerse `main`/`master` as `d5984adc2ec8edcaa4f77c26aeaf427b274944a5` on October 22;
five GitHub workflows succeeded. The rebased runtime commit
`32c04a7c3443b6207a8f79490ec247dea1450556` is equivalent to the originally accepted
`b21b81c13e61d5254d7f73c724c6c8ab3e8be307`, which is the version installed on Jetson.
The new local hash does not replace the installed commit. All 39 runtime files plus
one dependency match the original accepted manifest; the manifest was not regenerated.

The two-hour observer completed with `accepted=true`, Result=success / exit 0:
121 samples / 7,200.053 s, CPU 2.5665%, VmHWM peak 22.3008 MiB, cgroup peak
35.9883 MiB, heartbeat age max 11 s; 6,984 fast, 119 minute and 158 process
snapshots were added. PID/restart count stayed unchanged; cgroup `failcnt` delta
was 0. The ≤60 MB/day SSD target remains unverified. Over only these two hours,
process `write_bytes` rose 59,826,176 B and the SSD partition counter 181,403,648 B;
the latter includes other writers, and neither is a NAND-write measurement. Do not
extrapolate these deltas to a day.

A separate 24-hour observer started October 22 at 08:48:22 UTC and targets October
23 around 08:48:22 UTC. Its result and UTC-midnight transition check are pending.
Earlier cgroup peak / `memory.failcnt` observations do not by themselves establish
OOM or a Python leak: cgroup memory includes file cache, and failcnt records limit
hits followed by reclaim. See the [checkpoint](CHECKPOINT_2026-10-20.md) for the
dated cache/RSS snapshot and conditional storage-geometry estimate.

Zero normal-operation SD writes are also unverified; `fallback=0` does not measure that.
Sudo was explicitly authorized.

Live acceptance found quadratic long-log redaction and oversized read batches,
then sleep-after-work sampling drift. Completeness checks also found missing
process snapshots: a guarded `snapshot(None, ...)` TypeError prevented baseline
updates. These issues are fixed, and actual process/power/temperature rows now
grow. Active state or heartbeat alone does not prove observation completeness.

Combined preflight reported 38 regressions. Windows blackbox: 317 passed / 6
skipped; Linux blackbox: 323 passed separately. Twelve Compose configurations
validated without a daemon. ShellCheck and a Docker daemon were unavailable in
the validation environment. Actual Python 3.6.9 / SQLite 3.22 passed 32 synthetic
assertions and a separate lossless 8 MiB `RLIMIT_AS=64 MiB` check. These are
separate checks, not one combined runtime suite. Separately, Cloud validation on
Ubuntu 24.04 x86_64 / Python 3.12.3 passed the Linux blackbox suite 323/323 in
17.12 s (zero skips). This is additional Linux evidence, not the Python 3.6 Jetson
ARM target check. Earlier read-only DB, boot/snapshot and installed-unit checks
remain recorded in the [checkpoint](CHECKPOINT_2026-10-20.md).

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
