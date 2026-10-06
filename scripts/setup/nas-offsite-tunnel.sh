#!/usr/bin/env bash
# Runs ON VOSTRO as ExecStart of nas-offsite-tunnel.service (drop-in
# systemd/nas-offsite-tunnel.service.d/10-pick-address.conf). Keeps the reverse
# tunnel VPS 127.0.0.1:10222 -> Vostro:22: the off-site backup channel and the
# bastion from home into the corporate LAN (docs/plans/VOSTRO_BASTION_HOME_ACCESS.md).
#
# Why the address is picked on every start instead of being written once: the
# office ISP drops new flows to ONE of the two VPS addresses, and which one flips
# (02.09 the old 193.8.215.130, since 26.09 the new 95.163.176.103). The unit
# used autossh with a fixed address and retried a blocked one 8390 times.
# systemd restarts this script (Restart=always), so each restart probes again.
set -u

CANDIDATES="${NAS_VPS_CANDIDATES:-95.163.176.103 193.8.215.130}"
PROBE_PORT="${NAS_VPS_PROBE_PORT:-22}"
PROBE_TIMEOUT="${NAS_VPS_PROBE_TIMEOUT:-6}"
SSH_BIN="${NAS_TUNNEL_SSH:-/usr/bin/ssh}"
TUNNEL_KEY="${NAS_TUNNEL_KEY:-/home/alexey/.ssh/id_ed25519_nas_offsite}"
# Both addresses are the same VPS with the same host key. Pinning it under one
# alias verifies either address against the known key instead of trusting the
# first key a not-yet-seen address presents (accept-new would).
HOST_KEY_ALIAS="${NAS_VPS_HOST_KEY_ALIAS:-nas-vps}"

# Do not interpolate unvalidated environment values into bash -c.
if [[ ! "$PROBE_PORT" =~ ^[0-9]{1,5}$ ]] || (( 10#$PROBE_PORT < 1 || 10#$PROBE_PORT > 65535 )); then
    echo "ERROR: invalid probe port" >&2
    exit 2
fi
if [[ ! "$PROBE_TIMEOUT" =~ ^[0-9]{1,2}$ ]] || (( 10#$PROBE_TIMEOUT < 1 || 10#$PROBE_TIMEOUT > 60 )); then
    echo "ERROR: invalid probe timeout" >&2
    exit 2
fi

for addr in $CANDIDATES; do
    case "$addr" in
        *[!A-Za-z0-9.:-]*)
            echo "skip invalid VPS address: $addr" >&2
            continue
            ;;
    esac
    if timeout "$PROBE_TIMEOUT" bash -c ": </dev/tcp/$addr/$PROBE_PORT" 2>/dev/null; then
        echo "VPS $addr:$PROBE_PORT reachable, starting tunnel"
        exec "$SSH_BIN" -N \
            -R 10222:localhost:22 \
            -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o BatchMode=yes \
            -o ConnectTimeout=15 \
            -o HostKeyAlias="$HOST_KEY_ALIAS" \
            -o StrictHostKeyChecking=yes \
            -i "$TUNNEL_KEY" \
            "root@$addr"
    fi
    echo "VPS $addr:$PROBE_PORT unreachable within ${PROBE_TIMEOUT}s" >&2
done

echo "ERROR: no VPS address reachable: $CANDIDATES" >&2
exit 1
