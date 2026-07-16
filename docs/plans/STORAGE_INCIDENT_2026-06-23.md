# Storage Incident 2026-06-23 / Инцидент с хранилищем 2026-06-23

> 🇬🇧 Post-mortem of the USB SSD outage caused by RTL9210B-CG USB bridge instability.
> 🇷🇺 Разбор инцидента с USB SSD (нестабильность моста RTL9210B-CG).

## 1. Summary

On 2026-06-23 the Jetson Nano was reachable through the VPS reverse SSH tunnel,
but storage-backed services were degraded because the 250 GB USB storage device
was no longer present as a block device.

The failure is below Docker and Nextcloud: the kernel repeatedly fails to
enumerate the USB device on `usb 1-2.1` with `error -71`.

Recovery update 2026-06-23 09:32 UTC: after physical reconnect the SSD appeared
again as Realtek RTL9210B-CG `/dev/sda1`, mounted at `/mnt/storage` with label
`nas_jetson_nano-storage`, passed `e2fsck -f -n` and `storage_preflight.sh`, and fresh DB
dumps were created.

Recovery update 2026-06-23 12:10 UTC: Nextcloud data/app review found no marker,
ownership, config or DB blocker. Controlled start succeeded; `/status.php`
returns HTTP 200 locally and through the VPS, and the container is healthy.

Recovery update 2026-06-23 12:59 UTC: reboot/autorecovery test succeeded.
After reboot the reverse tunnel returned, `/mnt/storage` remounted as
`/dev/sda1`, storage preflight passed, storage-backed containers recovered, VPS
HTTP checks returned 200, and `jetson-nas-health.timer` finished with
`issues: 0`.

## 2. Observed State

| Area | Result |
|---|---|
| Jetson SSH via VPS | OK: `ssh root@193.8.215.130` then `ssh -p 10022 admin@127.0.0.1` |
| `/mnt/storage` on host | Recovered: ext4 mountpoint after reconnect |
| Block devices | Recovered: Realtek RTL9210B-CG `/dev/sda1` visible |
| USB topology | Recovered, but prior `error -71` keeps cable/enclosure/power suspect |
| Nextcloud | Recovered: controlled start OK, `/status.php` HTTP 200 |
| Immich | Responds to `/api/server/ping` |
| LLM Gateway | Responds to `/health` |
| nas_jetson_nano-api | Responds to `/healthcheck` |
| Reboot/autorecovery | Passed: tunnel, storage, containers, HTTP and health timer recovered automatically |
| Backup timer | Recovered: fresh DB dumps created; fail-closed guard remains |

## 3. Kernel Evidence

Important kernel messages:

```text
usb 1-2.1: device descriptor read/64, error -71
usb 1-2-port1: unable to enumerate USB device
blk_update_request: I/O error, dev sda
Aborting journal on device sda1-8
EXT4-fs (sda1): Remounting filesystem read-only
EXT4-fs error (device sdb1): ext4_find_entry
```

Initial successful detection on 2026-06-21:

```text
Realtek RTL9210B-CG
[sda] 488397168 512-byte logical blocks: (250 GB/233 GiB)
sda: sda1
EXT4-fs (sda1): mounted filesystem
```

## 4. Safety Rules

Do not:

- create `.ncdata` manually while `/mnt/storage` is not mounted;
- start Nextcloud or Immich while `storage_preflight.sh` fails;
- run `fsck` against a mounted filesystem;
- run `docker compose down -v`;
- write backups into a false `/mnt/storage` directory on microSD;
- touch Amnezia VPN containers or router firewall/VPN settings.

## 5. Recovery Order

1. Physically stabilize the USB chain: cable, port, powered hub, enclosure,
   power supply.
2. Confirm the disk is visible:

```bash
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,RO
blkid
journalctl -k -n 120 --no-pager
```

3. Run preflight:

```bash
cd ~/nas_jetson_nano
sudo bash scripts/storage/storage_preflight.sh
```

4. Only after the disk is stable and preflight is clean, install/start the mount
   unit and restart storage-backed services.
5. If Nextcloud returns HTTP 503 again after an ext4/read-only event, treat it as
   a storage incident first. Do not create `.ncdata` manually as a shortcut.

## 6. Follow-Up Changes

- `scripts/backup/backup_databases.sh` now refuses to write when storage is not
  safely mounted.
- `scripts/storage/storage_preflight.sh` provides a single pre-start gate for
  storage-backed services.
- `scripts/storage/install_mount_service.sh` installs the mount unit without
  mounting immediately unless `--start` is passed.
- `scripts/storage/install_docker_storage_guard.sh` installs a Docker systemd
  drop-in so Docker waits for `/mnt/storage` on future restarts/boots.
- `docs/13_MONITORING_RUNBOOK.md` now contains the incident workflow.
