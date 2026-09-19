#!/usr/bin/env bash
# Дневной лимит скорости качалки: day — DL_DAY_LIMIT (по умолчанию 6M ≈ 48 Мбит/с,
# половина домашнего канала), night — без лимита. Секрет — в теле запроса через stdin,
# не в аргументах curl (argv виден в `ps`).
set -euo pipefail
mode="${1:?использование: aria2_speed.sh day|night}"

if [ -z "${ARIA2_RPC_SECRET:-}" ]; then
  _nas_lay="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/layout.sh"
  [[ -r "$_nas_lay" ]] || _nas_lay=/usr/local/lib/nas_jetson_nano/layout.sh
  # shellcheck source=/dev/null
  source "$_nas_lay"
  ARIA2_RPC_SECRET="$(grep '^ARIA2_RPC_SECRET=' "$NAS_ENV_FILE" | cut -d= -f2- | tr -d '"')"
  DL_DAY_LIMIT="${DL_DAY_LIMIT:-$(grep '^DL_DAY_LIMIT=' "$NAS_ENV_FILE" | cut -d= -f2- | tr -d '"' || true)}"
fi

case "$mode" in
  day) limit="${DL_DAY_LIMIT:-6M}" ;;
  night) limit="0" ;;
  *) echo "режим: day или night" >&2; exit 2 ;;
esac

printf '{"jsonrpc":"2.0","id":"speed","method":"aria2.changeGlobalOption","params":["token:%s",{"max-overall-download-limit":"%s"}]}' \
  "$ARIA2_RPC_SECRET" "$limit" \
  | curl -s -m 10 -H 'Content-Type: application/json' -d @- http://127.0.0.1:6800/jsonrpc
echo
