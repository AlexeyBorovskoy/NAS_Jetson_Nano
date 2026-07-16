# Reliability Audit 2026-06-23 / Аудит надёжности 2026-06-23

> 🇬🇧 Live reliability audit through VPS reverse SSH tunnel after 250 GB SSD recovery.
> 🇷🇺 Живой аудит надёжности через VPS reverse SSH tunnel после восстановления 250 GB SSD.

## 1. Scope

Live audit through the VPS reverse SSH tunnel after the 250 GB SSD was
reconnected. Goal: identify reliability risks that prevent automatic recovery
after USB reconnects, container crashes, or power loss.

No destructive storage operations were performed during this audit.

## 2. Live Findings

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| R-01 | Critical | Storage | SSD is visible again as Realtek RTL9210B-CG `/dev/sda1`, mounted at `/mnt/storage`, stayed `rw` through controlled Nextcloud start, and remounted automatically after reboot. Prior `error -71`/ext4 errors still make the USB chain a hardware risk. | Open / reboot verified / monitored |
| R-02 | Critical | Nextcloud | HTTP 503 was caused by the storage remounting read-only during the USB incident. Step 2 review found `.ncdata`, config, data ownership and DB state consistent. Controlled start and reboot autorecovery succeeded: `status.php` HTTP 200, container healthy. | Fixed live / reboot verified |
| R-03 | High | Boot ordering | Docker can start before `/mnt/storage` is safely mounted, which can create/write bind-mount data under a plain microSD directory after power loss. The 2026-06-23 reboot test came back clean, but the guard remains required for future drift protection. | Mitigation added / reboot verified |
| R-04 | High | Runtime drift | Jetson `~/nas_jetson_nano` was behind `origin/main` and had live changes. It is now clean at `2272679`; the pre-sync live diff is preserved as `stash@{0}`. | Fixed live + repo |
| R-05 | Medium | Reporting | Daily report and nas_jetson_nano-api expected old compose-generated container names, causing false `missing` warnings. | Fixed in repo |
| R-06 | Medium | Restart policy | `docker-compose.stage1.yml`, Samba and VPS nginx still used `restart: unless-stopped` in repo templates. | Fixed in repo |
| R-07 | Medium | Failed units | `jetson-nas-health.service` and `nas_jetson_nano-backup.service` were updated and rerun successfully; `systemctl --failed` reports zero failed units. | Fixed live + repo |
| R-08 | Medium | Sudo access | Sudo was available through an existing private runtime secret; no password value was committed or documented. | Resolved for this recovery |

## 3. Evidence Snapshot

```text
Tunnel: VPS 127.0.0.1:10022 -> Jetson SSH OK
SSD: /dev/sda1 ext4 label=nas_jetson_nano-storage mounted rw,noatime at /mnt/storage
Disk: 229G total, 525M used, 217G free
e2fsck: e2fsck -f -n returned 0, no repairs required
Preflight: sudo storage_preflight.sh returned errors=0 warnings=0
Nextcloud: controlled start completed; restart=always, running, healthy
Nextcloud review: logs show read-only data-dir writes failed; current mount is rw
Nextcloud data: `.ncdata` present, data dir 33:33 mode 750, no ownership drift
Nextcloud DB: pg_isready OK; users=1, filecache=76, file_locks=0
Nextcloud HTTP: local `/status.php` 200, VPS `/status.php` 200, root 302
Immich: HTTP 200
LLM Gateway: HTTP 200
nas_jetson_nano-api: HTTP 200
Reboot/autorecovery: boot id changed 56addc55 -> 13f68009; tunnel, storage,
  containers and HTTP endpoints recovered automatically
Backup: fresh nextcloud and immich DB dumps created at 2026-06-23 09:32 UTC
Failed units: 0
New kernel storage errors after controlled Nextcloud start/reboot: none observed
Post-reboot health timer: jetson-nas-health.service Result=success, issues=0
Jetson checkout: clean at 2272679 after `git pull --ff-only origin main`
Pre-sync live diff: preserved as git stash `stash@{0}`
```

## 4. Repo Mitigations Added

- Correct expected container names in:
  - `docker/compose/docker-compose.nas_jetson_nano-api.yml`
  - `services/nas_jetson_nano-api/app/config.py`
  - `scripts/monitoring/nas_jetson_nano-daily-report.sh`
- Daily report now checks:
  - real `/mnt/storage` mount source/fstype/options;
  - read-only or microSD-backed storage;
  - Nextcloud `.ncdata` presence when readable;
  - recent kernel storage errors;
  - separate VPS checks for Nextcloud, Immich and LLM Gateway.
- `nas_jetson_nano-backup.service` now has `RequiresMountsFor=/mnt/storage`,
  `ConditionPathIsMountPoint=/mnt/storage`, and `ExecStartPre=mountpoint`.
