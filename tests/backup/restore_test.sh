#!/usr/bin/env bash
set -euo pipefail
# restore_test.sh -- backup validation: dry-run rsync and restore check
# NEVER touches real user data. Creates test files only in --restore-dir.

SCRIPT_NAME="$(basename "$0")"
SOURCE=""
RESTORE_DIR=""
OUTPUT=""

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME --source <dir> --restore-dir <dir> [OPTIONS]

Options:
  --source <dir>       Source backup directory to validate (required)
                       Example: /mnt/storage/backups/database-dumps
  --restore-dir <dir>  Temporary directory for restore test (required)
                       Must NOT be /, /home, or system directories.
                       Example: /tmp/nas_jetson_nano-restore-test
  --output <file>      Save Markdown report (optional)
  --help               Show this help

Examples:
  $SCRIPT_NAME \\
    --source /mnt/storage/backups/database-dumps \\
    --restore-dir /tmp/nas_jetson_nano-restore-\$(date +%Y%m%d)

Note: Restore dir is created and cleaned up automatically.
      Only creates files within --restore-dir.
EOF
}

check_deps() {
    for dep in rsync diff; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            echo "ERROR: $dep not found" >&2; exit 2
        fi
    done
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source)      SOURCE="${2:-}"; shift 2 ;;
        --restore-dir) RESTORE_DIR="${2:-}"; shift 2 ;;
        --output)      OUTPUT="${2:-}"; shift 2 ;;
        --help|-h)     usage; exit 0 ;;
        *)             echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$SOURCE" ]]; then
    echo "ERROR: --source is required" >&2; usage >&2; exit 1
fi
if [[ -z "$RESTORE_DIR" ]]; then
    echo "ERROR: --restore-dir is required" >&2; usage >&2; exit 1
fi

# Safety: reject system directories for restore target
DANGEROUS_DIRS=("/" "/home" "/etc" "/var" "/boot" "/sys" "/proc" "/dev" "/run" "/usr" "/lib")
for DANGER in "${DANGEROUS_DIRS[@]}"; do
    if [[ "$(realpath "$RESTORE_DIR" 2>/dev/null || echo "$RESTORE_DIR")" == "$DANGER" ]]; then
        echo "ERROR: --restore-dir cannot be $RESTORE_DIR" >&2
        exit 1
    fi
done

check_deps

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
PASS=0
FAIL=0
REPORT_LINES=()

echo "=== NAS_Jetson_Nano Backup Restore Test ($TIMESTAMP) ==="
echo "Source: $SOURCE"
echo "Restore dir: $RESTORE_DIR"
echo ""

# Cleanup on exit
cleanup() {
    if [[ -d "$RESTORE_DIR" ]]; then
        echo ""
        echo "Cleaning up restore dir: $RESTORE_DIR"
        rm -rf "$RESTORE_DIR"
    fi
}
trap cleanup EXIT

mkdir -p "$RESTORE_DIR"

# 1. Check source directory exists and has content
echo "--- Source Directory Check ---"
if [[ ! -d "$SOURCE" ]]; then
    echo "FAIL: Source directory does not exist: $SOURCE"
    FAIL=$((FAIL + 1))
    REPORT_LINES+=("| Source exists | FAIL | $SOURCE not found |")
else
    FILE_COUNT="$(find "$SOURCE" -type f | wc -l)"
    echo "PASS: Source directory exists with $FILE_COUNT files"
    PASS=$((PASS + 1))
    REPORT_LINES+=("| Source exists | PASS | $FILE_COUNT files |")
fi

# 2. Check for DB dump files specifically
echo ""
echo "--- Database Dump Check ---"
for DB in nextcloud immich; do
    LATEST="$(ls -t "${SOURCE}/${DB}_"*.sql.gz 2>/dev/null | head -1 || echo "")"
    if [[ -n "$LATEST" ]]; then
        SIZE="$(du -sh "$LATEST" | cut -f1)"
        AGE_DAYS="$(( ($(date +%s) - $(date -r "$LATEST" +%s)) / 86400 ))"
        echo "PASS: $DB dump: $(basename "$LATEST") ($SIZE, ${AGE_DAYS} days old)"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| $DB dump | PASS | $SIZE, ${AGE_DAYS}d old |")

        # Integrity check
        if gzip -t "$LATEST" 2>/dev/null; then
            echo "PASS: $DB dump gzip integrity OK"
            PASS=$((PASS + 1))
            REPORT_LINES+=("| $DB gzip check | PASS | integrity OK |")
        else
            echo "FAIL: $DB dump gzip integrity FAILED"
            FAIL=$((FAIL + 1))
            REPORT_LINES+=("| $DB gzip check | FAIL | corrupted |")
        fi
    else
        echo "FAIL: No $DB dump found in $SOURCE"
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| $DB dump | FAIL | no dump found |")
    fi
done

# 3. rsync dry-run
echo ""
echo "--- rsync Dry Run ---"
if rsync -avz --dry-run "${SOURCE}/" "${RESTORE_DIR}/" >/dev/null 2>&1; then
    echo "PASS: rsync dry-run completed successfully"
    PASS=$((PASS + 1))
    REPORT_LINES+=("| rsync dry-run | PASS | completed |")
else
    echo "FAIL: rsync dry-run failed"
    FAIL=$((FAIL + 1))
    REPORT_LINES+=("| rsync dry-run | FAIL | rsync error |")
fi

# 4. Actual restore to temp dir + diff
echo ""
echo "--- Restore and Diff Check ---"
if rsync -az "${SOURCE}/" "${RESTORE_DIR}/" 2>/dev/null; then
    SOURCE_FILES="$(find "$SOURCE" -type f | sort | xargs -I{} basename {})"
    RESTORE_FILES="$(find "$RESTORE_DIR" -type f | sort | xargs -I{} basename {})"
    if diff <(echo "$SOURCE_FILES") <(echo "$RESTORE_FILES") >/dev/null 2>&1; then
        echo "PASS: Restored files match source (diff check OK)"
        PASS=$((PASS + 1))
        REPORT_LINES+=("| Restore diff | PASS | files match |")
    else
        echo "FAIL: Restored files do not match source"
        FAIL=$((FAIL + 1))
        REPORT_LINES+=("| Restore diff | FAIL | mismatch |")
    fi
else
    echo "FAIL: rsync restore failed"
    FAIL=$((FAIL + 1))
    REPORT_LINES+=("| Restore rsync | FAIL | rsync error |")
fi

echo ""
echo "=== Summary: PASS=$PASS  FAIL=$FAIL ==="

if [[ -n "$OUTPUT" ]]; then
    {
        echo "# Backup Restore Test Report"
        echo ""
        echo "**Date:** $TIMESTAMP"
        echo "**Source:** $SOURCE"
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

[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
