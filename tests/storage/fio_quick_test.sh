#!/usr/bin/env bash
set -euo pipefail
# fio_quick_test.sh -- safe sequential I/O benchmark using fio
# ONLY writes to specified test directory.
# NEVER touches /, /home, /etc, /var, /mnt/storage root directly.
# Requires explicit --confirm flag to run.

SCRIPT_NAME="$(basename "$0")"
TEST_DIR=""
TEST_SIZE="512m"
OUTPUT=""
CONFIRM="no"

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --directory <path> [OPTIONS]

Options:
  --directory <path>  Directory to run fio test in (required).
                      Must NOT be /, /home, /etc, /var, /boot, /sys, /proc.
                      Recommended: /mnt/storage/test_fio
  --size <size>       Test file size, e.g. 256m, 512m, 1g (default: 512m)
  --output <file>     Save Markdown report (optional)
  --confirm           Required flag to actually run (safety gate)
  --help              Show this help

Examples:
  $SCRIPT_NAME --directory /mnt/storage/test_fio --confirm
  $SCRIPT_NAME --directory /mnt/storage/test_fio --size 256m --confirm --output /tmp/fio.md

WARNING: This creates and then deletes test files in --directory.
         Never run on directories containing real data.
EOF
}

check_deps() {
    if ! command -v fio >/dev/null 2>&1; then
        echo "ERROR: fio not found. Install: apt-get install fio" >&2
        exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --directory) TEST_DIR="${2:-}"; shift 2 ;;
        --size)      TEST_SIZE="${2:-512m}"; shift 2 ;;
        --output)    OUTPUT="${2:-}"; shift 2 ;;
        --confirm)   CONFIRM="yes"; shift ;;
        --help|-h)   usage; exit 0 ;;
        *)           echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$TEST_DIR" ]]; then
    echo "ERROR: --directory is required" >&2; usage >&2; exit 1
fi

# Safety: reject dangerous directories
DANGEROUS_DIRS=("/" "/home" "/etc" "/var" "/boot" "/sys" "/proc" "/dev" "/run" "/tmp" "/usr" "/lib" "/bin" "/sbin")
for DANGER in "${DANGEROUS_DIRS[@]}"; do
    if [[ "$(realpath "$TEST_DIR" 2>/dev/null || echo "$TEST_DIR")" == "$DANGER" ]]; then
        echo "ERROR: Cannot run fio test in $TEST_DIR (protected directory)" >&2
        exit 1
    fi
done

# Safety: require --confirm
if [[ "$CONFIRM" != "yes" ]]; then
    echo "ERROR: Add --confirm flag to actually run the test." >&2
    echo "       This will create and delete test files in: $TEST_DIR" >&2
    exit 1
fi

check_deps

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
echo "=== NAS_Jetson_Nano fio Quick Test ($TIMESTAMP) ==="
echo "Directory: $TEST_DIR"
echo "Test size: $TEST_SIZE"
echo ""

# Create test directory (only the specific test dir, not parents beyond storage)
mkdir -p "$TEST_DIR"

TESTFILE="${TEST_DIR}/fio_test_$(date +%Y%m%d_%H%M%S)"
RESULTS=()

cleanup() {
    echo ""
    echo "Cleaning up test files..."
    rm -f "${TESTFILE}"
    rm -f "${TESTFILE}.0" "${TESTFILE}".*
    echo "Cleanup done."
}
trap cleanup EXIT

echo "--- Sequential WRITE ---"
WRITE_RESULT="$(fio \
    --name=seqwrite \
    --ioengine=libaio \
    --rw=write \
    --bs=1m \
    --size="$TEST_SIZE" \
    --numjobs=1 \
    --iodepth=4 \
    --runtime=30 \
    --time_based \
    --filename="$TESTFILE" \
    --output-format=json \
    2>/dev/null)"

WRITE_BW="$(echo "$WRITE_RESULT" | python3 -c "
import sys, json
d=json.load(sys.stdin)
bw=d['jobs'][0]['write']['bw']
print(f'{bw/1024:.1f} MB/s')
" 2>/dev/null || echo "unknown")"
echo "Sequential write: $WRITE_BW"
RESULTS+=("Sequential Write: $WRITE_BW")

echo ""
echo "--- Sequential READ ---"
READ_RESULT="$(fio \
    --name=seqread \
    --ioengine=libaio \
    --rw=read \
    --bs=1m \
    --size="$TEST_SIZE" \
    --numjobs=1 \
    --iodepth=4 \
    --runtime=30 \
    --time_based \
    --filename="$TESTFILE" \
    --output-format=json \
    2>/dev/null)"

READ_BW="$(echo "$READ_RESULT" | python3 -c "
import sys, json
d=json.load(sys.stdin)
bw=d['jobs'][0]['read']['bw']
print(f'{bw/1024:.1f} MB/s')
" 2>/dev/null || echo "unknown")"
echo "Sequential read: $READ_BW"
RESULTS+=("Sequential Read: $READ_BW")

echo ""
echo "=== Results ==="
for r in "${RESULTS[@]}"; do
    echo "  $r"
done

echo ""
echo "Reference (USB 3.0 SSD via RTL9210B-CG):"
echo "  Write: ~250-350 MB/s expected"
echo "  Read:  ~300-400 MB/s expected"
echo "  < 50 MB/s likely means USB 2.0 port or device issue"

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# fio Quick Test Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Directory:** $TEST_DIR"
        echo "**Test size:** $TEST_SIZE"
        echo ""
        echo "## Results"
        echo ""
        for r in "${RESULTS[@]}"; do
            echo "- $r"
        done
        echo ""
        echo "## Reference (USB 3.0 SSD)"
        echo "- Write: ~250-350 MB/s"
        echo "- Read: ~300-400 MB/s"
        echo "- < 50 MB/s = USB 2.0 or device issue"
    } > "$OUTPUT"
    echo "Report saved: $OUTPUT"
fi

exit 0
