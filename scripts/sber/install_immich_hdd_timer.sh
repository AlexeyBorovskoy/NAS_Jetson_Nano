#!/usr/bin/env bash
# Install Immich→HDD second-copy timer on Jetson (ADR-0009).
# Run as root on device after git pull.
# Usage: sudo bash scripts/sber/install_immich_hdd_timer.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
UNIT_SRC="$ROOT/systemd"
# Prefer live layout used on device
PROJECT_DIR="${NAS_JETSON_NANO_PROJECT_DIR:-/home/admin/nasa}"

if [[ ! -d /mnt/hdd2tb ]]; then
  echo "ERROR: /mnt/hdd2tb not mounted"
  exit 1
fi
if [[ ! -d /mnt/storage ]]; then
  echo "ERROR: /mnt/storage not mounted"
  exit 1
fi

install -m 0644 "$UNIT_SRC/nas_jetson_nano-immich-hdd-copy.service" /etc/systemd/system/
install -m 0644 "$UNIT_SRC/nas_jetson_nano-immich-hdd-copy.timer" /etc/systemd/system/

# Point service at actual project dir if different
if [[ -d "$PROJECT_DIR" ]]; then
  sed -i "s|/home/admin/nasa|$PROJECT_DIR|g" /etc/systemd/system/nas_jetson_nano-immich-hdd-copy.service
fi

mkdir -p /mnt/hdd2tb/backups/immich
systemctl daemon-reload
systemctl enable --now nas_jetson_nano-immich-hdd-copy.timer
systemctl status nas_jetson_nano-immich-hdd-copy.timer --no-pager || true

echo "Dry-run once:"
echo "  DRY_RUN=1 NAS_JETSON_NANO_PROJECT_DIR=$PROJECT_DIR bash $PROJECT_DIR/scripts/backup/immich_hdd_second_copy.sh"
