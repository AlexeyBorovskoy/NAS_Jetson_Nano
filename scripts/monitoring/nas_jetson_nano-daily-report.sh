#!/usr/bin/env bash
# NAS_Jetson_Nano — daily health report (Jetson Nano)
# shellcheck disable=SC2034  # variables used in printf %b heredoc expansions
set -uo pipefail

CONF="/etc/nas_jetson_nano-monitor/nas_jetson_nano-monitor.env"
[ -f "$CONF" ] && . "$CONF"

VPS_KEY="${VPS_KEY:-/home/admin/.ssh/id_ed25519}"
VPS_USER="${VPS_USER:-root}"

NOW_UTC="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
NOW_MSK="$(TZ='Europe/Moscow' date '+%Y-%m-%d %H:%M:%S MSK')"
HOST="$(hostname)"
LOAD="$(cut -d' ' -f1-3 /proc/loadavg)"
UPTIME="$(uptime -p 2>/dev/null || uptime)"

DISK_ROOT_LINE="$(df -h / | awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}')"
DISK_ROOT_PCT="$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')"

DISK_STORAGE_LINE="not mounted"
DISK_STORAGE_PCT=0
STORAGE_HEALTH_LINE="❌ /mnt/storage is not a mountpoint"
if mountpoint -q /mnt/storage 2>/dev/null; then
    DISK_STORAGE_LINE="$(df -h /mnt/storage | awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}')"
    DISK_STORAGE_PCT="$(df -P /mnt/storage | awk 'NR==2 {gsub("%","",$5); print $5}')"
    storage_src="$(findmnt -n -T /mnt/storage -o SOURCE 2>/dev/null || echo unknown)"
    storage_fstype="$(findmnt -n -T /mnt/storage -o FSTYPE 2>/dev/null || echo unknown)"
    storage_opts="$(findmnt -n -T /mnt/storage -o OPTIONS 2>/dev/null || echo unknown)"
    STORAGE_HEALTH_LINE="✅ /mnt/storage mounted: ${storage_src} (${storage_fstype}, ${storage_opts})"
    case "$storage_src" in
        /dev/mmcblk*) STORAGE_HEALTH_LINE="❌ /mnt/storage is backed by microSD: ${storage_src}" ;;
    esac
    case ",${storage_opts}," in
        *,ro,*) STORAGE_HEALTH_LINE="❌ /mnt/storage is read-only: ${storage_src}" ;;
    esac
fi

RAM_LINE="$(free -h | awk '/Mem:/ {print $3 " / " $2 " (avail " $7 ")"}')"
RAM_AVAIL_MB="$(free -m | awk '/Mem:/ {print $7}')"

# Jetson thermal zones
TEMP_REPORT=""
for zone in /sys/class/thermal/thermal_zone*/; do
    name="$(cat "${zone}type" 2>/dev/null || echo unknown)"
    temp_raw="$(cat "${zone}temp" 2>/dev/null || echo 0)"
    temp_c="$((temp_raw / 1000))"
    case "$name" in
        CPU-therm|GPU-therm|PLL-therm|AO-therm|PMIC-Die|thermal-fan-est)
            TEMP_REPORT="${TEMP_REPORT}  ${name}: ${temp_c}°C\n"
            ;;
    esac
done
[ -z "$TEMP_REPORT" ] && TEMP_REPORT="  (thermal zones unavailable)\n"

# Services
TUNNEL_STATE="$(systemctl is-active nas_jetson_nano-tunnel.service 2>/dev/null || echo unknown)"
DOCKER_STATE="$(systemctl is-active docker 2>/dev/null || echo unknown)"
NM_STATE="$(systemctl is-active NetworkManager 2>/dev/null || echo unknown)"

# Containers
EXPECTED_CONTAINERS="${EXPECTED_CONTAINERS:-homecloud_nextcloud homecloud_nextcloud_db homecloud_nextcloud_redis homecloud_immich_server homecloud_immich_microservices homecloud_immich_db homecloud_immich_redis homecloud_llm_gateway homecloud_nas_jetson_nano_api homecloud_samba homecloud_netdata homecloud_uptime_kuma homecloud_portainer}"

CONTAINER_REPORT=""
WARNINGS=""

add_warning() { WARNINGS="${WARNINGS}\n  ⚠️  $1"; }

for c in $EXPECTED_CONTAINERS; do
    status="$(docker inspect "$c" --format '{{.State.Status}}' 2>/dev/null || echo missing)"
    restarts="$(docker inspect "$c" --format '{{.RestartCount}}' 2>/dev/null || echo ?)"
    icon="✅"
    [ "$status" != "running" ] && { icon="❌"; add_warning "container ${c} is ${status}"; }
    short="${c#homecloud-}"
    short="${short#homecloud_}"
    CONTAINER_REPORT="${CONTAINER_REPORT}\n  ${icon} ${short}: ${status} (restarts: ${restarts})"
