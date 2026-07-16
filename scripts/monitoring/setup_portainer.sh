#!/usr/bin/env bash
# setup_portainer.sh — initialize Portainer CE admin user via API
# Run ON JETSON NANO from ~/nas_jetson_nano:
#   bash scripts/monitoring/setup_portainer.sh
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

PORTAINER_URL="http://localhost:9000"
PORTAINER_CONTAINER="homecloud_portainer"

# Generate password if not set
if [[ -z "${PORTAINER_ADMIN_PASSWORD:-}" ]]; then
    PORTAINER_ADMIN_PASSWORD="$(openssl rand -base64 18 | tr -d '+/=' | head -c 20)"
    log "Generated Portainer password: ${PORTAINER_ADMIN_PASSWORD}"
    log "Save it to config/.env as PORTAINER_ADMIN_PASSWORD"
fi

# Check if already initialized
check_init() {
    local code
    code=$(curl -sf -o /dev/null -w "%{http_code}" "${PORTAINER_URL}/api/users/admin/check" 2>/dev/null || echo "000")
    echo "$code"
}

STATUS=$(check_init)
if [[ "$STATUS" == "204" ]]; then
    log "Portainer admin already initialized — nothing to do."
    log "Access: http://192.168.0.50:9000  user: admin"
    exit 0
fi

if [[ "$STATUS" != "404" ]]; then
    log "Portainer not responding (HTTP $STATUS). Restarting container..."
    docker restart "$PORTAINER_CONTAINER"
    log "Waiting 20s for Portainer to start..."
    sleep 20
fi

# Initialize admin
log "Initializing Portainer admin user..."
RESPONSE=$(curl -sf -X POST "${PORTAINER_URL}/api/users/admin/init" \
    -H "Content-Type: application/json" \
    -d "{\"Username\":\"admin\",\"Password\":\"${PORTAINER_ADMIN_PASSWORD}\"}" || true)

if echo "$RESPONSE" | grep -q '"jwt"'; then
    log "SUCCESS: Portainer admin created."
    log "  URL:      http://192.168.0.50:9000"
    log "  User:     admin"
    log "  Password: ${PORTAINER_ADMIN_PASSWORD}"
else
    log "ERROR: Unexpected response: ${RESPONSE}"
    exit 1
fi
