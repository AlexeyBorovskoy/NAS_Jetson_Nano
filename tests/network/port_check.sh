#!/usr/bin/env bash
set -euo pipefail
# port_check.sh -- check that TCP ports are reachable on a host
# Uses nc (netcat) only. Does NOT run nmap or aggressive scanning.

SCRIPT_NAME="$(basename "$0")"
HOST=""
PORTS=""
OUTPUT=""
TIMEOUT=5

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --host <host> --ports <port_list> [OPTIONS]

Options:
  --host <ip>           Target host (required)
  --ports <list>        Comma-separated port list, e.g. "22,80,443" (required)
  --timeout <secs>      Connection timeout in seconds (default: 5)
  --output <file>       Save Markdown report (optional)
  --help                Show this help

Examples:
  $SCRIPT_NAME --host 192.168.0.50 --ports "22,8080,2283"
  $SCRIPT_NAME --host 192.168.0.50 --ports "22,8080,2283,8090,19999,3001,9000" --output /tmp/ports.md
EOF
}

check_deps() {
    if ! command -v nc >/dev/null 2>&1; then
        echo "ERROR: nc (netcat) not found. Install: apt-get install netcat-openbsd" >&2
        exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)    HOST="${2:-}"; shift 2 ;;
        --ports)   PORTS="${2:-}"; shift 2 ;;
        --timeout) TIMEOUT="${2:-5}"; shift 2 ;;
        --output)  OUTPUT="${2:-}"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *)         echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$HOST" ]]; then
    echo "ERROR: --host is required" >&2; usage >&2; exit 1
fi
if [[ -z "$PORTS" ]]; then
    echo "ERROR: --ports is required" >&2; usage >&2; exit 1
fi

check_deps

PASS=0
FAIL=0
REPORT_LINES=()
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

echo "=== NAS_Jetson_Nano Port Check: $HOST ($TIMESTAMP) ==="
echo "Ports: $PORTS"
echo ""

IFS=',' read -ra PORT_LIST <<< "$PORTS"

for PORT in "${PORT_LIST[@]}"; do
    PORT="${PORT// /}"  # trim whitespace
    if [[ -z "$PORT" ]]; then continue; fi

    if nc -vz -w "$TIMEOUT" "$HOST" "$PORT" >/dev/null 2>&1; then
        echo "PASS: $HOST:$PORT is open"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| $HOST:$PORT | OPEN | |")
    else
        echo "FAIL: $HOST:$PORT is closed or unreachable"
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| $HOST:$PORT | CLOSED | |")
    fi
done

echo ""
echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Port Check Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Target:** $HOST"
        echo "**Ports:** $PORTS"
        echo ""
        echo "| Endpoint | Status | Notes |"
        echo "|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do
            echo "$line"
        done
        echo ""
        echo "**Total:** OPEN=$PASS  CLOSED=$FAIL"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