done

# HTTP checks (local)
http_check() {
    local url="$1" label="$2"
    code="$(curl -o /dev/null -s -w '%{http_code}' --max-time 5 "$url" 2>/dev/null || true)"
    [ -n "$code" ] || code="000"
    if [ "$code" = "200" ] || [ "$code" = "302" ]; then
        echo "  ✅ ${label}: HTTP ${code}"
    else
        echo "  ❌ ${label}: HTTP ${code}"
        add_warning "${label} returned HTTP ${code}"
    fi
}

HTTP_REPORT=""
HTTP_REPORT="${HTTP_REPORT}\n$(http_check "http://localhost:8080/" "Nextcloud")"
HTTP_REPORT="${HTTP_REPORT}\n$(http_check "http://localhost:2283/" "Immich")"
HTTP_REPORT="${HTTP_REPORT}\n$(http_check "http://localhost:8090/health" "LLM Gateway")"
HTTP_REPORT="${HTTP_REPORT}\n$(http_check "http://localhost:19999/" "Netdata")"

# Beszel monitoring via SSH to VPS
BESZEL_REPORT=""
BESZEL_SCRIPT="/usr/local/sbin/nas_jetson_nano-beszel-report.py"
if [ -f "$VPS_KEY" ]; then
    # Use mktemp to avoid predictable temp file names (security hardening)
    _BESZEL_WARN_LOCAL="$(mktemp /tmp/nas_jetson_nano-beszel-warn.XXXXXXXXXX)"
    BESZEL_RAW="$(ssh -i "$VPS_KEY" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -o BatchMode=yes \
        "${VPS_USER}@${SERVER_IP:-95.163.176.103}" \
        "python3 $BESZEL_SCRIPT 2>/tmp/beszel_warn_\$\$.txt; cat /tmp/beszel_warn_\$\$.txt >&2; rm -f /tmp/beszel_warn_\$\$.txt" \
        2>"$_BESZEL_WARN_LOCAL" || true)"
    BESZEL_REPORT="$BESZEL_RAW"
    # harvest __WARN__ lines from stderr
    if [ -f "$_BESZEL_WARN_LOCAL" ]; then
        while IFS= read -r line; do
            case "$line" in
                __WARN__:*) add_warning "${line#__WARN__:}" ;;
            esac
        done < "$_BESZEL_WARN_LOCAL"
        rm -f "$_BESZEL_WARN_LOCAL"
    fi
    [ -z "$BESZEL_REPORT" ] && BESZEL_REPORT="  ⚠️ Beszel Hub unreachable via SSH"
fi

# External access.
#
# Service ports on the VPS are deliberately closed to the internet: ufw admits
# them only from 172.29.172.0/24 and 10.8.1.0/24 (project rule #4). A curl from
# the Jetson's public egress therefore MUST fail. The previous check treated
# that desired state as an error and printed ❌ every single day — which is how
# a monitor teaches the family to ignore it.
#
# What a family member actually depends on is the chain
#     client -> VPS nginx -> reverse SSH tunnel -> Jetson
# and it is measurable on the VPS itself against 127.0.0.1: the same path a VPN
# client's request takes, minus the client->VPS hop.
#
# The one check still pointed outward is inverted on purpose: a service port
# that answers from the public internet is now the alarm.
EXTERNAL_REPORT=""
VPS="${SERVER_IP:-95.163.176.103}"

if [ -f "$VPS_KEY" ]; then
    CHAIN_RAW="$(ssh -i "$VPS_KEY" \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -o BatchMode=yes \
        "${VPS_USER}@${VPS}" \
        'for s in "8080:/status.php:Nextcloud" "2283:/api/server/ping:Immich" "8090:/health:LLM Gateway" "8099:/healthcheck:API" "8091:/:Beszel Hub"; do
             p="${s%%:*}"; r="${s#*:}"; path="${r%%:*}"; name="${r#*:}"
             c="$(curl -o /dev/null -s -w "%{http_code}" --max-time 8 "http://127.0.0.1:${p}${path}" 2>/dev/null)"
             echo "${c:-000}|${p}|${name}"
         done' 2>/dev/null || true)"

    if [ -z "$CHAIN_RAW" ]; then
        EXTERNAL_REPORT="  ⚠️ VPS unreachable over SSH — chain NOT measured"
        add_warning "VPS unreachable over SSH: external chain not measured"
    else
        while IFS='|' read -r code port name; do
            [ -n "$name" ] || continue
            case "$code" in
                200|302)
                    EXTERNAL_REPORT="${EXTERNAL_REPORT}\n  ✅ ${name} through tunnel (:${port}): HTTP ${code}" ;;
                *)
                    EXTERNAL_REPORT="${EXTERNAL_REPORT}\n  ❌ ${name} through tunnel (:${port}): HTTP ${code}"
                    add_warning "${name} not reachable through the VPS tunnel (HTTP ${code})" ;;
            esac
        done <<CHAIN
