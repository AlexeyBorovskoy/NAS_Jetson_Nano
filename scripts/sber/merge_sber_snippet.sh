#!/usr/bin/env bash
# Merge config/sber.env.snippet keys into an existing .env WITHOUT wiping secrets.
# Only updates known Sber-era keys; does not remove GIGACHAT_AUTH_KEY / DEEPSEEK_*.
#
# Usage:
#   bash scripts/sber/merge_sber_snippet.sh /path/to/config/.env
#   DRY_RUN=1 bash scripts/sber/merge_sber_snippet.sh config/.env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SNIPPET="$ROOT/config/sber.env.snippet"
TARGET="${1:-}"
DRY_RUN="${DRY_RUN:-0}"

if [[ -z "$TARGET" || ! -f "$TARGET" ]]; then
  echo "Usage: $0 /path/to/.env"
  exit 2
fi
if [[ ! -f "$SNIPPET" ]]; then
  echo "missing $SNIPPET"
  exit 1
fi

# Keys we manage from snippet (never force empty secrets)
KEYS=(
  LLM_PROVIDER
  LLM_PREFER_LOCAL
  LLM_GIGA_FALLBACK_DEEPSEEK
  GIGACHAT_SCOPE
  GIGACHAT_OAUTH_URL
  GIGACHAT_BASE_URL
  GIGACHAT_MODEL
  GIGACHAT_IMAGE_MODEL
  GIGACHAT_CA_BUNDLE
  GIGACHAT_VERIFY_SSL
  TALK_BOT_LLM_PROVIDER
  TALK_BOT_LLM_TIMEOUT
  CLOUDRU_FM_BASE_URL
  CLOUDRU_FM_MODEL
  CLOUDRU_FM_MAX_TOKENS
  CLOUDRU_FM_TIMEOUT
  LLM_LOCAL_URL
)

tmp=$(mktemp)
cp "$TARGET" "$tmp"

get_snip() {
  # last non-comment assignment in snippet
  grep -E "^${1}=" "$SNIPPET" | tail -1 || true
}

for k in "${KEYS[@]}"; do
  line=$(get_snip "$k")
  [[ -z "$line" ]] && continue
  if grep -qE "^${k}=" "$tmp"; then
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "WOULD replace $k"
    else
      # portable-ish: rewrite file without that key then append
      grep -vE "^${k}=" "$tmp" > "${tmp}.2" || true
      echo "$line" >> "${tmp}.2"
      mv "${tmp}.2" "$tmp"
    fi
  else
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "WOULD append $line"
    else
      echo "$line" >> "$tmp"
    fi
  fi
done

if [[ "$DRY_RUN" == "1" ]]; then
  echo "dry-run only; $TARGET unchanged"
  rm -f "$tmp"
  exit 0
fi

cp "$TARGET" "${TARGET}.bak.$(date +%Y%m%d%H%M%S)"
mv "$tmp" "$TARGET"
echo "updated $TARGET (backup alongside)"
echo "NOTE: GIGACHAT_AUTH_KEY / DEEPSEEK_API_KEY / CLOUDRU_FM_API_KEY not touched — set manually if needed."
