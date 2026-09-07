#!/usr/bin/env bash
# Smoke Cloud.ru Foundation Models from workstation (Jetson not required).
# Usage:
#   export CLOUDRU_FM_API_KEY='...'   # never commit
#   bash scripts/sber/smoke_cloudru_fm.sh
set -euo pipefail

: "${CLOUDRU_FM_API_KEY:?set CLOUDRU_FM_API_KEY}"
BASE="${CLOUDRU_FM_BASE_URL:-https://foundation-models.api.cloud.ru/v1}"
MODEL="${CLOUDRU_FM_MODEL:-GigaChat/GigaChat-2-Max}"

code=$(curl -sS -o /tmp/fm_smoke.json -w "%{http_code}" \
  -H "Authorization: Bearer ${CLOUDRU_FM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":8}" \
  "${BASE%/}/chat/completions")

echo "HTTP $code model=$MODEL"
head -c 400 /tmp/fm_smoke.json
echo
[[ "$code" == "200" ]] || exit 1
echo "FM smoke OK"
