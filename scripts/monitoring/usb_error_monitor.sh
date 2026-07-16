#!/usr/bin/env bash
# usb_error_monitor.sh — real-time USB SSD error monitor
#
# Watches dmesg for USB SSD errors. On error:
#   1. Sends Telegram alert
#   2. Triggers watchdog immediately (no 3 min wait)
#
# Supported enclosures:
#   RTL9210B-CG (0bda:9210, USB 2.0 hub 1-2.2) — legacy, error -71
#   JMS583      (152d:a583, USB 3.0 port 2-1.3) — current, UAS stream errors
#                 After adding 152d:a583:u quirk + reboot, JMS583 won't generate
#                 stream errors anymore. Monitor still watches as safety net.
#
# Launched by: systemd (nas_jetson_nano-usb-monitor.service) as persistent daemon

set -uo pipefail

LOG_TAG="nas_jetson_nano-usb-monitor"
SSD_DEV="/dev/sda"
ALERT_COOLDOWN_SECS=300
LAST_ALERT=0

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
[[ -f /etc/nas_jetson_nano-monitor/telegram.env ]] && source /etc/nas_jetson_nano-monitor/telegram.env

HOSTNAME_SHORT="$(hostname -s)"

log()  { echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $*" | systemd-cat -t "$LOG_TAG" -p info;  echo "$*" >&2; }
warn() { echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN]  $*" | systemd-cat -t "$LOG_TAG" -p warning; echo "$*" >&2; }

tg_send() {
    local msg="$1"
    [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return 0
    local now
    now=$(date +%s)
    if (( now - LAST_ALERT < ALERT_COOLDOWN_SECS )); then
        return 0
    fi
    LAST_ALERT=$now
    curl -sf --max-time 10 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=[${HOSTNAME_SHORT}] ${msg}" \
        -d "parse_mode=HTML" > /dev/null || true
}

trigger_watchdog() {
    systemctl start nas_jetson_nano-usb-watchdog.service 2>/dev/null || true
}

log "USB error monitor started. Watching dmesg for USB SSD errors..."

dmesg --follow --decode 2>/dev/null | while IFS= read -r line; do

    # RTL9210B-CG: error -71 (USB 2.0 hub path 1-2.2)
    if echo "$line" | grep -qE "usb 1-2\.2.*error -71|1-2-port2.*unable to enum"; then
        warn "USB ERROR (RTL9210B-CG error -71): $line"
        tg_send "⚠️ USB SSD error -71. Docker может упасть. Запускаю watchdog..."
        trigger_watchdog
    fi

    # JMS583: UAS xHCI stream ring errors (USB 3.0 path 2-1.3)
    # These disappear after applying usb-storage.quirks=152d:a583:u + reboot
    if echo "$line" | grep -qE "tegra-xusb.*ERROR Transfer event.*stream ring"; then
        warn "USB ERROR (JMS583 UAS stream error): $line"
        tg_send "⚠️ USB SSD JMS583 xHCI stream error. Запускаю watchdog..."
        trigger_watchdog
    fi

    # Generic USB reset on SSD port — repeated resets indicate a problem
    if echo "$line" | grep -qE "usb 2-1\.3: reset SuperSpeed"; then
        warn "USB reset on port 2-1.3: $line"
    fi

    # SSD reconnected (RTL9210B-CG)
    if echo "$line" | grep -qE "usb 1-2\.2.*New USB device found.*9210"; then
        log "RTL9210B-CG re-enumerated"
        tg_send "✅ USB SSD (RTL9210B-CG) переподключился"
    fi

    # SSD reconnected (JMS583)
    if echo "$line" | grep -qE "usb.*New USB device found.*152d"; then
        log "JMS583 re-enumerated"
        tg_send "✅ USB SSD (JMS583) переподключился"
    fi

done

log "dmesg follow exited — restarting..."
exit 1
