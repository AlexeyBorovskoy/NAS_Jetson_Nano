#!/usr/bin/env bash
set -euo pipefail
# mount_check.sh -- read-only storage mount check
# Checks lsblk, blkid, df, mountpoint. Never formats or unmounts.

SCRIPT_NAME="$(basename "$0")"
MOUNT_POINT="/mnt/storage"
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Options:
  --mount-point <path>  Mount point to check (default: /mnt/storage)
  --output <file>       Save Markdown report (optional)
  --help                Show this help

Examples:
  $SCRIPT_NAME
  $SCRIPT_NAME --mount-point /mnt/storage --output /tmp/mount-report.md
EOF
}

check_deps() {
    for dep in df mountpoint; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            echo "ERROR: $dep not found" >&2; exit 2
        fi
    done
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mount-point) MOUNT_POINT="${2:-}"; shift 2 ;;
        --output)      OUTPUT="${2:-}"; shift 2 ;;
        --help|-h)     usage; exit 0 ;;
        *)             echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

check_deps

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
PASS=0
FAIL=0
WARN=0
REPORT_LINES=()

echo "=== NAS_Jetson_Nano Storage Mount Check ($TIMESTAMP) ==="
echo "Mount point: $MOUNT_POINT"
echo ""

# 1. Block devices
echo "--- Block Devices ---"
if command -v lsblk >/dev/null 2>&1; then
    lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL 2>/dev/null || true
fi
echo ""

# 2. Mount check
echo "--- Mount Check: $MOUNT_POINT ---"
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "PASS: $MOUNT_POINT is mounted"
    PASS=$((PASS + 1))
    REPORT_LINES+=("| Mounted | PASS | $MOUNT_POINT is a mountpoint |")
else
    echo "FAIL: $MOUNT_POINT is NOT mounted"
    FAIL=$((FAIL + 1))
    REPORT_LINES+=("| Mounted | FAIL | $MOUNT_POINT is not a mountpoint |")
fi

# 3. Backing device check (must NOT be microSD)
if command -v findmnt >/dev/null 2>&1; then
    SOURCE="$(findmnt -n -T "$MOUNT_POINT" -o SOURCE 2>/dev/null || echo "unknown")"
    FSTYPE="$(findmnt -n -T "$MOUNT_POINT" -o FSTYPE 2>/dev/null || echo "unknown")"
    OPTIONS="$(findmnt -n -T "$MOUNT_POINT" -o OPTIONS 2>/dev/null || echo "unknown")"

    echo "Source: $SOURCE"
    echo "Fstype: $FSTYPE"
    echo "Options: $OPTIONS"

    if [[ "$SOURCE" == /dev/mmcblk* ]]; then
        echo "FAIL: Storage is backed by microSD ($SOURCE) -- unsafe for data"
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| Backing device | FAIL | microSD: $SOURCE |")
    elif [[ "$SOURCE" == /dev/sd* ]]; then
        echo "PASS: Backing device is USB storage: $SOURCE"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| Backing device | PASS | USB: $SOURCE |")
    else
        echo "WARN: Backing device unknown: $SOURCE"
        WARN=$((WARN + 1))
        REPORT_LINES+=("| Backing device | WARN | $SOURCE |")
    fi

    if [[ "$FSTYPE" == "ext4" ]]; then
        echo "PASS: Filesystem is ext4"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| Filesystem | PASS | ext4 |")
    else
        echo "WARN: Filesystem is $FSTYPE (expected ext4)"
        WARN=$((WARN + 1))
        REPORT_LINES+=("| Filesystem | WARN | $FSTYPE (expected ext4) |")
    fi

    if [[ ",${OPTIONS}," == *",ro,"* ]]; then
        echo "FAIL: Filesystem is mounted READ-ONLY"
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| Mount mode | FAIL | read-only |")
    else
        echo "PASS: Filesystem is mounted read-write"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| Mount mode | PASS | read-write |")
    fi
fi

# 4. Disk usage
echo ""
echo "--- Disk Usage ---"
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    df -h "$MOUNT_POINT"
    USAGE_PCT="$(df -P "$MOUNT_POINT" 2>/dev/null | awk 'NR==2 {gsub("%","",$5); print $5}')"
    if [[ -n "$USAGE_PCT" ]]; then
        if [[ "$USAGE_PCT" -ge 90 ]]; then
            echo "FAIL: Disk usage is ${USAGE_PCT}% (>= 90% critical)"
            FAIL=$((FAIL + 1))
            REPORT_LINES+=("| Disk usage | FAIL | ${USAGE_PCT}% |")
        elif [[ "$USAGE_PCT" -ge 85 ]]; then
            echo "WARN: Disk usage is ${USAGE_PCT}% (>= 85% warning)"
            WARN=$((WARN + 1))
            REPORT_LINES+=("| Disk usage | WARN | ${USAGE_PCT}% |")
        else
            echo "PASS: Disk usage is ${USAGE_PCT}%"
            PASS=$((PASS + 1))
            REPORT_LINES+=("| Disk usage | PASS | ${USAGE_PCT}% |")
        fi
    fi
fi

echo ""
echo "=== Summary: PASS=$PASS  WARN=$WARN  FAIL=$FAIL ==="

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Storage Mount Check Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Mount Point:** $MOUNT_POINT"
        echo ""
        echo "| Check | Result | Details |"
        echo "|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do
            echo "$line"
        done
        echo ""
        echo "**Total:** PASS=$PASS  WARN=$WARN  FAIL=$FAIL"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

[[ "$FAIL" -gt 0 ]] && exit 1
[[ "$WARN" -gt 0 ]] && exit 2
exit 0
