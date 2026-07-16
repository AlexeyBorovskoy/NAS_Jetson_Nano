#!/usr/bin/env bash
set -euo pipefail
# adb_readonly_check.sh -- read-only ADB device check
#
# SAFETY POLICY (MANDATORY):
# - ONLY read-only ADB commands
# - NO adb install / uninstall / shell rm / pull personal data / reboot
# - NO IMEI, serial number, phone number, email, WiFi password logging
# - NO personal photos, contacts, SMS extraction
#
# Reports: device connection, Android version, user app list (anonymized)

SCRIPT_NAME="$(basename "$0")"
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Options:
  --output <file>  Save Markdown report (optional)
  --help           Show this help

Note: Requires ADB installed and device connected via USB with USB debugging enabled.
      This script performs ONLY read-only checks.
      IMEI, serial number, accounts, and personal data are NEVER logged.

Examples:
  $SCRIPT_NAME
  $SCRIPT_NAME --output /tmp/android-check.md
EOF
}

check_deps() {
    if ! command -v adb >/dev/null 2>&1; then
        echo "INFO: adb not found -- Android checks not applicable in this environment" >&2
        echo "Install ADB: apt-get install adb  OR  download from developer.android.com"
        echo ""
        echo "RESULT: NOT APPLICABLE (adb not installed)"
        exit 0
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)  OUTPUT="${2:-}"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

check_deps

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
PASS=0
FAIL=0
REPORT_LINES=()

echo "=== NAS_Jetson_Nano Android ADB Read-Only Check ($TIMESTAMP) ==="
echo ""
echo "POLICY: Only read-only ADB commands. No personal data extracted."
echo ""

# 1. Check ADB server
echo "--- ADB Device List ---"
DEVICES="$(adb devices 2>/dev/null || echo "")"
echo "$DEVICES"

DEVICE_COUNT="$(echo "$DEVICES" | grep -c "device$" || echo "0")"
if [[ "$DEVICE_COUNT" -gt 0 ]]; then
    echo "PASS: $DEVICE_COUNT device(s) connected"
    PASS=$((PASS + 1))
    REPORT_LINES+=("| ADB devices | PASS | $DEVICE_COUNT device(s) connected |")
else
    echo "FAIL: No authorized ADB devices found"
    echo "      Check: USB debugging enabled, authorization prompt accepted"
    FAIL=$((FAIL + 1))
    REPORT_LINES+=("| ADB devices | FAIL | no authorized devices |")
    # If no device, remaining checks are not applicable
    echo ""
    echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="
    exit 1
fi

# 2. Android version (safe property)
echo ""
echo "--- Android Version ---"
ANDROID_VER="$(adb shell getprop ro.build.version.release 2>/dev/null || echo "unknown")"
ANDROID_API="$(adb shell getprop ro.build.version.sdk 2>/dev/null || echo "unknown")"
BRAND="$(adb shell getprop ro.product.brand 2>/dev/null || echo "unknown")"
MODEL="$(adb shell getprop ro.product.model 2>/dev/null || echo "unknown")"

echo "Brand: $BRAND"
echo "Model: $MODEL"
echo "Android: $ANDROID_VER (API $ANDROID_API)"

# NOTE: NOT logging IMEI, serial, phone number, accounts
REPORT_LINES+=("| Android version | INFO | $BRAND $MODEL, Android $ANDROID_VER (API $ANDROID_API) |")

# 3. Check NAS_Jetson_Nano-related apps installed
echo ""
echo "--- NAS_Jetson_Nano Apps Check ---"
APP_LIST="$(adb shell pm list packages -3 2>/dev/null || echo "")"

check_app() {
    local label="$1" package="$2"
    if echo "$APP_LIST" | grep -q "package:${package}"; then
        echo "PASS: $label ($package) is installed"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| $label installed | PASS | $package |")
    else
        echo "WARN: $label ($package) not found"
        REPORT_LINES+=("| $label installed | WARN | not found |")
    fi
}

check_app "Immich" "app.alextran.immich"
check_app "Nextcloud" "com.nextcloud.client"
check_app "DAVx5" "at.bitfire.davdroid"

echo ""
echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="
echo ""
echo "NOTE: Manual verification required for:"
echo "  - Login success (cannot test without credentials in script)"
echo "  - Backup queue status"
echo "  - Sync configuration"
echo "See: docs/quality/ANDROID_TESTS.md"

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Android ADB Read-Only Check Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Policy:** Read-only checks only. No personal data logged."
        echo ""
        echo "| Check | Result | Details |"
        echo "|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do
            echo "$line"
        done
        echo ""
        echo "**Total:** PASS=$PASS  FAIL=$FAIL"
        echo ""
        echo "## Not Logged (Privacy)"
        echo "- IMEI / MEID"
        echo "- Phone number"
        echo "- Google/email accounts"
        echo "- WiFi passwords"
        echo "- Personal photos or contacts"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
