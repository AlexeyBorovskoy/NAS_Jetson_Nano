#!/usr/bin/env bash
set -euo pipefail

# install_mount_service.sh - install jetson-nas-mount.service on Jetson.
# Default behavior only installs/enables the unit. Pass --start after storage
# hardware is stable to mount immediately.

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
SYSTEMD_SRC="${REPO_ROOT}/systemd/jetson-nas-mount.service"
SYSTEMD_DST="/etc/systemd/system/jetson-nas-mount.service"
NAS_JETSON_NANO_DIR="$(realpath "${REPO_ROOT}")"

log "Installing jetson-nas-mount.service with NAS_JETSON_NANO_DIR=${NAS_JETSON_NANO_DIR}"
sudo sed "s|/home/admin/nas_jetson_nano|${NAS_JETSON_NANO_DIR}|g" \
    "${SYSTEMD_SRC}" \
    | sudo tee "${SYSTEMD_DST}" > /dev/null
sudo chmod 644 "${SYSTEMD_DST}"

sudo systemctl daemon-reload
sudo systemctl enable jetson-nas-mount.service

if (( START_NOW == 1 )); then
    log "Starting jetson-nas-mount.service"
    sudo systemctl start jetson-nas-mount.service
else
    log "Unit enabled. Start later with: sudo systemctl start jetson-nas-mount.service"
fi

systemctl status jetson-nas-mount.service --no-pager || true
