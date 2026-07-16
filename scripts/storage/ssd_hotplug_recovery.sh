#!/usr/bin/env bash
# NAS_Jetson_Nano SSD hotplug auto-recovery
# Triggered by udev when /dev/sda1 partition appears (USB SSD connected)
# Flow: mount /mnt/storage → storage preflight → start Docker → start stopped containers
set -euo pipefail

LOG_DIR="/var/log/nas_jetson_nano-monitor"
LOG="$LOG_DIR/ssd-recovery.log"
mkdir -p "$LOG_DIR"
exec >> "$LOG" 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== SSD hotplug recovery triggered ==="

# Wait for partition to fully settle (device node stabilizes after udev add event)
sleep 5

# Mount /mnt/storage if not already mounted
if mountpoint -q /mnt/storage; then
    log "/mnt/storage already mounted"
else
    log "Mounting /mnt/storage..."
    if mount /mnt/storage; then
        log "Mounted: $(findmnt -n -o SOURCE,FSTYPE,OPTIONS /mnt/storage 2>/dev/null || echo 'OK')"
    else
        log "ERROR: mount /mnt/storage failed — aborting recovery"
        exit 1
    fi
fi

# Storage preflight — guards against read-only or corrupted filesystem
log "Running storage preflight..."
PREFLIGHT_OUT=$(bash /home/admin/nas_jetson_nano/scripts/storage/storage_preflight.sh 2>&1)
echo "$PREFLIGHT_OUT"
if echo "$PREFLIGHT_OUT" | grep -q "errors=0"; then
    log "Preflight OK"
else
    log "ERROR: preflight failed — not starting Docker"
    exit 1
fi

# Start Docker if not running (stopped by storage guard when SSD was gone)
if systemctl is-active --quiet docker; then
    log "Docker already running"
else
    log "Starting Docker..."
    systemctl start docker
    # Wait for Docker daemon to accept connections
    for i in $(seq 1 10); do
        docker info &>/dev/null && break
        sleep 2
    done
    log "Docker status: $(systemctl is-active docker)"
fi

# Start stopped containers (restart:always handles crashes, not Docker daemon restarts)
STOPPED_IDS=$(docker ps -a -q --filter status=exited 2>/dev/null || true)
if [ -n "$STOPPED_IDS" ]; then
    STOPPED_NAMES=$(docker ps -a --format '{{.Names}}' --filter status=exited | tr '\n' ' ')
    log "Starting stopped containers: $STOPPED_NAMES"
    echo "$STOPPED_IDS" | xargs docker start
    sleep 3
    RUNNING=$(docker ps --format '{{.Names}}' | wc -l)
    log "Running containers after recovery: $RUNNING"
else
    log "All containers already running — nothing to do"
fi

log "=== Recovery complete ==="
