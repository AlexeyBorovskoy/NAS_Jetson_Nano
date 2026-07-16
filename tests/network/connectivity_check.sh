#!/usr/bin/env bash
set -euo pipefail
# connectivity_check.sh -- ping and HTTP connectivity check for NAS_Jetson_Nano
# Does NOT perform aggressive scanning or nmap.

SCRIPT_NAME="$(basename "$0")"
HOST=""
URL=""
DNS_NAME=""
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --host <ip_or_hostname> [OPTIONS]

Options:
  --host <ip>          Target host to ping (required)
  --url <url>          HTTP URL to check (optional)
  --dns-name <name>    DNS name to resolve (optional)
  --output <file>      Save Markdown report to file (optional)
  --help               Show this help

Examples:
  $SCRIPT_NAME --host 192.168.0.50
  $SCRIPT_NAME --host 192.168.0.50 --url http://192.168.0.50:8080/status.php
  $SCRIPT_NAME --host 193.8.215.130 --url http://193.8.215.130:8080/ --output /tmp/report.md
EOF
}

check_deps() {
    local missing=0
    for dep in ping curl; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            echo "ERROR: dependency not found: $dep" >&2
            missing=1
        fi
    done
    if [[ "$missing" -ne 0 ]]; then
        exit 2
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)     HOST="${2:-}"; shift 2 ;;
        --url)      URL="${2:-}"; shift 2 ;;
        --dns-name) DNS_NAME="${2:-}"; shift 2 ;;
        --output)   OUTPUT="${2:-}"; shift 2 ;;
        --help|-h)  usage; exit 0 ;;
        *)          echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$HOST" ]]; then
    echo "ERROR: --host is required" >&2
    usage >&2
    exit 1
fi

check_deps

PASS=0
FAIL=0
REPORT_LINES=()

add_line() {
    REPORT_LINES+=("$1")
}

result() {
    local label="$1" status="$2" detail="${3:-}"
    if [[ "$status" == "PASS" ]]; then
        PASS=$((PASS + 1))
        add_line "| $label | PASS | $detail |"
    else
        FAIL=$((FAIL + 1))
        add_line "| $label | FAIL | $detail |"
    fi
}

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
echo "=== NAS_Jetson_Nano Connectivity Check: $HOST ($TIMESTAMP) ==="

# 1. Ping
echo ""
echo "--- Ping: $HOST ---"
if ping -c 3 -W 3 "$HOST" >/dev/null 2>&1; then
    RTT="$(ping -c 3 -W 3 "$HOST" 2>/dev/null | grep 'avg' | awk -F'/' '{print $5}' || echo '?')"
    echo "PASS: $HOST is reachable (avg RTT: ${RTT}ms)"
    result "Ping $HOST" "PASS" "avg RTT: ${RTT}ms"
else
    echo "FAIL: $HOST is not reachable"
    result "Ping $HOST" "FAIL" "no response"
fi

# 2. HTTP check
if [[ -n "$URL" ]]; then
    echo ""
    echo "--- HTTP: $URL ---"
    HTTP_CODE="000"
    RESPONSE_TIME="0"
    HTTP_CODE="$(curl -o /dev/null -sf -w '%{http_code}' --max-time 10 "$URL" 2>/dev/null || echo "000")"
    RESPONSE_TIME="$(curl -o /dev/null -sf -w '%{time_total}' --max-time 10 "$URL" 2>/dev/null || echo "0")"
    if [[ "$HTTP_CODE" =~ ^(200|201|204|301|302|304)$ ]]; then
        echo "PASS: HTTP $HTTP_CODE (${RESPONSE_TIME}s)"
        result "HTTP $URL" "PASS" "HTTP $HTTP_CODE in ${RESPONSE_TIME}s"
    else
        echo "FAIL: HTTP $HTTP_CODE"
        result "HTTP $URL" "FAIL" "HTTP $HTTP_CODE"
    fi
fi

# 3. DNS check
if [[ -n "$DNS_NAME" ]]; then
    echo ""
    echo "--- DNS: $DNS_NAME ---"
    if command -v host >/dev/null 2>&1; then
        if host "$DNS_NAME" >/dev/null 2>&1; then
            RESOLVED="$(host "$DNS_NAME" 2>/dev/null | grep 'has address' | head -1 | awk '{print $NF}' || echo '?')"
            echo "PASS: $DNS_NAME resolves to $RESOLVED"
            result "DNS $DNS_NAME" "PASS" "resolves to $RESOLVED"
        else
            echo "FAIL: $DNS_NAME does not resolve"
            result "DNS $DNS_NAME" "FAIL" "no resolution"
        fi
    elif command -v nslookup >/dev/null 2>&1; then
        if nslookup "$DNS_NAME" >/dev/null 2>&1; then
            echo "PASS: $DNS_NAME resolves (nslookup)"
            result "DNS $DNS_NAME" "PASS" "resolves (nslookup)"
        else
            echo "FAIL: $DNS_NAME does not resolve"
            result "DNS $DNS_NAME" "FAIL" "no resolution"
        fi
    else
        echo "INFO: no DNS tool available (host/nslookup not found)"
        result "DNS $DNS_NAME" "PASS" "skipped (no dns tool)"
    fi
fi

echo ""
echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="

# Generate Markdown report
if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Connectivity Check Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Target:** $HOST"
        echo ""
        echo "| Check | Result | Details |"
        echo "|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do
            echo "$line"
        done
        echo ""
        echo "**Total:** PASS=$PASS  FAIL=$FAIL"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
