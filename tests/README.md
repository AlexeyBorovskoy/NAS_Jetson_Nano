# Tests: NAS_Jetson_Nano

This directory contains test scripts for validating the NAS_Jetson_Nano system.

## Directory Structure

```
tests/
  network/
    connectivity_check.sh   -- ping + HTTP check
    port_check.sh           -- TCP port check (nc -vz only)
  service/
    docker_healthcheck.sh   -- Docker container health (read-only)
    nextcloud_smoke.sh      -- Nextcloud /status.php smoke test
    immich_smoke.sh         -- Immich /api/server/ping smoke test
  storage/
    mount_check.sh          -- Mount point and disk usage check
    smart_check.sh          -- Read-only SMART check (sudo required)
    fio_quick_test.sh       -- Safe fio benchmark (requires --confirm)
  backup/
    restore_test.sh         -- Backup validation and rsync dry-run
  android/
    adb_readonly_check.sh   -- Read-only ADB check (no personal data)
  load/
    nextcloud-smoke.js      -- k6 smoke test (5 VU / 2 min)
  goss/
    goss.yaml               -- goss infrastructure tests
  test_healthcheck.sh       -- Quick storage health test
  test_mount.sh             -- Mount test
  test_samba_config.sh      -- Samba config test
```

## Quick Start

```bash
# Network check
tests/network/connectivity_check.sh --host 192.168.0.50

# Port check
tests/network/port_check.sh --host 192.168.0.50 --ports "22,8080,2283,8090"

# Docker health (run on Jetson)
tests/service/docker_healthcheck.sh

# Nextcloud smoke
tests/service/nextcloud_smoke.sh --url http://192.168.0.50:8080

# Immich smoke
tests/service/immich_smoke.sh --url http://192.168.0.50:2283

# Storage mount check (run on Jetson)
tests/storage/mount_check.sh

# SMART check (run on Jetson, requires sudo)
sudo tests/storage/smart_check.sh --device /dev/sda

# Backup validation (run on Jetson)
tests/backup/restore_test.sh \
  --source /mnt/storage/backups/database-dumps \
  --restore-dir /tmp/nas_jetson_nano-restore-test

# k6 load test (manual, install k6 first)
NEXTCLOUD_URL=http://192.168.0.50:8080 k6 run tests/load/nextcloud-smoke.js
```

## Safety Rules

All scripts follow these rules:

1. **No destructive operations** -- no mkfs, fdisk, dd, wipefs
2. **No data deletion** -- never rm -rf on user data directories
3. **No automatic restarts** -- report only, never restart services
4. **Temp files via mktemp** -- not fixed /tmp/name paths
5. **--confirm required** for fio (creates test files)
6. **ADB: read-only only** -- no install/uninstall/personal data pull

## Dependencies

| Script | Required tools |
|---|---|
| connectivity_check.sh | ping, curl |
| port_check.sh | nc (netcat-openbsd) |
| docker_healthcheck.sh | docker |
| nextcloud_smoke.sh | curl |
| immich_smoke.sh | curl |
| mount_check.sh | df, mountpoint, findmnt |
| smart_check.sh | smartctl (smartmontools) |
| fio_quick_test.sh | fio, python3 |
| restore_test.sh | rsync, diff |
| adb_readonly_check.sh | adb |
| nextcloud-smoke.js | k6 |

## Reports

All scripts support `--output <file>` to save Markdown reports to `docs/quality/results/`.
