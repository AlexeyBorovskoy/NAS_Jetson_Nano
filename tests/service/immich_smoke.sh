#!/usr/bin/env bash
set -euo pipefail
# immich_smoke.sh -- smoke test for Immich service
# Checks /api/server/ping endpoint availability.

SCRIPT_NAME="$(basename "$0")"
URL=""
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --url <immich_url> [OPTIONS]

Options:
  --url <url>     Immich base URL, e.g. http://192.168.0.50:2283 (required)
  --output <file> Save Markdown report (optional)
  --help          Show this help

Examples:
  $SCRIPT_NAME --url http://192.168.0.50:2283
  $SCRIPT_NAME --url http://95.163.176.103:2283 --output /tmp/immich-smoke.md
EOF
}

check_deps() {
    for dep in curl; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            echo "ERROR: $dep not found" >&2; exit 2
        fi
    done
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)     URL="${2:-}"; shift 2 ;;
        --output)  OUTPUT="${2:-}"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$URL" ]]; then
    echo "ERROR: --url is required" >&2; usage >&2; exit 1
fi

check_deps

URL="${URL%/}"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
PASS=0
FAIL=0
REPORT_LINES=()

echo "=== Immich Smoke Test: $URL ($TIMESTAMP) ==="
echo ""

check_endpoint() {
    local label="$1" path="$2" expected_http="${3:-200}"
    local http_code response_time
    http_code="$(curl -o /dev/null -sf -w '%{http_code}' --max-time 15 "${URL}${path}" 2>/dev/null || echo "000")"
    response_time="$(curl -o /dev/null -sf -w '%{time_total}' --max-time 15 "${URL}${path}" 2>/dev/null || echo "0")"

    if [[ "$http_code" == "$expected_http" ]]; then
        echo "PASS: $label -> HTTP $http_code (${response_time}s)"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| $label | PASS | HTTP $http_code | ${response_time}s |")
    else
        echo "FAIL: $label -> HTTP $http_code (expected $expected_http)"
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| $label | FAIL | HTTP $http_code (expected $expected_http) | ${response_time}s |")
    fi
}

check_endpoint "API ping" "/api/server/ping" "200"

# Check ping response body
PING_BODY="$(curl -sf --max-time 10 "${URL}/api/server/ping" 2>/dev/null || echo "")"
if echo "$PING_BODY" | grep -q '"res":"pong"'; then
    echo "PASS: Immich ping responds with pong"
    PASS=$((PASS + 1))
    REPORT_LINES+=("| res=pong | PASS | got pong response | -- |")
else
    echo "WARN: Immich ping response: $PING_BODY"
    REPORT_LINES+=("| res=pong | WARN | unexpected: $PING_BODY | -- |")
fi

# Check server info (no auth required)
check_endpoint "Server info" "/api/server/about" "200"

echo ""
echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Immich Smoke Test Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**URL:** $URL"
        echo ""
        echo "| Check | Result | Details | Response Time |"
        echo "|---|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do
            echo "$line"
        done
        echo ""
        echo "**Total:** PASS=$PASS  FAIL=$FAIL"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
