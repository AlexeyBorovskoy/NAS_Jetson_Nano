#!/usr/bin/env bash
set -euo pipefail
# docker_healthcheck.sh -- read-only health check of NAS_Jetson_Nano Docker containers
# Does NOT restart containers. Reports status only.

SCRIPT_NAME="$(basename "$0")"
OUTPUT=""
COMPOSE_DIR=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Options:
  --compose-dir <dir>   Path to docker/compose/ directory (default: auto-detect)
  --output <file>       Save Markdown report (optional)
  --help                Show this help

Examples:
  $SCRIPT_NAME
  $SCRIPT_NAME --output /tmp/docker-health.md
EOF
}

check_deps() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "ERROR: docker not found" >&2; exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --compose-dir) COMPOSE_DIR="${2:-}"; shift 2 ;;
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

echo "=== NAS_Jetson_Nano Docker Health Check ($TIMESTAMP) ==="
echo ""

# Auto-detect compose dir
if [[ -z "$COMPOSE_DIR" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    COMPOSE_DIR="${SCRIPT_DIR}/../../docker/compose"
fi

# Expected containers
EXPECTED_CONTAINERS=(
    "homecloud_nextcloud"
    "homecloud_nextcloud_db"
    "homecloud_nextcloud_redis"
    "homecloud_immich_server"
    "homecloud_immich_microservices"
    "homecloud_immich_db"
    "homecloud_immich_redis"
    "homecloud_llm_gateway"
    "homecloud_nas_jetson_nano_api"
    "homecloud_samba"
    "homecloud_netdata"
    "homecloud_uptime_kuma"
    "homecloud_portainer"
)

echo "  Container                          Status      Health      Restarts  Started"
echo "  ---------------------------------------------------------------------------"

for cname in "${EXPECTED_CONTAINERS[@]}"; do
    status="$(docker inspect --format '{{.State.Status}}' "${cname}" 2>/dev/null || echo "missing")"
    running="$(docker inspect --format '{{.State.Running}}' "${cname}" 2>/dev/null || echo "false")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "${cname}" 2>/dev/null || echo "n/a")"
    restarts="$(docker inspect --format '{{.RestartCount}}' "${cname}" 2>/dev/null || echo "?")"
    started="$(docker inspect --format '{{.State.StartedAt}}' "${cname}" 2>/dev/null || echo "unknown")"
    started="${started:0:19}"

    printf "  %-34s %-11s %-11s %-9s %s\n" \
        "${cname}" "${status}" "${health}" "${restarts}" "${started}"

    if [[ "${status}" == "missing" ]]; then
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| ${cname} | missing | n/a | ${restarts} | FAIL: container not found |")
    elif [[ "${running}" != "true" ]]; then
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| ${cname} | ${status} | ${health} | ${restarts} | FAIL: not running |")
    elif [[ "${health}" == "unhealthy" ]]; then
        WARN=$((WARN + 1))
        REPORT_LINES+=("| ${cname} | ${status} | ${health} | ${restarts} | WARN: unhealthy |")
    else
        PASS=$((PASS + 1))
        REPORT_LINES+=("| ${cname} | ${status} | ${health} | ${restarts} | OK |")
    fi
done

echo ""
echo "--- Docker system info ---"
docker info --format 'Containers: {{.Containers}} (running: {{.ContainersRunning}}, stopped: {{.ContainersStopped}})' 2>/dev/null || true
echo ""

echo "--- Resource usage (snapshot) ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null || true
echo ""

echo "=== Summary: OK=$PASS  WARN=$WARN  FAIL=$FAIL ==="

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Docker Health Check Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo ""
        echo "| Container | Status | Health | Restarts | Notes |"
        echo "|---|---|---|---|---|"
        for line in "${REPORT_LINES[@]}"; do
            echo "$line"
        done
        echo ""
        echo "**Total:** OK=$PASS  WARN=$WARN  FAIL=$FAIL"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
if [[ "$WARN" -gt 0 ]]; then
    exit 2
fi
exit 0
