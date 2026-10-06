#!/usr/bin/env bash
# Правило №13: то, что обязано совпасть до и после установки или отката учёта VPN.
#   bash rule13_snapshot.sh > /root/vpnmon-rule13-before.txt
#   ... установка ...
#   bash rule13_snapshot.sh | diff /root/vpnmon-rule13-before.txt -   # пусто = норма
set -euo pipefail
for c in amnezia-awg2 amnezia-xray; do
  docker inspect -f "$c started={{.State.StartedAt}} restarts={{.RestartCount}} running={{.State.Running}}" "$c"
done
# Число клиентов владелец сверяет в Amnezia Desktop; команды внутри VPN не выполняются.
ss -tlnuH | awk '{print $1, $5}' | sort -u
