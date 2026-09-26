#!/bin/bash
# API-2/3 (аудит 2026-09-26) — сетевой барьер для качалки: контейнер aria2 не ходит
# в домашнюю сеть, Docker-сети и на сам Jetson.
#
# ЗАЧЕМ. Ссылку на закачку присылает человек, а качает её aria2 сам: идёт по
# HTTP-редиректам и резолвит имя в свой момент. Прикладная проверка адреса в API
# не может это закрыть в принципе (редирект, DNS rebinding) — закрывает только сеть.
#
# КАК. Своя цепочка NAS-DL-EGRESS: разрешены ответы на уже открытые соединения
# (RPC от API, AriaNg из LAN), всё НОВОЕ в частные диапазоны — REJECT. Прыжок в
# неё — из DOCKER-USER (транзит) и INPUT (сам Jetson), только для подсети сети
# качалки. Подсеть назначает Docker и может смениться при пересоздании — поэтому
# скрипт идемпотентный и крутится таймером: узнаёт текущую подсеть, чистит прыжки
# на старую. 100.64.0.0/10 (CGNAT) не режем — там живут обычные пиры торрентов.
# IPv6 у сети качалки нет — ip6tables не трогаем.
set -euo pipefail

NET="${DL_NETWORK:-homecloud-downloads_default}"
CHAIN="NAS-DL-EGRESS"

subnet="$(docker network inspect -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}' "$NET" 2>/dev/null || true)"
if [ -z "$subnet" ]; then
  echo "dl-egress: сеть $NET не найдена — пропуск"
  exit 0
fi

iptables -N "$CHAIN" 2>/dev/null || true
iptables -F "$CHAIN"
iptables -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
for dst in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 127.0.0.0/8; do
  iptables -A "$CHAIN" -d "$dst" -j REJECT
done
iptables -A "$CHAIN" -j RETURN

for parent in DOCKER-USER INPUT; do
  iptables -S "$parent" 2>/dev/null | grep -- "-j $CHAIN" | grep -v -- "-s $subnet " \
    | sed 's/^-A /-D /' | while read -r rule; do
      # shellcheck disable=SC2086  # правило — список аргументов iptables
      iptables $rule
    done
  iptables -C "$parent" -s "$subnet" -j "$CHAIN" 2>/dev/null \
    || iptables -I "$parent" 1 -s "$subnet" -j "$CHAIN"
done
echo "dl-egress: барьер для $NET ($subnet) на месте"
