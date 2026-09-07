#!/usr/bin/env bash
# Push current branch to GitVerse mirror NAS_HOME (no secrets).
# Usage (on workstation with gitverse SSH key):
#   bash scripts/sber/gitverse_mirror_push.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

if ! bash scripts/quality/preflight.sh --quick; then
  echo "preflight failed — abort push"
  exit 1
fi

if ! git remote get-url gitverse >/dev/null 2>&1; then
  git remote add gitverse git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git
  echo "added remote gitverse"
fi

branch=$(git rev-parse --abbrev-ref HEAD)
echo "pushing $branch → gitverse"
# Remote may use master; push both names safely
git push gitverse "HEAD:refs/heads/${branch}"
git push gitverse "HEAD:refs/heads/master" 2>/dev/null || true
echo "done"
echo "verify: git ls-remote gitverse"
