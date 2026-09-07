#!/usr/bin/env bash
# Post-deploy verify on Jetson (or any host where gateway listens).
# Usage: bash scripts/sber/verify_gateway.sh [BASE_URL]
# Default BASE_URL=http://127.0.0.1:8090
set -euo pipefail

BASE="${1:-http://127.0.0.1:8090}"
BASE="${BASE%/}"

echo "=== health ==="
curl -fsS "$BASE/health" | tee /tmp/llm_health.json
echo

python3 - <<'PY' || python - <<'PY'
import json, sys
h = json.load(open("/tmp/llm_health.json", encoding="utf-8"))
assert h.get("status") == "ok", h
prov = h.get("provider", "")
print("default provider:", prov)
print("providers:", h.get("providers"))
print("prefer_local:", h.get("prefer_local"))
print("giga base:", h.get("gigachat_base"))
print("giga model:", h.get("gigachat_model"))
if h.get("prefer_local") is True:
    print("WARN: prefer_local still true (ADR-0008 wants false in prod)")
if "giga.chat" not in str(h.get("gigachat_base", "")):
    print("WARN: gigachat_base is not api.giga.chat — check env")
PY

echo "=== chat gigachat ==="
code=$(curl -sS -o /tmp/llm_chat.json -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Ответь одним словом: ок","provider":"gigachat","user":"admin"}' \
  "$BASE/v1/chat" || true)
echo "HTTP $code"
head -c 500 /tmp/llm_chat.json 2>/dev/null; echo

if [[ "$code" == "200" ]]; then
  echo "=== balance (if key set) ==="
  curl -sS "$BASE/v1/provider/gigachat/balance" | head -c 800 || true
  echo
fi

echo "=== done ==="
