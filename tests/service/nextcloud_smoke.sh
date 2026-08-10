#!/usr/bin/env bash
set -euo pipefail
# nextcloud_smoke.sh -- smoke test for Nextcloud service
# Checks /status.php endpoint, HTTP code, response time.

SCRIPT_NAME="$(basename "$0")"
URL=""
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --url <nextcloud_url> [OPTIONS]

Options:
  --url <url>     Nextcloud base URL, e.g. http://192.168.0.50:8080 (required)
  --output <file> Save Markdown report (optional)
  --help          Show this help

Examples:
  $SCRIPT_NAME --url http://192.168.0.50:8080
  $SCRIPT_NAME --url https://95.163.176.103:8443 --output /tmp/nc-smoke.md
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
        --url)    URL="${2:-}"; shift 2 ;;
        --output) OUTPUT="${2:-}"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *)        echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$URL" ]]; then
    echo "ERROR: --url is required" >&2; usage >&2; exit 1
fi

check_deps

# Normalize URL (strip trailing slash)
URL="${URL%/}"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
PASS=0
FAIL=0

echo "=== Nextcloud Smoke Test: $URL ($TIMESTAMP) ==="
echo ""

check_endpoint() {
    local label="$1" path="$2" expected_code="${3:-200}" insecure="${4:-}"
    local curl_opts=("-o" "/dev/null" "-sf" "-w" "%{http_code} %{time_total}" "--max-time" "15")
    [[ -n "$insecure" ]] && curl_opts+=("-k")

    local result http_code response_time
    result="$(curl "${curl_opts[@]}" "${URL}${path}" 2>/dev/null || echo "000 0")"
    http_code="${result%% *}"
    response_time="${result##* }"

    if [[ "$http_code" == "$expected_code" ]] || [[ "$http_code" =~ ^(200|201|204|301|302)$ && "$expected_code" == "2xx" ]]; then
        echo "PASS: $label -> HTTP $http_code (${response_time}s)"
        PASS=$((PASS + 1))
        REPORT_LINE="| $label | PASS | HTTP $http_code | ${response_time}s |"
    else
        echo "FAIL: $label -> HTTP $http_code (expected: $expected_code)"
        FAIL=$((FAIL + 1))
        REPORT_LINE="| $label | FAIL | HTTP $http_code (expected $expected_code) | ${response_time}s |"
    fi
    REPORT_LINES+=("$REPORT_LINE")
}

REPORT_LINES=()

# Detect HTTP vs HTTPS
INSECURE=""
if [[ "$URL" == https://* ]]; then
    INSECURE="1"
    echo "Note: HTTPS detected, using -k (self-signed cert accepted)"
fi

check_endpoint "status.php" "/status.php" "200" "$INSECURE"
check_endpoint "root redirect" "/" "302" "$INSECURE"

# Check status.php content
STATUS_BODY="$(curl -sf -k --max-time 10 "${URL}/status.php" 2>/dev/null || echo "")"
if echo "$STATUS_BODY" | grep -q '"installed":true'; then
    echo "PASS: Nextcloud reports installed=true"
    PASS=$((PASS + 1))
    REPORT_LINES+=("| installed=true | PASS | $(echo "$STATUS_BODY" | tr -d '\n' | head -c 80) | -- |")
elif echo "$STATUS_BODY" | grep -q '"installed"'; then
    echo "WARN: Nextcloud reports installed=false (setup required)"
    REPORT_LINES+=("| installed=true | WARN | installed=false in status | -- |")
else
    echo "WARN: Cannot parse status.php response"
    REPORT_LINES+=("| installed=true | WARN | unreadable response | -- |")
fi

echo ""
echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Nextcloud Smoke Test Report"
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
