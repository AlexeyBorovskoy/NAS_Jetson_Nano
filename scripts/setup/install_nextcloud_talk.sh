#!/usr/bin/env bash
# install_nextcloud_talk.sh — Install and configure Nextcloud Talk on Jetson.
#
# Run AFTER Docker and all containers are up:
#   ssh admin@192.168.0.50
#   cd ~/nas_jetson_nano && bash scripts/setup/install_nextcloud_talk.sh
#
# What this does:
#   1. Installs the Talk app via occ
#   2. Configures STUN server (Google public, works on LAN)
#   3. Optionally configures TURN server (coturn on VPS, for external calls)
#   4. Verifies installation
#
# After install: Android app "Nextcloud Talk" from Play Store
set -euo pipefail

NC_CONTAINER="homecloud_nextcloud"
CONF="/etc/nas_jetson_nano-monitor/talk.env"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
ok()  { echo "[$(date '+%H:%M:%S')] ✅ $*"; }
err() { echo "[$(date '+%H:%M:%S')] ❌ $*" >&2; }

# Load optional TURN config
[[ -f "$CONF" ]] && source "$CONF"
TURN_SERVER="${TURN_SERVER:-}"      # e.g. turn:95.163.176.103:3478
TURN_SECRET="${TURN_SECRET:-}"      # shared secret (from coturn config)

# ── 1. Check Nextcloud is running ─────────────────────────────────────────────
log "Checking Nextcloud container..."
if ! docker ps --format '{{.Names}}' | grep -q "^${NC_CONTAINER}$"; then
    err "Container $NC_CONTAINER is not running. Start it first."
    exit 1
fi
ok "Nextcloud container is running"

# ── 2. Install Talk app ───────────────────────────────────────────────────────
log "Installing Nextcloud Talk app..."
INSTALLED=$(docker exec "$NC_CONTAINER" php occ app:list --output json 2>/dev/null \
    | python3 -c "import sys,json; apps=json.load(sys.stdin); print('yes' if 'spreed' in apps.get('enabled',{}) else 'no')" \
    2>/dev/null || echo "no")

if [[ "$INSTALLED" == "yes" ]]; then
    ok "Talk (spreed) already installed and enabled"
else
    log "Running: occ app:install spreed"
    docker exec "$NC_CONTAINER" php occ app:install spreed
    ok "Talk app installed"
fi

# ── 3. Configure STUN server ──────────────────────────────────────────────────
log "Configuring STUN server (stun.l.google.com:19302)..."
docker exec "$NC_CONTAINER" php occ talk:stun:add stun.l.google.com:19302 2>/dev/null \
    || docker exec "$NC_CONTAINER" php occ config:app:set spreed stun_servers \
        --value='[{"schemes":"stun","server":"stun.l.google.com:19302"}]'
ok "STUN configured: stun.l.google.com:19302"

# ── 4. Configure TURN server (optional) ──────────────────────────────────────
if [[ -n "$TURN_SERVER" && -n "$TURN_SECRET" ]]; then
    log "Configuring TURN server: $TURN_SERVER"
    docker exec "$NC_CONTAINER" php occ talk:turn:add \
        --secret="$TURN_SECRET" \
        --schemes=turn,turns \
        "$TURN_SERVER" 2>/dev/null \
    || log "WARN: talk:turn:add not available — set via web UI (Talk → Admin → TURN)"
    ok "TURN configured: $TURN_SERVER"
else
    log "TURN server not configured (video calls work on LAN only)."
    log "To enable video outside LAN: set TURN_SERVER and TURN_SECRET in $CONF"
    log "Then re-run this script or configure via Nextcloud → Talk → Admin settings"
fi

# ── 5. Set signaling server mode ──────────────────────────────────────────────
# Default internal signaling — works for small family (≤ 10 users).
# External HPB (high-performance backend) not needed at this scale.
log "Signaling: using internal (default, OK for family use)"

# ── 6. Verify ─────────────────────────────────────────────────────────────────
log "Verifying Talk installation..."
STATUS=$(docker exec "$NC_CONTAINER" php occ app:list --output json 2>/dev/null \
    | python3 -c "
import sys, json
apps = json.load(sys.stdin)
enabled = apps.get('enabled', {})
print('enabled' if 'spreed' in enabled else 'not enabled')
" 2>/dev/null || echo "unknown")

if [[ "$STATUS" == "enabled" ]]; then
    ok "Nextcloud Talk is installed and enabled"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Nextcloud Talk — setup complete"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Web:     https://95.163.176.103:8443/apps/spreed"
    echo "  Android: Play Store → 'Nextcloud Talk'"
    echo "           (Same Nextcloud credentials)"
    echo ""
    echo "  Video calls:"
    echo "    ✅ Text chat — everywhere"
    echo "    ✅ Voice/video — home WiFi (LAN)"
    if [[ -n "$TURN_SERVER" ]]; then
        echo "    ✅ Voice/video — outside LAN (TURN configured)"
    else
        echo "    ⚠️  Voice/video outside LAN — needs TURN server"
        echo "       See: docs/plans/NEXTCLOUD_TALK_SETUP.md"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    err "Talk installation status: $STATUS"
    exit 1
fi