$CHAIN_RAW
CHAIN
    fi
else
    EXTERNAL_REPORT="  ⚠️ no VPS key — external chain NOT measured"
fi

# Inverted check: this port MUST NOT answer from the public internet.
PUB_CODE="$(curl -o /dev/null -s -w '%{http_code}' --max-time 6 "http://${VPS}:8080/" 2>/dev/null)"
if [ "${PUB_CODE:-000}" = "000" ]; then
    EXTERNAL_REPORT="${EXTERNAL_REPORT}\n  ✅ ports closed to the internet (VPN only) — rule #4 holds"
else
    EXTERNAL_REPORT="${EXTERNAL_REPORT}\n  ❌ :8080 answered from the public internet: HTTP ${PUB_CODE}"
    add_warning "VPS port 8080 is reachable from the public internet"
fi

# Threshold warnings
[ "$DISK_ROOT_PCT" -ge "${DISK_WARN_PERCENT:-80}" ] && \
    add_warning "root disk usage high: ${DISK_ROOT_PCT}%"
[ "$DISK_STORAGE_PCT" -ge "${DISK_WARN_PERCENT:-80}" ] && \
    add_warning "storage disk usage high: ${DISK_STORAGE_PCT}%"
[ "$RAM_AVAIL_MB" -lt "${RAM_WARN_MB:-300}" ] && \
    add_warning "available RAM low: ${RAM_AVAIL_MB} MB"
[ "$STORAGE_HEALTH_LINE" != "${STORAGE_HEALTH_LINE#❌}" ] && \
    add_warning "$STORAGE_HEALTH_LINE"
if mountpoint -q /mnt/storage 2>/dev/null; then
    if [ -f /mnt/storage/nextcloud/data/.ncdata ]; then
        :  # marker present — all good
    elif [ "$(id -u)" -ne 0 ]; then
        :  # skip: ncdata owned by www-data, non-root can't read; container healthy = OK
    else
        add_warning "Nextcloud marker missing: /mnt/storage/nextcloud/data/.ncdata"
    fi
fi
# Kernel storage errors: only warn if storage is NOT healthy (USB reconnect
# produces expected error -71 / unable to enumerate during physical replug).
if ! mountpoint -q /mnt/storage 2>/dev/null; then
    journalctl -k --since "1 hour ago" --no-pager 2>/dev/null \
        | grep -qiE "EXT4-fs error|I/O error|error -71|unable to enumerate|read-only" \
        && add_warning "kernel storage errors in last hour AND storage not mounted"
else
    # Only flag hard I/O or filesystem errors, not USB enumeration (replug noise)
    journalctl -k --since "1 hour ago" --no-pager 2>/dev/null \
        | grep -qiE "EXT4-fs error|I/O error.*sda|read-only file system" \
        && add_warning "EXT4 / I/O errors on storage device in last hour"
fi
[ "$TUNNEL_STATE" != "active" ] && \
    add_warning "nas_jetson_nano-tunnel.service is ${TUNNEL_STATE}"
[ "$DOCKER_STATE" != "active" ] && \
    add_warning "docker.service is ${DOCKER_STATE}"

WARN_SECTION=""
if [ -n "$WARNINGS" ]; then
    WARN_SECTION="$(printf "\n⚠️  WARNINGS%b" "$WARNINGS")"
fi

cat <<REPORT
🏠 NAS_JETSON_NANO — Daily Report
📅 ${NOW_MSK}

💻 SYSTEM — ${HOST}
  Uptime: ${UPTIME}
  Load: ${LOAD}
  RAM: ${RAM_LINE}
  Disk /: ${DISK_ROOT_LINE}
  Disk /mnt/storage: ${DISK_STORAGE_LINE}
  Storage health: ${STORAGE_HEALTH_LINE}

🌡  TEMPERATURE
$(printf "%b" "$TEMP_REPORT")
🔌 SERVICES
  NAS_Jetson_Nano tunnel: ${TUNNEL_STATE}
  Docker: ${DOCKER_STATE}
  NetworkManager: ${NM_STATE}

🐳 CONTAINERS
$(printf "%b" "$CONTAINER_REPORT")

🌐 LOCAL HTTP
$(printf "%b" "$HTTP_REPORT")

☁️  EXTERNAL ACCESS
$(printf "%b" "$EXTERNAL_REPORT")

🔭 BESZEL MONITORING
${BESZEL_REPORT}
${WARN_SECTION}
REPORT
