#!/usr/bin/env bash
# NAS_Jetson_Nano — Add HTTPS to nas_jetson_nano_nginx Docker container (VPS)
#
# Context: nas_jetson_nano_nginx (nginx:alpine, host network) already proxies:
#   :8080  → 127.0.0.1:18080 → Jetson:8080 (Nextcloud)  [HTTP]
#   :2283  → 127.0.0.1:12283 → Jetson:2283 (Immich)     [HTTP]
#   :8090  → 127.0.0.1:18090 → Jetson:8090 (LLM Gateway)[HTTP]
#
# This script adds HTTPS server blocks:
#   :8443  → Nextcloud HTTPS
#   :2443  → Immich HTTPS
#   :9443  → LLM Gateway HTTPS
#
# Run on VPS:
#   ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 "bash -s" < install_nginx_vps.sh

set -euo pipefail

NGINX_CONF_DIR="/opt/nas_jetson_nano/nginx/conf.d"
NGINX_SSL_DIR="/opt/nas_jetson_nano/nginx/ssl"
NGINX_CONTAINER="nas_jetson_nano_nginx"
VPS_IP="95.163.176.103"

# HTTPS ports (avoid 443 — taken by Amnezia xray)
NC_HTTPS=8443    # Nextcloud HTTPS
IM_HTTPS=2443    # Immich HTTPS
LLM_HTTPS=9443   # LLM Gateway HTTPS (already in ufw)

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# ── 1. Preflight ──────────────────────────────────────────────────────────────
docker ps --filter "name=${NGINX_CONTAINER}" --format "{{.Names}}" | grep -q "^${NGINX_CONTAINER}$" \
    || die "${NGINX_CONTAINER} container not running. Check: docker ps"

[ -d "$NGINX_CONF_DIR" ] \
    || die "nginx conf dir not found: $NGINX_CONF_DIR"

# ── 2. Generate self-signed TLS certificate ───────────────────────────────────
log "Generating self-signed TLS certificate..."
mkdir -p "$NGINX_SSL_DIR"

if [ ! -f "$NGINX_SSL_DIR/nas_jetson_nano.crt" ]; then
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "$NGINX_SSL_DIR/nas_jetson_nano.key" \
        -out    "$NGINX_SSL_DIR/nas_jetson_nano.crt" \
        -days 3650 \
        -subj "/CN=nas_jetson_nano-homecloud/O=NAS_Jetson_Nano/C=RU" \
        -addext "subjectAltName=IP:${VPS_IP},DNS:localhost" \
        2>/dev/null
    chmod 600 "$NGINX_SSL_DIR/nas_jetson_nano.key"
    log "Certificate saved: $NGINX_SSL_DIR/nas_jetson_nano.crt"
else
    log "Certificate already exists — skipping."
fi

# ── 3. Add HTTPS blocks to nginx configs ──────────────────────────────────────
log "Adding HTTPS server blocks to nginx configs..."

# ─── Nextcloud ───
grep -q "listen ${NC_HTTPS}" "${NGINX_CONF_DIR}/nextcloud.conf" 2>/dev/null && {
    log "Nextcloud HTTPS block already present — skipping.";
} || {
cat >> "${NGINX_CONF_DIR}/nextcloud.conf" <<'NCCONF'

# HTTPS (added by install_nginx_vps.sh)
server {
    listen 8443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/nas_jetson_nano.crt;
    ssl_certificate_key /etc/nginx/ssl/nas_jetson_nano.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    client_max_body_size 10G;
    proxy_read_timeout 600;
    proxy_send_timeout 600;

    location / {
        proxy_pass         http://127.0.0.1:18080;
        proxy_set_header   Host $http_host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_set_header   X-Forwarded-Host $http_host;
        proxy_buffering    off;
        proxy_request_buffering off;
    }

    location /.well-known/carddav { return 301 /remote.php/dav; }
    location /.well-known/caldav  { return 301 /remote.php/dav; }
}
NCCONF
    log "Nextcloud HTTPS block added."
}

