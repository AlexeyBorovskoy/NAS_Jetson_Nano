#!/usr/bin/env bash
# usb_preboot_cycle.sh — сброс RTL9210B-CG при каждом старте системы
#
# Проблема: RTL9210B-CG сохраняет crashed-состояние через software reboot
# (USB хаб остаётся под питанием). Этот скрипт запускается ДО
# jetson-nas-mount.service и делает full power cycle всего хаба,
# давая чипу шанс полностью переинициализироваться.
#
# Запускается: systemd (nas_jetson_nano-usb-preboot.service) до монтирования SSD

set -euo pipefail

UHUBCTL="/usr/local/sbin/uhubctl"
HUB_USB2="1-2"
HUB_USB3="2-1"
PORT=2
POWER_OFF_SECS=30
WAIT_ENUM_SECS=25
LOG_TAG="nas_jetson_nano-usb-preboot"
SSD_DEV="/dev/sda"

log()  { echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $*" | systemd-cat -t "$LOG_TAG" -p info;  echo "$*" >&2; }
warn() { echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN]  $*" | systemd-cat -t "$LOG_TAG" -p warning; echo "$*" >&2; }

# Если SSD уже виден — хип не в плохом состоянии, пропускаем цикл
if [[ -b "$SSD_DEV" ]]; then
    log "SSD $SSD_DEV already present — skipping pre-boot power cycle"
    exit 0
fi

log "SSD $SSD_DEV not found at boot — applying pre-boot USB power cycle (port $PORT, ${POWER_OFF_SECS}s off)..."

# Power off port 2 на обоих хабах
"$UHUBCTL" -l "$HUB_USB2" -p "$PORT" -a off 2>/dev/null || true
"$UHUBCTL" -l "$HUB_USB3" -p "$PORT" -a off 2>/dev/null || true

sleep "$POWER_OFF_SECS"

# Power on
"$UHUBCTL" -l "$HUB_USB3" -p "$PORT" -a on 2>/dev/null || true
"$UHUBCTL" -l "$HUB_USB2" -p "$PORT" -a on 2>/dev/null || true

log "Power cycle done. Waiting ${WAIT_ENUM_SECS}s for enumeration..."
sleep "$WAIT_ENUM_SECS"

if [[ -b "$SSD_DEV" ]]; then
    log "SSD $SSD_DEV enumerated successfully after pre-boot cycle"
    exit 0
else
    warn "SSD $SSD_DEV still not visible after pre-boot cycle — watchdog will handle recovery"
    exit 0  # Не падаем — пусть watchdog попробует дальше
fi
