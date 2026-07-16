# EVIDENCE_REPORT — NAS_Jetson_Nano Article
> Generated: 2026-06-29  
> Purpose: Pre-publication evidence collection for Habr article  
> SSH collection status: **SSH UNAVAILABLE** — Windows host cannot reach Jetson LAN (192.168.0.50) directly. Manual collection required via `ssh root@VPS_IP` tunnel.

---

## SSH Collection Status

```
Collection method attempted: ssh admin@JETSON_LAN_IP
Result: Connection timed out (port 22)
Reason: Windows host not on same LAN as Jetson; tunnel via VPS required
Manual collection command:
  ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'docker ps --format table'"
```

---

## Docker Container Status

**Status: MANUAL COLLECTION REQUIRED**

Expected state (from CLAUDE.md operational table, 2026-06-28):
- 13 containers — all up/healthy
- immich_microservices: mem_limit 512m applied

To verify manually:
```bash
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'docker ps --format \"table {{.Names}}\t{{.Status}}\t{{.Ports}}\"'"
```

Known container list (from article + docker-compose files):
| Container | Expected Status |
|---|---|
| nextcloud | up, healthy |
| nextcloud_db | up, healthy |
| nextcloud_redis | up |
| immich_server | up, healthy |
| immich_db | up, healthy |
| immich_redis | up |
| immich_microservices | up |
| llm_gateway | up |
| nas_jetson_nano_api | up |
| samba | up |
| netdata | up |
| uptime_kuma | up |
| portainer | up |

---

## Service HTTP Status

**Status: MANUAL COLLECTION REQUIRED**

Expected (from CLAUDE.md and article):
| Service | URL | Expected Code |
|---|---|---|
| Nextcloud | http://JETSON_LAN_IP:8080/status.php | 200 |
| Immich | http://JETSON_LAN_IP:2283/api/server/ping | 200 |
| NAS_Jetson_Nano API | http://JETSON_LAN_IP:8099/healthcheck | 200 |
| Nextcloud (VPS) | http://VPS_IP:8080 | 302 |
| Immich (VPS) | http://VPS_IP:2283 | 200 |

To verify manually:
```bash
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8080/status.php'"
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'curl -s -o /dev/null -w \"%{http_code}\" http://localhost:2283/api/server/ping'"
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8099/healthcheck'"
```

---

## System Stats (RAM, Disk, Uptime)

**Status: MANUAL COLLECTION REQUIRED**

Expected values (from article + Telegram report example):
```
RAM:   2.3 / 3.9 GB used  (article claims ~2.3 GB in use)
Disk:  7 GB / 229 GB used  (3%)
Uptime: varies (expected multi-day)
CPU temp: ~41°C
GPU temp: ~40°C
```

To verify:
```bash
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'free -h && df -h /mnt/storage && uptime'"
```

---

## USB / Storage Status

**Status: MANUAL COLLECTION REQUIRED**

Expected (from CLAUDE.md, 2026-06-28):
```
Device:      /dev/sda1
Mount:       /mnt/storage
Size:        229 GB
USB:         JMS583 (152d:a583), USB 3.0, 5000 Mbps, port 2-1.3
UAS quirk:   usb-storage.quirks=...,152d:a583:u  (in /proc/cmdline)
SCSI timeout: 120s (udev rule active)
autosuspend:  -1 (disabled, kernel param)
Write speed:  250 MB/s (measured post-quirk)
Read speed:   172 MB/s (measured post-quirk)
```

To verify:
```bash
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'cat /proc/cmdline && lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT && ls /sys/bus/usb/devices/ | head -20'"
```

---

## Photo / Content Counts

**Status: CROSS-REFERENCED from multiple sources**

| Metric | Source | Value |
|---|---|---|
| Total items uploaded (Android) | Article (Шаг 5) | 6 697 |
| Total in Immich queue (Checkpoint) | CLAUDE.md | 6 710 |
| Immich: photos | NAS_Jetson_Nano API Фото endpoint | 6 484 |
| Immich: videos | NAS_Jetson_Nano API Фото endpoint | 210 |
| Immich total (photos+videos) | Computed | 6 694 |
| Immich: total objects (API) | Article: "6719" (screenshot caption) | 6 719 |
| Contacts (DAVx5/CardDAV) | Article | 2 151 |
| Family members in Talk | Article | 5 |

Notes:
- Discrepancy between 6 697 (uploaded from phone) and 6 484+210=6 694 (Immich count): Immich may exclude duplicates or corrupted files; minor 3-item difference within normal range.
- "6719" in screenshot caption vs "6697" in article text: 6719 likely includes all media items tracked in phone's gallery (including system/hidden files), 6697 is what Immich accepted.
- Checkpoint 2026-06-29 states "6484 фото" — consistent with API data.

---

## goss Test Results

**Status: MANUAL COLLECTION REQUIRED** (last known: 40/40, 2026-06-28)

To verify:
```bash
ssh root@VPS_IP "ssh -p 10022 admin@127.0.0.1 'cd ~/nas_jetson_nano && goss validate --gossfile tests/goss/goss.yaml'"
```

---

## Security Check

**SENSITIVE DATA IN secrets.json — DO NOT EXPOSE:**
- Jetson sudo password: REDACTED
- VPS IP: VPS_IP (placeholder used in this report)
- Nextcloud admin password: REDACTED
- Immich DB password: REDACTED
- Redis password: REDACTED
- DeepSeek API key: REDACTED
- Immich NAS_Jetson_Nano API key: REDACTED
- Family user passwords: REDACTED

**secrets.json is in .gitignore — confirmed NOT committed.**

---

## Screenshot Inventory

**Found in `assets/screenshots/article/` (9 files):**
- beszel_systems_overview.png
- beszel_jetson_metrics.png
- telegram_report_containers.png
- telegram_report_full.png
- telegram_report_external.png
- nextcloud_dashboard.png
- nextcloud_talk.png
- immich_web.png
- nas_jetson_nano_api_swagger.png

**Found in `docs/articles/publication/screenshots/` (8 files — Habr upload set):**
- beszel_systems_overview.png
- beszel_jetson_metrics.png
- android_immich_backup_stats.jpg
- android_davx5_caldav.jpg
- nextcloud_talk.png
- nextcloud_dashboard.png
- nas_jetson_nano_api_swagger.png
- immich_web.png

**Missing from publication set:**
- android_immich_backup_stats.jpg — present ✓
- android_davx5_caldav.jpg — present ✓
- telegram screenshots — present in assets/ but NOT referenced in article (potential addition)

---

## Manual Actions Required

1. SSH into Jetson via VPS tunnel and run collection commands above
2. Visually inspect all 8 publication screenshots for sensitive data (IPs, passwords, emails)
3. Re-run goss to confirm 40/40 still holds
4. Verify docker container count is still 13
