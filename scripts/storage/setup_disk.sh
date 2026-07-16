#!/usr/bin/env bash
set -euo pipefail
# setup_disk.sh — mount USB HDD for NAS_Jetson_Nano on Jetson Nano
#
# Usage: sudo bash scripts/storage/setup_disk.sh [DEVICE] [MOUNT_POINT]
# Example: sudo bash scripts/storage/setup_disk.sh /dev/sda1 /mnt/storage
#
# Patterns from: JetsonHacks bootFromUSB (UUID/PARTUUID) + NasberryPi (preflight)

DEVICE="${1:-}"
MOUNT_POINT="${2:-/mnt/storage}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [[ -z "${DEVICE}" ]]; then
    echo "Available block devices:"
    lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL --noheadings | grep -v "^loop"
    echo ""
    echo "Usage: sudo bash $0 /dev/sdXN /mnt/storage"
    echo "Example: sudo bash $0 /dev/sda1 /mnt/storage"
    exit 1
fi

if [[ ! -b "${DEVICE}" ]]; then
    log "ERROR: ${DEVICE} is not a block device."
    lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT --noheadings | grep -v "^loop"
    exit 1
fi

UUID="$(blkid -s UUID -o value "${DEVICE}")"
FSTYPE="$(blkid -s TYPE -o value "${DEVICE}")"

log "Device:     ${DEVICE}"
log "UUID:       ${UUID}"
log "FSTYPE:     ${FSTYPE}"
log "MountPoint: ${MOUNT_POINT}"

mkdir -p "${MOUNT_POINT}"
cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"
log "fstab backed up."

if grep -q "${UUID}" /etc/fstab; then
    log "UUID ${UUID} already in /etc/fstab — skipping."
else
    echo "UUID=${UUID} ${MOUNT_POINT} ${FSTYPE} defaults,nofail,x-systemd.device-timeout=15s 0 2" \
        | tee -a /etc/fstab
    log "Added to /etc/fstab."
fi

mount -a
findmnt "${MOUNT_POINT}"

# Create NAS_Jetson_Nano directory layout
for dir in \
    nextcloud/data \
    immich/library \
    db/nextcloud-postgres \
    db/immich-postgres \
    samba/public \
    backups/database-dumps \
    logs/health; do
    mkdir -p "${MOUNT_POINT}/${dir}"
done
chown -R 1000:1000 "${MOUNT_POINT}" 2>/dev/null || true

log "=== Disk setup complete ==="
log "  Set STORAGE_ROOT=${MOUNT_POINT} in config/.env"
df -h "${MOUNT_POINT}"
