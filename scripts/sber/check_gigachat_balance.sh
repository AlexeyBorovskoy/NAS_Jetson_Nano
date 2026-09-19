#!/usr/bin/env bash
# Poll GigaChat balance via local gateway.
# Env: LLM_GATEWAY_URL=http://127.0.0.1:8090
#      GIGA_BALANCE_FILE — куда сохранить ответ для алерта (E2, nas_jetson_nano-talk-alert.py).
# Файл пишется только при HTTP 200 и разбираемом JSON, атомарно. При сбое прежний
# файл остаётся и стареет — алерт через 50 ч скажет, что опрос сломан.
set -euo pipefail

URL="${LLM_GATEWAY_URL:-http://127.0.0.1:8090}"
URL="${URL%/}"
OUT="${GIGA_BALANCE_FILE:-/var/lib/nas-giga-balance/balance.json}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

code=$(curl -sS -o "$TMP" -w "%{http_code}" \
  "${URL}/v1/provider/gigachat/balance" || true)

echo "HTTP $code"
if [[ "$code" != "200" ]]; then
  head -c 400 "$TMP" 2>/dev/null || true
  echo
  exit 1
fi

head -c 4000 "$TMP"
echo

PY="$(command -v python3 || command -v python)"
"$PY" - "$TMP" "$OUT" <<'EOF'
import json, os, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as fh:
    data = json.load(fh)
data["balance"]["balance"]
d = os.path.dirname(os.path.abspath(dst))
os.makedirs(d, exist_ok=True)
tmp = dst + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False)
os.replace(tmp, dst)
EOF
echo "balance poll OK → $OUT"
exit 0
