#!/usr/bin/env bash
# test_dump_validate.sh — F-01: reject empty/corrupt gzip dumps (no Docker, no real data)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NAS_BACKUP_LIB_ONLY=1
# shellcheck source=../../scripts/backup/backup_databases.sh
source "${ROOT}/scripts/backup/backup_databases.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

FAIL=0
pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL + 1)); }

# ~20-byte gzip of empty stdin — same class as 2026-09-08 04:04 dumps
: | gzip > "${TMP}/empty.sql.gz"
if validate_dump_gz "${TMP}/empty.sql.gz"; then
    fail "empty gzip must be rejected"
else
    pass "empty gzip rejected"
fi

echo "not-gzip" > "${TMP}/corrupt.sql.gz"
if validate_dump_gz "${TMP}/corrupt.sql.gz"; then
    fail "corrupt gzip must be rejected"
else
    pass "corrupt gzip rejected"
fi

if validate_dump_gz "${TMP}/missing.sql.gz"; then
    fail "missing file must be rejected"
else
    pass "missing file rejected"
fi

# urandom does not collapse under gzip (zeros compress below MIN_DUMP_BYTES)
dd if=/dev/urandom bs=1024 count=3 status=none | gzip > "${TMP}/ok.sql.gz"
if validate_dump_gz "${TMP}/ok.sql.gz"; then
    pass "payload gzip accepted"
else
    fail "payload gzip must be accepted"
fi

echo "=== test_dump_validate: FAIL=${FAIL} ==="
exit "${FAIL}"
