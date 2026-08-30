# Сетевые тесты / Network Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Тестовые скрипты / Test Scripts

### connectivity_check.sh

🇷🇺 Проверяет доступность по ping и доступность HTTP-эндпоинтов.

🇬🇧 Checks ping reachability and HTTP endpoint availability.

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
  --host 95.163.176.103 \
  --url http://95.163.176.103:8080/status.php
```

### port_check.sh

🇷🇺 Проверяет, что заданные TCP-порты слушают соединения.

🇬🇧 Checks that specific TCP ports are listening.

```bash
# Check all Jetson service ports
tests/network/port_check.sh \
  --host 192.168.0.50 \
  --ports "22,8080,2283,8090,8099,19999,3001,9000"

# Check VPS proxy ports
tests/network/port_check.sh \
  --host 95.163.176.103 \
  --ports "8080,2283,8090,8091"
```

---

## Процедуры ручного тестирования / Manual Test Procedures

### T2.1: Ping Jetson с домашней сети / Ping Jetson from LAN

```bash
ping -c 4 192.168.0.50
```

🇷🇺 Ожидается: 0% потерь пакетов, RTT < 5 мс в локальной сети.

🇬🇧 Expected: 0% packet loss, RTT < 5ms on LAN

### T2.2: Сканирование портов (только перечисленные порты) / Port scan (listed ports only)

🇷🇺 Запустить `tests/network/port_check.sh`, как показано выше.

🇬🇧 Run `tests/network/port_check.sh` as above.

Ожидаемые порты / Expected ports:
- :22 SSH
- :8080 Nextcloud
- :2283 Immich
- :8090 LLM Gateway
- :8099 NAS_Jetson_Nano API
- :19999 Netdata
- :3001 Uptime Kuma
- :9000 Portainer

### T2.3: Прокси VPS / VPS Proxy

```bash
curl -sf http://95.163.176.103:8080/status.php | python3 -m json.tool
curl -sf http://95.163.176.103:2283/api/server/ping
curl -sf http://95.163.176.103:8090/health
```

### T2.4: DNS

```bash
host 192.168.0.50
nslookup jetson-nano.local
```

---

## Ожидаемые результаты / Expected Results

| Тест / Test | Ожидается / Expected | Фактически / Actual | Прошло? / Pass? |
|---|---|---|---|
| Ping 192.168.0.50 | 0% loss | | |
| :22 open | yes | | |
| :8080 HTTP 200 | yes | | |
| :2283 HTTP 200 | yes | | |
| VPS :8080 | HTTP 200 | | |
| VPS :2283 | HTTP 200 | | |

---

## Разбор сбоев / Failure Analysis

### Ping не проходит, но SSH работает / Ping fails but SSH works
🇷🇺 Проверить IP-адрес: `ip -4 addr show eth0` на Jetson. Проверить файрвол: `ufw status` (должен быть неактивен или пропускать ICMP).

🇬🇧
- Check IP address: `ip -4 addr show eth0` on Jetson
- Check firewall: `ufw status` (should be inactive or allow ICMP)

### Порт не слушает / Port not listening
🇷🇺 Проверить контейнер и проброс портов.

🇬🇧
- Check container: `docker ps | grep homecloud_nextcloud`
- Check port mapping: `docker inspect homecloud_nextcloud | grep PortBindings`

### Прокси VPS не отвечает / VPS proxy not responding
🇷🇺 Проверить туннель, nginx и конечную точку туннеля.

🇬🇧
- Check tunnel: `ssh root@95.163.176.103 "systemctl status autossh-nas_jetson_nano.service"`
- Check nginx: `ssh root@95.163.176.103 "nginx -t && systemctl status nginx"`
- Check tunnel endpoint: `ssh root@95.163.176.103 "ss -tlnp | grep :8080"`
