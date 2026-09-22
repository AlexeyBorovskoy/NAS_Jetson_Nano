#!/usr/bin/env bash
# Diagnose restic ↔ Cloud.ru Object Storage (L2).
# Run on Jetson. Never prints keys/passwords.
# Usage: sudo bash scripts/backup/restic_s3_cloudru_probe.sh
set -euo pipefail
ENVF="${NAS_ENV_FILE:-/home/admin/nasa/config/.env}"
[[ -r "$ENVF" ]] || { echo "cannot read $ENVF"; exit 1; }

eval "$(python3 - "$ENVF" <<'PY'
import sys
p=sys.argv[1]
keep=("AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","CLOUDRU_S3_BUCKET",
      "CLOUDRU_S3_ENDPOINT","CLOUDRU_S3_REGION","RESTIC_CLOUDRU_PASSWORD",
      "RESTIC_REPOSITORY")
def q(s):
    return "'"+s.replace("'","'\\''")+"'"
for line in open(p):
    line=line.strip().strip("\r")
    if not line or line.startswith("#") or "=" not in line:
        continue
    k,v=line.split("=",1)
    v=v.strip().strip('"').strip("'")
    if k in keep and v:
        print("export %s=%s" % (k, q(v)))
PY
)"

export AWS_DEFAULT_REGION="${CLOUDRU_S3_REGION:-ru-central-1}"
export RESTIC_PASSWORD="${RESTIC_PASSWORD:-${RESTIC_CLOUDRU_PASSWORD:-}}"
: "${AWS_ACCESS_KEY_ID:?}"
: "${AWS_SECRET_ACCESS_KEY:?}"
: "${RESTIC_PASSWORD:?}"
EP="${CLOUDRU_S3_ENDPOINT:-https://s3.cloud.ru}"
BU="${CLOUDRU_S3_BUCKET:-nas-immich-offsite}"
REG="${AWS_DEFAULT_REGION}"

echo "restic=$(restic version)"
echo "endpoint=$EP bucket=$BU region=$REG key_len=${#AWS_ACCESS_KEY_ID} colon=$(awk -v k="$AWS_ACCESS_KEY_ID" 'BEGIN{print gsub(/:/,"",k)}')"

try() {
  local name="$1"; shift
  echo "===== $name ====="
  set +e
  timeout 45 restic "$@" snapshots 2>&1 \
    | grep -vE 'AWS_|SECRET|PASSWORD|KeyId|Authorization|Credential=' \
    | tail -n 15
  echo "exit=$?"
  set -e
}

# Cloud.ru Object Storage is path-style. dns/virtual-host often → HTTP 400.
try "path https /immich" -o s3.bucket-lookup=path -o "s3.region=$REG" -r "s3:${EP}/${BU}/immich"
try "dns https /immich"  -o s3.bucket-lookup=dns  -o "s3.region=$REG" -r "s3:${EP}/${BU}/immich"
try "path https bucket-root" -o s3.bucket-lookup=path -o "s3.region=$REG" -r "s3:${EP}/${BU}"
try "path host-only /immich" -o s3.bucket-lookup=path -o "s3.region=$REG" -r "s3:s3.cloud.ru/${BU}/immich"

echo "NOTE: after 2026-09-21 prefix immich/ was emptied — even a good client gets no restic config."
echo "A 400 on Stat is a client/style bug; 404/NoSuchKey after path-style means 'empty, need restic init'."
