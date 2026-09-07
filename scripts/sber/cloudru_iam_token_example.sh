#!/usr/bin/env bash
# EXAMPLE — obtain Cloud.ru IAM token from access key pair (docs quickstart).
# Does NOT store secrets. Read Key ID/Secret from env only.
#
#   export CLOUDRU_KEY_ID='...'
#   export CLOUDRU_KEY_SECRET='...'
#   bash scripts/sber/cloudru_iam_token_example.sh
#
# Token is printed once to stdout — do not log to shared files.
set -euo pipefail

: "${CLOUDRU_KEY_ID:?}"
: "${CLOUDRU_KEY_SECRET:?}"

# Official: https://cloud.ru/docs/console_api/ug/topics/quickstart
resp=$(curl -sS -X POST \
  --data-urlencode "grant_type=access_key" \
  --data-urlencode "client_id=${CLOUDRU_KEY_ID}" \
  --data-urlencode "client_secret=${CLOUDRU_KEY_SECRET}" \
  "https://auth.iam.cloud.ru/auth/system/openid/token")

# Print only metadata + token length (avoid accidental board paste of full token)
python3 - <<PY || python - <<PY
import json, os, sys
raw = '''$resp'''
try:
    d = json.loads(raw)
except Exception as e:
    print("non-json response", raw[:200])
    sys.exit(1)
tok = d.get("access_token") or d.get("accessToken") or ""
print("keys:", sorted(d.keys()))
print("token_len:", len(tok))
print("expires_in:", d.get("expires_in") or d.get("expiresIn"))
if os.environ.get("PRINT_TOKEN") == "1":
    print(tok)
else:
    print("(set PRINT_TOKEN=1 to print token once)")
PY
