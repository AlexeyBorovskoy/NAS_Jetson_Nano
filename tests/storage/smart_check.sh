#!/usr/bin/env bash
set -euo pipefail
# smart_check.sh -- read-only SMART health check for USB SSD
# Handles RTL9210B-CG USB bridge quirks (known SMART passthrough limitation).
# NEVER runs destructive tests. Reports only.

SCRIPT_NAME="$(basename "$0")"
DEVICE=""
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --device <device_path> [OPTIONS]

Options:
  --device <dev>  Block device to check, e.g. /dev/sda (required)
  --output <file> Save Markdown report (optional)
  --help          Show this help

Note: Requires sudo / root to access SMART data.
      RTL9210B-CG (0x0bda:0x9210) blocks SMART passthrough -- this is a
      known hardware limitation. Script falls back to read-speed test.

Examples:
  sudo $SCRIPT_NAME --device /dev/sda
  sudo $SCRIPT_NAME --device /dev/sda --output /tmp/smart-report.md
EOF
}

check_deps() {
    local missing=()
    command -v smartctl >/dev/null 2>&1 || missing+=("smartmontools")
    command -v dd       >/dev/null 2>&1 || missing+=("coreutils(dd)")
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: missing tools: ${missing[*]}. Install via apt-get." >&2
        exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --device)  DEVICE="${2:-}"; shift 2 ;;
        --output)  OUTPUT="${2:-}"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[[ -z "$DEVICE" ]]   && { echo "ERROR: --device is required" >&2; usage >&2; exit 1; }
[[ ! -b "$DEVICE" ]] && { echo "ERROR: $DEVICE is not a block device" >&2; exit 1; }

check_deps

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
PASS=0; FAIL=0; WARN=0
REPORT_LINES=()
USB_BRIDGE_LIMITED=false

echo "=== NAS_Jetson_Nano SMART Check: $DEVICE ($TIMESTAMP) ==="
echo ""

# --- Detect USB bridge ---
USB_VID_PID=""
DEV_NAME="$(basename "$DEVICE")"
SYS_USB_PATH="$(find /sys/block/"$DEV_NAME"/device -name "idVendor" 2>/dev/null | head -1 || true)"
if [[ -n "$SYS_USB_PATH" ]]; then
    VID="$(cat "$(dirname "$SYS_USB_PATH")/idVendor" 2>/dev/null || true)"
    PID="$(cat "$(dirname "$SYS_USB_PATH")/idProduct" 2>/dev/null || true)"
    USB_VID_PID="${VID}:${PID}"
fi

