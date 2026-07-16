#!/usr/bin/env bash
set -euo pipefail
# benchmark_io.sh — sequential I/O benchmark for NAS_Jetson_Nano storage (USB HDD / SSD)
# Reference speeds (JetsonHacks): microSD ~87 MB/s, USB HDD ~80-120 MB/s, USB SSD ~367 MB/s

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"
[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"

STORAGE_ROOT="${STORAGE_ROOT:-/mnt/storage}"
LOG_DIR="${STORAGE_ROOT}/logs/health"
TEST_FILE="${STORAGE_ROOT}/.benchmark_tmp"
TEST_SIZE="${BENCHMARK_SIZE_MB:-512}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "${LOG_DIR}"
REPORT="${LOG_DIR}/benchmark-$(date +%Y%m%d-%H%M%S).txt"

log "=== NAS_Jetson_Nano I/O Benchmark === (${TEST_SIZE}MB on ${STORAGE_ROOT})"
{
    echo "Benchmark: $(date)"
    echo "Device: ${STORAGE_ROOT}"
    df -h "${STORAGE_ROOT}" | tail -1
    echo ""

    echo "--- Sequential WRITE ---"
    dd if=/dev/zero of="${TEST_FILE}" bs=1M count="${TEST_SIZE}" conv=fdatasync 2>&1 | tail -1

    # Drop page cache if root
    if [[ "$(id -u)" -eq 0 ]]; then
        sync
        echo 3 > /proc/sys/vm/drop_caches
    fi

    echo ""
    echo "--- Sequential READ ---"
    dd if="${TEST_FILE}" of=/dev/null bs=1M 2>&1 | tail -1
} | tee "${REPORT}"

# Cleanup test file
[[ -f "${TEST_FILE}" ]] && unlink "${TEST_FILE}"

log "Report saved: ${REPORT}"
