#!/usr/bin/env bash
# Учёт VPN и нагрузки VPS: установка на VPS. Только по команде «деплой»,
# runbook — docs/plans/DEPLOY_VPNMON_2026-10.ru.md, спецификация 2026-10-04 §11.
#   bash install_vps.sh
# Код — /usr/local/lib/nasa-vpnmon, юниты — /etc/systemd/system, таймер сбора включается.
# Таймер отчёта включается, только если уже лежит /etc/nasa-vpnmon/telegram.env.
# Новых портов, пакетов и пользователей нет; VPN и сетевые правила не меняются.
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
LIB=/usr/local/lib/nasa-vpnmon

[ "$(id -u)" -eq 0 ] || { echo "нужен root" >&2; exit 1; }
for f in collect.py report.py vpnmon_parse.py vpnmon_store.py vpnmon_query.py vpnmon_render.py \
         systemd/nasa-vpnmon-collect.service systemd/nasa-vpnmon-collect.timer \
         systemd/nasa-vpnmon-report.service systemd/nasa-vpnmon-report.timer names.conf.example; do
  [ -f "$HERE/$f" ] || { echo "неполный установочный комплект: $f" >&2; exit 1; }
done

install -d -m 0755 -o root -g root "$LIB"
install -d -m 0700 -o root -g root /etc/nasa-vpnmon /var/lib/nasa-vpnmon
for f in collect.py report.py vpnmon_parse.py vpnmon_store.py vpnmon_query.py vpnmon_render.py; do
  install -m 0644 -o root -g root "$HERE/$f" "$LIB/$f"
done
python3 -m py_compile "$LIB"/*.py

for u in nasa-vpnmon-collect.service nasa-vpnmon-collect.timer \
         nasa-vpnmon-report.service nasa-vpnmon-report.timer; do
  install -m 0644 -o root -g root "$HERE/systemd/$u" "/etc/systemd/system/$u"
done
if [ ! -f /etc/nasa-vpnmon/names.conf ]; then
  install -m 0600 -o root -g root "$HERE/names.conf.example" /etc/nasa-vpnmon/names.conf
fi

systemctl daemon-reload
systemctl enable --now nasa-vpnmon-collect.timer
if [ -f /etc/nasa-vpnmon/telegram.env ]; then
  systemctl enable --now nasa-vpnmon-report.timer
else
  echo "нет файла с токеном — таймер отчёта НЕ включён (см. runbook, шаг токена)" >&2
fi
systemctl list-timers --all 'nasa-vpnmon-*' --no-pager
