#!/bin/bash
# aria2 on-download-stop (отмена или ошибка; готовое обрабатывает on_complete.sh):
# удаляет недокачанное из .incomplete, чтобы отменённые 100 ГБ не остались на HDD.
# Трогает ТОЛЬКО верхний элемент внутри .incomplete; «..» и пути вне корней — игнор.
set -u
SSD_INC="${DL_SSD_INCOMPLETE:-/downloads/ssd/.incomplete}"
HDD_INC="${DL_HDD_INCOMPLETE:-/downloads/hdd/.incomplete}"
path="${3:-}"
[ -n "$path" ] || exit 0
case "$path" in *"/../"*|*"/.."|"../"*) exit 0 ;; esac

# И3: aria2 вызывает on-download-stop и для отменённых, И для прерванных (например,
# остановкой контейнера) закачек — на факте вызова хука полагаться нельзя. Спрашиваем
# настоящий статус по RPC; удаляем только removed/error, иначе (active либо RPC не
# ответил) — не знаем, ничего не трогаем. Секрет не попадает в argv.
secret="$(sed -n 's/^rpc-secret=//p' "${ARIA2_CONF:-/tmp/aria2.conf}")"
status=""
if [ -n "$secret" ]; then
  body=$(mktemp); chmod 600 "$body"
  printf '{"jsonrpc":"2.0","id":"stop","method":"aria2.tellStatus","params":["token:%s","%s",["status"]]}' \
    "$secret" "$1" > "$body"
  status=$(${DL_WGET:-wget} -q -O - --post-file="$body" --header='Content-Type: application/json' \
    http://127.0.0.1:6800/jsonrpc 2>/dev/null | sed -n 's/.*"status":"\([a-z]*\)".*/\1/p')
  rm -f "$body"
fi
case "$status" in removed|error) ;; *) exit 0 ;; esac   # не знаем — ничего не удаляем

for root in "$SSD_INC" "$HDD_INC"; do
  case "$path" in
    "$root"/*)
      rel="${path#"$root"/}"
      case "$rel" in
        .u/*/*)  # папка члена семьи (2026-09-26): .incomplete/.u/<логин>/<top>
          user="${rel#.u/}"; user="${user%%/*}"
          case "$user" in ""|*[!A-Za-z0-9_-]*) exit 0 ;; esac
          root="$root/.u/$user"; rel="${rel#.u/"$user"/}" ;;
      esac
      top="${rel%%/*}"
      case "$top" in ""|"."|"..") exit 0 ;; esac
      rm -rf -- "$root/$top" "$root/$top.aria2"
      exit 0 ;;
  esac
done
exit 0
