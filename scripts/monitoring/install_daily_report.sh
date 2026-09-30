#!/usr/bin/env bash
# Install the daily Telegram report using the host-specific legacy/current prefix.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/layout.sh
source "${ROOT}/scripts/lib/layout.sh"

as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

unit="${NAS_UNIT_PREFIX}-daily-report-telegram"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

sed "s|/usr/local/sbin/nas_jetson_nano|${NAS_SBIN_PREFIX}|g" \
    "${ROOT}/systemd/nas_jetson_nano-daily-report-telegram.service" \
    > "${tmpdir}/${unit}.service"
sed "s|nas_jetson_nano-daily-report-telegram|${unit}|g" \
    "${ROOT}/systemd/nas_jetson_nano-daily-report-telegram.timer" \
    > "${tmpdir}/${unit}.timer"

as_root install -d -m 0755 /usr/local/lib/nas_jetson_nano
as_root install -m 0644 "${ROOT}/scripts/lib/layout.sh" \
    /usr/local/lib/nas_jetson_nano/layout.sh
as_root install -m 0755 \
    "${ROOT}/scripts/monitoring/nas_jetson_nano-daily-report.sh" \
    "${NAS_SBIN_PREFIX}-daily-report.sh"
as_root install -m 0755 \
    "${ROOT}/scripts/monitoring/nas_jetson_nano-send-report-telegram.sh" \
    "${NAS_SBIN_PREFIX}-send-report-telegram.sh"
as_root install -m 0644 "${tmpdir}/${unit}.service" "${tmpdir}/${unit}.timer" \
    /etc/systemd/system/
as_root systemctl daemon-reload
as_root systemctl enable --now "${unit}.timer"

systemctl is-enabled "${unit}.timer"
systemctl is-active "${unit}.timer"
systemctl list-timers "${unit}.timer" --no-pager
