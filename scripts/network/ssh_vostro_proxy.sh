#!/usr/bin/env bash
# Jetson SSH ProxyCommand: choose a reachable VPS, preserving its pinned key.
set -eu
for address in 95.163.176.103 193.8.215.130; do
    if timeout 6 bash -c ': </dev/tcp/'"$address"'/22' 2>/dev/null; then
        exec /usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=8 \
            -o StrictHostKeyChecking=yes -o HostKeyAlias=95.163.176.103 \
            -o IdentitiesOnly=yes -i "$HOME/.ssh/id_ed25519" \
            -W 127.0.0.1:10222 "root@$address"
    fi
done
echo 'No reachable NAS VPS address for Vostro proxy' >&2
exit 1
