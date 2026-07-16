---
layout: default
title: Reliability & Validation
---

# Reliability and validation

## USB SSD: three incidents

The most eventful part of the project was keeping the USB SSD alive.

### Incident 1 — RTL9210B-CG + autosuspend (error -71)

First enclosure used the RTL9210B-CG chip. After days of working fine, dmesg started showing:

```
usb 2-1.3: USB disconnect, device number X
sd 0:0:0:0: [sda] tag#0 FAILED Result: hostbyte=DID_ERROR
```

Root cause: RTL9210B-CG enters USB autosuspend at idle. Tegra kernel 4.9 does not wake it back.  
Docker dropped. Data unavailable. `usbcore.autosuspend=-1` helped partially but write speed degraded to 40 MB/s and stream errors started.

**Resolution:** Replace the enclosure.

### Incident 2 — broken USB port 4

New enclosure (JMS583) connected to port 4 — same disconnect symptoms. Port 4 is physically unstable.  
Moved to **port 2** — works reliably ever since. Documented in watchdog config: `PORT=2`.

### Incident 3 — CRLF line endings in bash scripts

Scripts edited on Windows had `\r\n` endings. Jetson bash saw `#!/bin/bash\r` and refused to execute.

**Resolution:** `.gitattributes` with `* text=auto eol=lf`. All scripts are auto-converted to LF on Linux checkout.

## Current reliability stack

| Layer | What it does |
|---|---|
| `usbcore.autosuspend=-1` | Disable USB power management globally (kernel cmdline) |
| `usb-storage.quirks=152d:a583:u` | Switch JMS583 to BOT mode, disable UAS |
| SCSI timeout 120s (udev rule) | Prevent premature I/O failure on slow responses |
| `nas_jetson_nano-usb-preboot.service` | Power cycle USB port 2 before mounting, every boot |
| `nas_jetson_nano-usb-watchdog.timer` | Periodic check; restores power to port 2 if SSD disappears |
| `nas_jetson_nano-usb-monitor.service` | Detects dmesg USB errors (-71, stream errors), sends Telegram alert |
| `nas_jetson_nano-ssd-recovery.service` | udev trigger on `sda1`: mount → preflight → Docker → 13 containers |

### Self-healing on SSD disconnect

If the SSD cable is physically unplugged and replugged:

1. udev detects `sda1` appearing
2. `nas_jetson_nano-ssd-recovery.service` runs automatically
3. Mounts `/mnt/storage`, runs preflight
4. Starts Docker daemon and all containers

No manual SSH required. Full recovery in under 60 seconds.

## Historical validation snapshot: goss 40/40

Infrastructure tested with [goss](https://github.com/goss-org/goss) (ARM64 binary):

```bash
# Run all tests:
cd ~/nas_jetson_nano && goss -g tests/goss/goss.yaml validate
```

Test categories:
- Ports open (Nextcloud, Immich, API, Netdata, etc.)
- Systemd services active (watchdog, monitor, preboot, tunnel)
- Files present (`/mnt/storage`, config files, scripts)
- HTTP endpoints responding (200/302)
- Mount point available

Recorded result on 2026-06-28: **40/40 passing**. This is historical evidence and must be rerun before being described as current.

## Telegram daily report

Every morning at 09:00 the monitoring script sends:

```
NAS_JETSON_NANO — Daily Report
SYSTEM: Uptime 18h | RAM 2.3/3.9G | Disk 7G/229G | Temp 41°C
CONTAINERS: ✅ all 13 running (restarts: 0)
LOCAL HTTP: ✅ Nextcloud 302 ✅ Immich 200
EXTERNAL: ✅ Nextcloud VPS ✅ Immich VPS
```

Also: JMS583 hourly health monitor posts to Telegram on USB errors or speed degradation.

## Monitoring stack

| Tool | What it shows |
|---|---|
| Beszel Hub (VPS:8091) | Historical CPU/RAM/Disk/Network for both Jetson and VPS |
| Uptime Kuma (Jetson:3001) | Service uptime, HTTP check history |
| Netdata (Jetson:19999) | Real-time system metrics, per-process breakdown |
| Portainer (Jetson:9000) | Container status, logs, resource usage |
| Telegram bot | Daily summary + critical alerts |

---

[← Architecture](architecture.md) | [Android client →](android.md)
