# OBS-1 deployment and acceptance

October 21 validation: 301 Linux tests, full preflight and metrics passed.
Windows: 296 tests, 5 platform skips. ShellCheck is unavailable locally.
Not installed on Jetson: SSH proxy unavailable; sudo still needs verification.

Final review fixed startup without SSD: its `ReadWritePaths` directory is optional,
while SD state remains required, as supported by
[systemd 237](https://github.com/systemd/systemd/blob/v237/man/systemd.exec.xml#L821-L827).
Keep the HDD mountpoint directory present even when its disk is disconnected.

Updated October 20, 2026. **Not installed on Jetson.** Local tests are not device
acceptance. Installation requires working sudo/root; password discovery or sudo
bypass is outside this procedure. RU: `DEPLOY_OBS1_BLACKBOX.ru.md`.

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

After package and capacity verification:

```sh
sudo systemctl enable --now nas_jetson_nano-blackbox-boot.service
sudo systemctl enable --now nas_jetson_nano-blackbox.service
sudo systemctl enable --now nas_jetson_nano-blackbox-archive.timer
systemctl show nas_jetson_nano-blackbox.service -p ActiveState -p ActiveEnterTimestamp
stat scripts/monitoring/nas_jetson_nano-blackbox.py services/blackbox/blackbox/collector.py
```

Active-enter time must follow executable-code updates; restart deliberately
after updates and check import/process errors too. A timestamp alone does not
prove which modules were loaded. Initial installation cannot reconstruct missing
historical evidence. Backups are under `.agent-work/archives/blackbox-install-*`.

## Acceptance

Observe one hour: current-boot heartbeat, growing records, no collector restarts,
measured CPU/RSS and SD/SSD writes. Check snapshot/boot-catalog association and
retry idempotence. `sudo nas-why --boot -1 --short` must produce at most six
lines and report unknown when evidence is unavailable; first installation may
have no previous boot record.

Test archiving on a separate synthetic week and separate HDD test directory,
including hash verification and preserving SSD sources on failure/busy HDD.
A controlled three-minute collector stop should cause one OPS-1 alert, with
an hourly cooldown. A harmless container restart checks its event/redacted tail.
These production-affecting actions are separate controlled steps. Tune thresholds
after a week; validate a real crash explanation when an actual event occurs,
without inducing a power loss.

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
