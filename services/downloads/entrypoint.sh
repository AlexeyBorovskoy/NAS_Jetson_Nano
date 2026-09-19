#!/bin/sh
# Запуск aria2 + страница AriaNg. Секрет — из окружения в копию конфига (права 600),
# не в аргументы процесса: argv контейнера виден в `ps` хоста.
set -eu
: "${ARIA2_RPC_SECRET:?нужен ARIA2_RPC_SECRET}"
mkdir -p /downloads/ssd/.incomplete /downloads/hdd/.incomplete /config
touch /config/aria2.session
( umask 077
  cp /etc/aria2/aria2.conf /tmp/aria2.conf
  printf 'rpc-secret=%s\n' "$ARIA2_RPC_SECRET" >> /tmp/aria2.conf )
umask 022
httpd -p 6880 -h /www
# И6: HDD — внешний NTFS-диск; если он не примонтирован, Docker тихо подставит
# пустой каталог вместо него. Маркер в корне Downloads отличает одно от другого.
[ -e /downloads/hdd/.nas-hdd-marker ] || { echo "HDD не смонтирован — жду" >&2; sleep 60; exit 1; }
exec aria2c --conf-path=/tmp/aria2.conf