- `jetson-nas-health.service` now uses `/home/admin/nas_jetson_nano` and also requires
  `/mnt/storage` to be a mountpoint.
- Optional strict Docker boot guard:
  - `systemd/docker.service.d/10-nas_jetson_nano-storage.conf`
  - `scripts/storage/install_docker_storage_guard.sh`
- `restart: always` normalized for Samba, Stage 1 compose, and VPS nginx.

## 5. Required Live Recovery Order

Step 1 completed on 2026-06-23: Jetson `~/nas_jetson_nano` was synchronized with
`origin/main` without discarding local changes. The dirty pre-sync state was
saved with `git stash -u` as `stash@{0}: pre-sync live Jetson checkout
2026-06-23 step1`.

Step 2 completed on 2026-06-23: Nextcloud data/app review stayed read-only and
found no data-marker, ownership, config or DB blocker. The observed 503 cause
was the earlier read-only filesystem state:

```text
fopen(/var/www/html/data/data_dir_writability_test_...tmp): Read-only file system
fopen(/var/www/html/data/nextcloud.log): Read-only file system
```

Current safe-state evidence:

```text
/mnt/storage: /dev/sda1 ext4 rw,noatime,data=ordered
/mnt/storage/nextcloud/data: mode 750, owner 33:33
`.ncdata`: present, owner 33:33
writability_test leftovers: 0
non-33 owner/group entries under data dir: 0
DB: accepting connections, file_locks=0
homecloud_nextcloud: exited, restart=no
```

Step 3 completed on 2026-06-23: controlled Nextcloud start succeeded.

```text
storage_preflight.sh: errors=0, warnings=0
docker update --restart=always homecloud_nextcloud: OK
docker start homecloud_nextcloud: OK
local /status.php: HTTP 200, maintenance=false, needsDbUpgrade=false
VPS /status.php: HTTP 200
container: running, healthy
kernel storage errors after start: none observed
```

Step 4 completed on 2026-06-23: reboot/autorecovery test succeeded.

```text
pre-reboot boot_id: 56addc55-6cc9-467d-9008-a830ea1d2d88
post-reboot boot_id: 13f68009-36ca-478f-a29b-4b422a9a6d08
VPS reverse tunnel: recovered automatically
/mnt/storage: /dev/sda1 ext4 rw,noatime,data=ordered
storage_preflight.sh: errors=0, warnings=0
containers: Nextcloud, Immich, LLM Gateway, nas_jetson_nano-api, Samba, Netdata,
  Uptime Kuma and Portainer recovered automatically
HTTP: Nextcloud/Immich/LLM Gateway through VPS returned 200
jetson-nas-health.timer: ran after reboot, SMART OK, issues=0
kernel storage error scan for this boot: no error -71/I/O/read-only failures
```

Path A was completed on 2026-06-23: storage-backed containers were stopped,
`/mnt/storage` was unmounted, `e2fsck -f -n` returned 0, the filesystem was
remounted, preflight passed, and non-Nextcloud services were restarted.

Nextcloud is running again. Keep the controlled start steps below as the rollback
and recovery procedure if another USB storage event occurs.

### Controlled Nextcloud start / restart

Before a future start/restart:

```bash
cd ~/nas_jetson_nano
sudo bash scripts/storage/storage_preflight.sh
sudo journalctl -k --since "10 minutes ago" --no-pager \
  | grep -i -E "ext4|I/O error|error -71|read-only" || true
```

Start/restart and observe:

```bash
docker update --restart=always homecloud_nextcloud
docker start homecloud_nextcloud || docker restart homecloud_nextcloud
docker logs -f --tail=80 homecloud_nextcloud
curl -i http://127.0.0.1:8080/status.php
```

### Optional Path B: Reformat SSD for maximum reliability

Requires explicit confirmation immediately before the destructive command.
Current target, if confirmed:

```text
/dev/disk/by-id/usb-Realtek_RTL9210B-CG_012345679039-0:0-part1
UUID target mount: /mnt/storage
filesystem: ext4
label: nas_jetson_nano-storage
```

Formatting is not currently required by read-only fsck. If chosen anyway, first
export or intentionally discard current data, recreate the storage tree, apply
the Docker storage guard, then start services in this order: DB/Redis, Immich,
LLM Gateway/nas_jetson_nano-api, Samba, Nextcloud last.

## 6. Remaining Design Risks

- A single USB SSD is not a backup. Off-device restic backup is still required.
- Jetson Nano USB power/cable stability remains the most likely hardware weak
  point; repeated `error -71` means cable/enclosure/power should be treated as
  suspect even when the SSD is currently visible.
- Docker restart policy alone is not enough. The 2026-06-23 reboot test passed,
  but boot ordering must keep preventing false bind-mount directories before
  `/mnt/storage` is mounted.
- Nextcloud is recovered, but any new HTTP 503/read-only log line should be
  treated as a storage incident first, not as an application-only problem.
