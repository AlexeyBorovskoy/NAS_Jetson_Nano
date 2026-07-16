#!/bin/bash
# setup_vps_tunnel.sh — establish reverse SSH tunnel from Jetson to VPS
# Run on JETSON NANO, not on Windows host
# Requires: apt install autossh
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

if [[ -z "${VPS_HOST:-}" ]]; then
    log "ERROR: VPS_HOST is not set. Add VPS_HOST=<ip> to config/.env"
    exit 1
fi
VPS_USER="${VPS_USER:-root}"
VPS_SSH_KEY="${VPS_SSH_KEY:-${HOME}/.ssh/id_ed25519}"

log "=== NAS_Jetson_Nano VPS reverse tunnel ==="
log "VPS: ${VPS_USER}@${VPS_HOST}"
log "Tunnels: 18080->8080 (Nextcloud), 12283->2283 (Immich), 18090->8090 (LLM-GW)"

# Check SSH key exists
if [[ ! -f "$VPS_SSH_KEY" ]]; then
    log "ERROR: SSH key not found: $VPS_SSH_KEY"
    log "Generate with: ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519"
    exit 1
fi

# Test VPS connectivity
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes -i "$VPS_SSH_KEY" \
    "${VPS_USER}@${VPS_HOST}" "echo ok" &>/dev/null; then
    log "ERROR: Cannot reach VPS ${VPS_HOST}"
    log "Add Jetson public key to VPS: cat ~/.ssh/id_ed25519.pub | ssh root@${VPS_HOST} tee -a ~/.ssh/authorized_keys"
    exit 1
fi

log "VPS reachable. Starting autossh tunnel..."

exec autossh -N \
    -R "18080:localhost:8080" \
    -R "12283:localhost:2283" \
    -R "18090:localhost:8090" \
    -o "ServerAliveInterval=30" \
    -o "ServerAliveCountMax=3" \
    -o "ExitOnForwardFailure=yes" \
    -o "StrictHostKeyChecking=accept-new" \
    -i "${VPS_SSH_KEY}" \
    "${VPS_USER}@${VPS_HOST}"