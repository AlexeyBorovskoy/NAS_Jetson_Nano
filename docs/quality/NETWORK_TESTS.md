# Сетевые тесты / Network Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Test Scripts

### connectivity_check.sh

Checks ping reachability and HTTP endpoint availability.

```bash
# Basic connectivity to Jetson
tests/network/connectivity_check.sh --host 192.168.0.50

# Full check with URL and DNS
tests/network/connectivity_check.sh \
  --host 192.168.0.50 \
  --url http://192.168.0.50:8080/status.php \
  --dns-name jetson-nano.local \
  --output /tmp/connectivity-report.md

# VPS check
tests/network/connectivity_check.sh \
  --host 193.8.215.130 \
  --url http://193.8.215.130:8080/status.php
```

### port_check.sh

Checks that specific TCP ports are listening.

```bash
# Check all Jetson service ports
tests/network/port_check.sh \
  --host 192.168.0.50 \
  --ports "22,8080,2283,8090,8099,19999,3001,9000"

# Check VPS proxy ports
tests/network/port_check.sh \
  --host 193.8.215.130 \
  --ports "8080,2283,8090,8091"
```

---

## Manual Test Procedures

### T2.1: Ping Jetson from LAN

```bash
ping -c 4 192.168.0.50
```

Expected: 0% packet loss, RTT < 5ms on LAN

### T2.2: Port scan (listed ports only)

Run `tests/network/port_check.sh` as above.

Expected ports:
- :22 SSH
- :8080 Nextcloud
- :2283 Immich
- :8090 LLM Gateway
- :8099 NAS_Jetson_Nano API
- :19999 Netdata
- :3001 Uptime Kuma
- :9000 Portainer

### T2.3: VPS Proxy

```bash
curl -sf http://193.8.215.130:8080/status.php | python3 -m json.tool
curl -sf http://193.8.215.130:2283/api/server/ping
curl -sf http://193.8.215.130:8090/health
```

### T2.4: DNS

```bash
host 192.168.0.50
nslookup jetson-nano.local
```

---

## Expected Results

| Test | Expected | Actual | Pass? |
|---|---|---|---|
| Ping 192.168.0.50 | 0% loss | | |
| :22 open | yes | | |
| :8080 HTTP 200 | yes | | |
| :2283 HTTP 200 | yes | | |
| VPS :8080 | HTTP 200 | | |
| VPS :2283 | HTTP 200 | | |

---

## Failure Analysis

### Ping fails but SSH works
- Check IP address: `ip -4 addr show eth0` on Jetson
- Check firewall: `ufw status` (should be inactive or allow ICMP)

### Port not listening
- Check container: `docker ps | grep homecloud_nextcloud`
- Check port mapping: `docker inspect homecloud_nextcloud | grep PortBindings`

### VPS proxy not responding
- Check tunnel: `ssh root@193.8.215.130 "systemctl status autossh-nas_jetson_nano.service"`
- Check nginx: `ssh root@193.8.215.130 "nginx -t && systemctl status nginx"`
- Check tunnel endpoint: `ssh root@193.8.215.130 "ss -tlnp | grep :8080"`
