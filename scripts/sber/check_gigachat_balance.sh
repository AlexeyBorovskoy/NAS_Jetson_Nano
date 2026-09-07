#!/usr/bin/env bash
# Poll GigaChat balance via local gateway.
# Env: LLM_GATEWAY_URL=http://127.0.0.1:8090
set -euo pipefail

URL="${LLM_GATEWAY_URL:-http://127.0.0.1:8090}"
URL="${URL%/}"

code=$(curl -sS -o /tmp/giga_balance.json -w "%{http_code}" \
  "${URL}/v1/provider/gigachat/balance" || true)

echo "HTTP $code"
if [[ "$code" != "200" ]]; then
  head -c 400 /tmp/giga_balance.json 2>/dev/null || true
  echo
  exit 1
fi

head -c 4000 /tmp/giga_balance.json
echo
echo "balance poll OK"
exit 0