# Check USB bus speed
USB_SPEED="unknown"
for speed_file in /sys/bus/usb/devices/*/speed; do
    [[ -f "$speed_file" ]] || continue
    spd="$(cat "$speed_file" 2>/dev/null || true)"
    # Find the device that has our vendor:product
    dev_dir="$(dirname "$speed_file")"
    vid_f="${dev_dir}/idVendor"
    pid_f="${dev_dir}/idProduct"
    if [[ -f "$vid_f" && -f "$pid_f" ]]; then
        v="$(cat "$vid_f" 2>/dev/null || true)"
        p="$(cat "$pid_f" 2>/dev/null || true)"
        if [[ "${v}:${p}" == "$USB_VID_PID" ]]; then
            USB_SPEED="$spd"
            break
        fi
    fi
done

RTL9210_DETECTED=false
if echo "$USB_VID_PID" | grep -qi "0bda:9210"; then
    RTL9210_DETECTED=true
    USB_BRIDGE_LIMITED=true
    echo "INFO: RTL9210B-CG USB bridge detected (${USB_VID_PID})"
    echo "      SMART passthrough is blocked by this chip -- known hardware limitation."
    echo "      Falling back to: lsblk, USB speed check, read-speed test."
    echo ""
fi

# --- USB Speed check ---
echo "--- USB Connection Speed ---"
case "$USB_SPEED" in
    5000) echo "PASS: USB 3.0 SuperSpeed (5000 Mbps)" ; PASS=$((PASS+1))
          REPORT_LINES+=("| USB Speed | PASS | 5000 Mbps (USB 3.0 SuperSpeed) |") ;;
    480)  echo "WARN: USB 2.0 High-Speed (480 Mbps) -- expected USB 3.0 SuperSpeed"
          echo "      Max throughput ~40 MB/s. Check cable and port."
          WARN=$((WARN+1))
          REPORT_LINES+=("| USB Speed | WARN | 480 Mbps (USB 2.0) -- should be 5000 Mbps |") ;;
    unknown) echo "INFO: USB speed unknown"
          REPORT_LINES+=("| USB Speed | INFO | could not determine |") ;;
    *)    echo "INFO: USB speed: ${USB_SPEED} Mbps"
          REPORT_LINES+=("| USB Speed | INFO | ${USB_SPEED} Mbps |") ;;
esac
echo ""

# --- SMART (skip if RTL9210 known to block) ---
echo "--- SMART Overall Health ---"
if $RTL9210_DETECTED; then
    echo "SKIP: RTL9210B-CG blocks SMART ATA passthrough (vendor ID 0x0bda:0x9210)"
    echo "      smartctl -d sat returns 'mandatory SMART command failed'"
    echo "      This is confirmed as a hardware bug in the RTL9210 chip family."
    WARN=$((WARN+1))
    REPORT_LINES+=("| SMART Health | WARN | RTL9210B-CG blocks passthrough -- SMART unavailable |")
else
    HEALTH_OUT="$(smartctl -H "$DEVICE" 2>/dev/null || smartctl -d sat -H "$DEVICE" 2>/dev/null || true)"
    echo "$HEALTH_OUT"
    if echo "$HEALTH_OUT" | grep -qiE "PASSED|Health Status:.*OK"; then
        echo "PASS: SMART health PASSED"
        PASS=$((PASS+1))
        REPORT_LINES+=("| SMART Health | PASS | PASSED |")
    elif echo "$HEALTH_OUT" | grep -qiE "FAILED"; then
        echo "FAIL: SMART health FAILED"
        FAIL=$((FAIL+1))
        REPORT_LINES+=("| SMART Health | FAIL | FAILED -- drive may be failing |")
    else
        WARN=$((WARN+1))
        REPORT_LINES+=("| SMART Health | WARN | Status ambiguous |")
    fi
fi
echo ""

# --- Temperature ---
echo "--- Temperature ---"
if $RTL9210_DETECTED; then
    echo "SKIP: Temperature not readable via RTL9210B-CG"
    REPORT_LINES+=("| Temperature | SKIP | RTL9210B-CG blocks thermal data |")
else
    TEMP_OUT="$(smartctl -a "$DEVICE" 2>/dev/null || true)"
    TEMP="$(echo "$TEMP_OUT" | grep -i 'Temperature_Celsius\|Temperature:' | head -1 || true)"
    if [[ -n "$TEMP" ]]; then
        TEMP_VAL="$(echo "$TEMP" | awk '{print $NF}')"
        echo "Temperature: ${TEMP_VAL}C"
        REPORT_LINES+=("| Temperature | INFO | ${TEMP_VAL}C |")
        if [[ "${TEMP_VAL}" -gt 55 ]] 2>/dev/null; then
            echo "WARN: ${TEMP_VAL}C is high (> 55C)"; WARN=$((WARN+1))
        fi
    else
        echo "INFO: Temperature data not available"
        REPORT_LINES+=("| Temperature | INFO | not available |")
    fi
fi
echo ""

# --- Read speed test (safe fallback, read-only) ---
echo "--- Read Speed Test (100 MB, read-only) ---"
READ_SPEED="$(dd if="$DEVICE" of=/dev/null bs=4M count=25 2>&1 | grep -oP '[\d.]+ [MGk]B/s' | tail -1 || true)"
if [[ -n "$READ_SPEED" ]]; then
    echo "Read speed: $READ_SPEED"
    REPORT_LINES+=("| Read Speed | INFO | $READ_SPEED (100 MB sequential read) |")
    # Below 10 MB/s on USB 3.0 = warning
    SPEED_NUM="$(echo "$READ_SPEED" | grep -oP '[\d.]+')"
    SPEED_UNIT="$(echo "$READ_SPEED" | grep -oP '[MG]B/s')"
    if [[ "$SPEED_UNIT" == "MB/s" ]] && awk "BEGIN{exit !($SPEED_NUM < 10)}"; then
        echo "WARN: Read speed very low (< 10 MB/s) -- possible drive failure"
        WARN=$((WARN+1))
    elif [[ "$SPEED_UNIT" == "MB/s" ]] && awk "BEGIN{exit !($SPEED_NUM >= 10)}"; then
        echo "PASS: Read speed $READ_SPEED -- drive responds normally"
        PASS=$((PASS+1))
    fi
else
    echo "FAIL: Read test failed -- device may be unreadable"
    FAIL=$((FAIL+1))
    REPORT_LINES+=("| Read Speed | FAIL | dd read failed |")
fi
echo ""

# --- Disk info summary ---
echo "--- Disk Info ---"
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL "$DEVICE" 2>/dev/null || true
echo ""
df -h "$DEVICE"1 2>/dev/null || df -h "${DEVICE}1" 2>/dev/null || true

echo ""
echo "=== Summary: PASS=$PASS  WARN=$WARN  FAIL=$FAIL ==="
if $USB_BRIDGE_LIMITED; then
    echo "NOTE: RTL9210B-CG limits SMART diagnostics. Replace with JMS583/ASM2362 for full health visibility."
fi

# --- Save report ---
if [[ -n "$OUTPUT" ]]; then
    {
        echo "# SMART Check Report: $DEVICE"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Device:** $DEVICE"
        [[ -n "$USB_VID_PID" ]] && echo "**USB Bridge:** $USB_VID_PID"
        echo ""
        echo "| Check | Result | Details |"
        echo "|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do echo "$line"; done
        echo ""
        echo "**Total:** PASS=$PASS  WARN=$WARN  FAIL=$FAIL"
        if $USB_BRIDGE_LIMITED; then
            echo ""
            echo "> **NOTE:** RTL9210B-CG (0x0bda:0x9210) blocks ATA SMART passthrough."
            echo "> Replace with JMS583 or ASM2362-based enclosure for full diagnostics."
        fi
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

[[ "$FAIL" -gt 0 ]] && exit 1
[[ "$WARN" -gt 0 ]] && exit 2
exit 0
