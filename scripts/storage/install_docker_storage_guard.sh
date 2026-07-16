#!/usr/bin/env bash
set -euo pipefail

# install_docker_storage_guard.sh - optional strict boot guard for Jetson.
# It makes docker.service wait for /mnt/storage, preventing bind mounts from
# silently writing to a plain microSD directory after power loss or USB failure.

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

START_NOW=0
if [[ "${1:-}" == "--start" ]]; then
    START_NOW=1
elif [[ -n "${1:-}" ]]; then
    echo "Usage: $0 [--start]" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../.."
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="/etc/systemd/system"
NAS_JETSON_NANO_DIR="$(realpath "${REPO_ROOT}")"

log "Installing jetson-nas-mount.service with NAS_JETSON_NANO_DIR=${NAS_JETSON_NANO_DIR}"
sudo sed "s|/home/admin/nas_jetson_nano|${NAS_JETSON_NANO_DIR}|g" \
    "${SYSTEMD_SRC}/jetson-nas-mount.service" \
    | sudo tee "${SYSTEMD_DST}/jetson-nas-mount.service" > /dev/null
sudo chmod 644 "${SYSTEMD_DST}/jetson-nas-mount.service"

log "Installing docker.service storage guard drop-in"
sudo mkdir -p "${SYSTEMD_DST}/docker.service.d"
sudo cp "${SYSTEMD_SRC}/docker.service.d/10-nas_jetson_nano-storage.conf" \
    "${SYSTEMD_DST}/docker.service.d/10-nas_jetson_nano-storage.conf"
sudo chmod 644 "${SYSTEMD_DST}/docker.service.d/10-nas_jetson_nano-storage.conf"

sudo systemctl daemon-reload
sudo systemctl enable jetson-nas-mount.service

if (( START_NOW == 1 )); then
    log "Starting jetson-nas-mount.service"
    sudo systemctl start jetson-nas-mount.service
fi

log "Installed. Verify before reboot:"
echo "  systemctl cat docker.service"
echo "  systemctl status jetson-nas-mount.service --no-pager"
echo "  mountpoint /mnt/storage"
