#!/usr/bin/env bash
# Offline readiness check for Sber-era cutover (no Jetson required).
# Usage: bash scripts/sber/preflight_sber_pack.sh
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2

FAIL=0
ok()  { printf '  OK  %s\n' "$1"; }
bad() { printf '  BAD %s\n' "$1"; FAIL=$((FAIL + 1)); }

need_file() {
  if [[ -f "$1" ]]; then ok "$1"
  else bad "missing $1"
  fi
}

echo "=== Sber offline pack preflight ==="

need_file "config/sber.env.snippet"
need_file "config/certs/russian_trusted_bundle.pem"
need_file "config/.env.example"
need_file "docs/plans/DEPLOY_W1_GIGA_CUTOVER.md"
need_file "docs/plans/OFFLINE_SBER_READY_PACK.md"
need_file "docs/integrations/sber/README.md"
need_file "docs/integrations/sber/CONSOLE_CHECKLIST.md"
need_file "docs/decisions/ADR-0007-node-model-jetson-sor-cloud-edge.md"
need_file "docs/decisions/ADR-0008-llm-routing-giga-first.md"
need_file "docs/decisions/ADR-0009-backup-ssd-hdd-s3.md"
need_file "services/llm-gateway/app/main.py"
need_file "scripts/backup/immich_hdd_second_copy.sh"
need_file "systemd/nas_jetson_nano-immich-hdd-copy.service"
need_file "systemd/nas_jetson_nano-immich-hdd-copy.timer"
need_file "scripts/sber/verify_gateway.sh"
need_file "scripts/sber/check_gigachat_balance.sh"
need_file "scripts/sber/install_immich_hdd_timer.sh"
need_file "scripts/backup/restic_s3_cloudru_example.sh"
need_file "tests/llm_gateway/test_sber_routing.py"

# Code markers
if grep -q 'api.giga.chat' services/llm-gateway/app/main.py; then
  ok "gateway default base api.giga.chat"
else
  bad "gateway missing api.giga.chat"
fi
if grep -q 'cloudru' services/llm-gateway/app/main.py; then
  ok "gateway has cloudru provider"
else
  bad "gateway missing cloudru"
fi
if grep -q 'talk_bot_llm_provider' services/nas_jetson_nano-api/app/config.py; then
  ok "talk bot provider setting"
else
  bad "talk bot provider missing"
fi
if grep -q 'LLM_GIGA_FALLBACK_DEEPSEEK' config/.env.example; then
  ok "env.example fallback flag"
else
  bad "env.example missing fallback"
fi

# Snippet must not contain real-looking secrets
if grep -EEq 'GIGACHAT_AUTH_KEY=[A-Za-z0-9+/]{20,}' config/sber.env.snippet; then
  bad "snippet looks like it contains a real AUTH_KEY"
else
  ok "snippet has no embedded auth key value"
fi

# Optional unit tests
if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
  PY=$(command -v python3 2>/dev/null || command -v python)
  if "$PY" -m pytest tests/llm_gateway/test_sber_routing.py -q --tb=no >/tmp/sber_pytest.out 2>&1; then
    ok "unit tests passed"
  else
    bad "unit tests failed (see pytest output)"
    tail -20 /tmp/sber_pytest.out 2>/dev/null || true
  fi
else
  printf '  WARN python not available — skip tests\n'
fi

echo "=== result: FAIL=$FAIL ==="
exit "$FAIL"
