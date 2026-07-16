#!/usr/bin/env bash
# install_backup_timer.sh — deploy nas_jetson_nano-backup.{service,timer} to Jetson systemd
# Run ON JETSON NANO as admin (sudo will be prompted):
#   bash scripts/backup/install_backup_timer.sh
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../.."
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="/etc/systemd/system"
NAS_JETSON_NANO_DIR="$(realpath "${REPO_ROOT}")"
SERVICE_FILE="${SYSTEMD_DST}/nas_jetson_nano-backup.service"

# Patch NAS_JETSON_NANO_PROJECT_DIR inside the service file at install time
log "Installing nas_jetson_nano-backup.service with NAS_JETSON_NANO_PROJECT_DIR=${NAS_JETSON_NANO_DIR}"
sudo sed "s|/home/admin/nas_jetson_nano|${NAS_JETSON_NANO_DIR}|g" \
    "${SYSTEMD_SRC}/nas_jetson_nano-backup.service" \
    | sudo tee "${SERVICE_FILE}" > /dev/null

sudo cp "${SYSTEMD_SRC}/nas_jetson_nano-backup.timer" "${SYSTEMD_DST}/nas_jetson_nano-backup.timer"
sudo chmod 644 "${SERVICE_FILE}" "${SYSTEMD_DST}/nas_jetson_nano-backup.timer"

sudo systemctl daemon-reload
sudo systemctl enable nas_jetson_nano-backup.timer
sudo systemctl start nas_jetson_nano-backup.timer

log "Timer enabled. Current state:"
systemctl status nas_jetson_nano-backup.timer --no-pager
systemctl list-timers nas_jetson_nano-backup.timer --no-pager
log "Next run at 03:00 (±15 min). Test run now: sudo systemctl start nas_jetson_nano-backup.service"
