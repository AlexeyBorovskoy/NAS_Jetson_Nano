#!/usr/bin/env bash
# Install and enable the two-minute homecloud_* recovery watchdog on Jetson.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/layout.sh
source "${ROOT}/scripts/lib/layout.sh"

sudo install -d -m 0755 "${NAS_STATE_DIR}" /etc/nas-watchdog.pause.d
sudo install -m 0644 \
  "${ROOT}/systemd/nas_jetson_nano-container-watchdog.service" \
  "${ROOT}/systemd/nas_jetson_nano-container-watchdog.timer" \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nas_jetson_nano-container-watchdog.timer

systemctl is-enabled nas_jetson_nano-container-watchdog.timer
systemctl is-active nas_jetson_nano-container-watchdog.timer
systemctl list-timers nas_jetson_nano-container-watchdog.timer --no-pager