# ─── Immich ───
grep -q "listen ${IM_HTTPS}" "${NGINX_CONF_DIR}/immich.conf" 2>/dev/null && {
    log "Immich HTTPS block already present — skipping.";
} || {
cat >> "${NGINX_CONF_DIR}/immich.conf" <<'IMCONF'

# HTTPS (added by install_nginx_vps.sh)
server {
    listen 2443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/nas_jetson_nano.crt;
    ssl_certificate_key /etc/nginx/ssl/nas_jetson_nano.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    client_max_body_size 10G;
    proxy_read_timeout 600;

    location / {
        proxy_pass         http://127.0.0.1:12283;
        proxy_set_header   Host $http_host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_buffering    off;
    }
}
IMCONF
    log "Immich HTTPS block added."
}

# ─── LLM Gateway ───
grep -q "listen ${LLM_HTTPS}" "${NGINX_CONF_DIR}/llm-gateway.conf" 2>/dev/null && {
    log "LLM HTTPS block already present — skipping.";
} || {
cat >> "${NGINX_CONF_DIR}/llm-gateway.conf" <<'LLMCONF'

# HTTPS (added by install_nginx_vps.sh)
server {
    listen 9443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/nas_jetson_nano.crt;
    ssl_certificate_key /etc/nginx/ssl/nas_jetson_nano.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    client_max_body_size 100M;
    proxy_read_timeout 300;

    location / {
        proxy_pass       http://127.0.0.1:18090;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_buffering  off;
    }
}
LLMCONF
    log "LLM Gateway HTTPS block added."
}

# ── 4. Open firewall ports ────────────────────────────────────────────────────
log "Opening HTTPS ports in ufw..."
ufw allow ${NC_HTTPS}/tcp  comment "NAS_Jetson_Nano Nextcloud HTTPS"  2>/dev/null || true
ufw allow ${IM_HTTPS}/tcp  comment "NAS_Jetson_Nano Immich HTTPS"     2>/dev/null || true
ufw allow ${LLM_HTTPS}/tcp comment "NAS_Jetson_Nano LLM Gateway HTTPS" 2>/dev/null || true

# ── 5. Reload nginx inside container ─────────────────────────────────────────
log "Reloading nginx inside ${NGINX_CONTAINER}..."
docker exec "$NGINX_CONTAINER" nginx -t \
    || die "nginx config test failed — check configs in $NGINX_CONF_DIR"
docker exec "$NGINX_CONTAINER" nginx -s reload
log "nginx reloaded."

# ── 6. Nextcloud trusted proxy ────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MANUAL STEP: Nextcloud trusted proxy config"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  On Jetson:"
echo "    docker exec -it homecloud_nextcloud bash"
echo "    # Add to /var/www/html/config/config.php inside \$CONFIG array:"
echo ""
echo "    'trusted_proxies'   => ['127.0.0.1', '${VPS_IP}'],"
echo "    'overwriteprotocol' => 'https',"
echo "    'forwarded_for_headers' => ['HTTP_X_FORWARDED_FOR'],"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 7. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "✅ HTTPS configured on VPS nginx (self-signed cert, valid 10 years)"
echo ""
echo "  HTTP (existing, unchanged):"
echo "    Nextcloud:   http://${VPS_IP}:8080"
echo "    Immich:      http://${VPS_IP}:2283"
echo "    LLM Gateway: http://${VPS_IP}:8090"
echo ""
echo "  HTTPS (new):"
echo "    Nextcloud:   https://${VPS_IP}:8443"
echo "    Immich:      https://${VPS_IP}:2443"
echo "    LLM Gateway: https://${VPS_IP}:9443"
echo ""
echo "  DAVx⁵ endpoint (contacts/calendar):"
echo "    https://${VPS_IP}:8443/remote.php/dav"
echo ""
echo "  Note: Self-signed cert → accept warning in browser/app once."
echo "  For DAVx⁵: go to Account settings → Accept untrusted certificate."
