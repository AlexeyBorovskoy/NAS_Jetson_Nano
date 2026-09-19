#!/bin/sh
# Запуск aria2 + страница AriaNg. Секрет — из окружения в копию конфига (права 600),
# не в аргументы процесса: argv контейнера виден в `ps` хоста.
set -eu
: "${ARIA2_RPC_SECRET:?нужен ARIA2_RPC_SECRET}"
mkdir -p /downloads/ssd/.incomplete /downloads/hdd/.incomplete /config
touch /config/aria2.session
umask 077
cp /etc/aria2/aria2.conf /tmp/aria2.conf
printf 'rpc-secret=%s\n' "$ARIA2_RPC_SECRET" >> /tmp/aria2.conf
httpd -p 6880 -h /www
exec aria2c --conf-path=/tmp/aria2.conf
