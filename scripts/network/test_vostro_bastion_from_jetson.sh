#!/usr/bin/env bash
# Run on Jetson (admin). Requires:
#   ~/.ssh/id_ed25519              → VPS root (tunnel key)
#   ~/.ssh/id_ed25519_nas_vostro_admin → Vostro alexey
set -euo pipefail
KEY="${HOME}/.ssh/id_ed25519_nas_vostro_admin"
VPS_KEY="${HOME}/.ssh/id_ed25519"
VPS_HOST="${VPS_HOST:-95.163.176.103}"

ssh -i "$KEY" \
  -o BatchMode=yes \
  -o ConnectTimeout=15 \
  -o StrictHostKeyChecking=accept-new \
  -o "ProxyCommand=ssh -i ${VPS_KEY} -W 127.0.0.1:10222 -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@${VPS_HOST}" \
  alexey@vostro-bastion \
  'echo JETSON_TO_VOSTRO_OK
   hostname
   whoami
   getent hosts rserver3 || true
   timeout 3 bash -c "echo >/dev/tcp/192.168.57.1/22" && echo rserver3_22_OK || echo rserver3_22_FAIL
   timeout 3 bash -c "echo >/dev/tcp/127.0.0.1/8774" && echo local_8774_OK || echo local_8774_FAIL'
