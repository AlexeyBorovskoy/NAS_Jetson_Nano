# Тесты хранилища / Storage Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Hardware Context

- Device: USB SSD via RTL9210B-CG USB-SATA bridge
- Known issue: RTL9210B-CG produces error -71 (USB disconnect) under load or after power events
- Mitigation: nas_jetson_nano-usb-watchdog.timer (every 3 min), nas_jetson_nano-usb-preboot.service (every boot)
- SMART passthrough: limited via USB bridge; use `smartctl -d sat` or `-d scsi`

---

## Test Scripts

### mount_check.sh

```bash
# Default (checks /mnt/storage)
tests/storage/mount_check.sh

# Custom mount point
tests/storage/mount_check.sh --mount-point /mnt/storage --output /tmp/mount-report.md
```

### smart_check.sh

```bash
# Read-only SMART check (requires sudo on Jetson)
sudo tests/storage/smart_check.sh --device /dev/sda

# With USB bridge hint
sudo tests/storage/smart_check.sh --device /dev/sda --output /tmp/smart-report.md
```

Note: SMART may return "Unable to detect device type" via RTL9210B-CG.
Try: `sudo smartctl -d sat -H /dev/sda` or `sudo smartctl -d scsi -H /dev/sda`

### fio_quick_test.sh

WARNING: Creates and deletes test files only in specified directory. Never run on /, /home, /etc.

```bash
# Requires explicit confirmation
tests/storage/fio_quick_test.sh \
  --directory /mnt/storage/test_fio \
  --size 512m
```

---

## Manual Test Procedures

### T4.1: Mount Check

```bash
mountpoint -q /mnt/storage && echo "MOUNTED" || echo "NOT MOUNTED"
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL
findmnt /mnt/storage
```

Expected:
- /mnt/storage is mounted
- Backing device is /dev/sda1 (NOT mmcblk)
- Filesystem: ext4
- Options: rw (not ro)

### T4.2: SMART Health

```bash
sudo smartctl -H /dev/sda
sudo smartctl -d sat -H /dev/sda  # if USB bridge
sudo smartctl -a /dev/sda | head -50
```

Expected: SMART overall-health self-assessment test result: PASSED

### T4.3: Disk Usage

```bash
df -h /mnt/storage
```

Expected: Use% < 85%

### T4.4: I/O Performance Baseline

Expected speeds (RTL9210B-CG USB 3.0 SSD):
- Sequential write: > 100 MB/s (target: ~300 MB/s)
- Sequential read: > 150 MB/s (target: ~350 MB/s)

If speeds are < 50 MB/s, check:
- USB 3.0 vs 2.0 port (USB 2.0 caps at ~40 MB/s)
- Hub port configuration
- USB error log: `dmesg | grep -i "usb\|sda\|rtl" | tail -30`

---

## USB SSD Reliability Checks

```bash
# Check watchdog status
systemctl status nas_jetson_nano-usb-watchdog.timer
systemctl status nas_jetson_nano-usb-watchdog.service

# Check preboot service
systemctl status nas_jetson_nano-usb-preboot.service

# Check error monitor
systemctl status nas_jetson_nano-usb-monitor.service

# Recent USB errors
dmesg | grep -E "error -71|unable to enum|sda.*error" | tail -20

# State file (retry counter)
cat /var/lib/nas_jetson_nano-usb-watchdog.state 2>/dev/null || echo "No state (SSD healthy)"
```

---

## Expected Results

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| /mnt/storage mounted | yes | | |
| Backing device | /dev/sda1 | | |
| Filesystem | ext4 | | |
| Mounted rw | yes | | |
| Disk usage | < 85% | | |
| SMART health | PASSED | | |
| USB watchdog | active | | |
| Error -71 in last hour | no | | |
| Sequential write | > 100 MB/s | | |
| Sequential read | > 150 MB/s | | |
