# ADR-0003: Сетевая модель — LAN-only на Stage 1
# ADR-0003: Networking Model — LAN-only in Stage 1

## Статус / Status

🇷🇺 Принято. / 🇬🇧 Accepted.

## Контекст / Context

🇷🇺 Провайдер использует **CGNAT** — публичный IP недоступен, проброс портов снаружи невозможен.
🇬🇧 The ISP uses **CGNAT** — no public IP assigned, port forwarding from outside is impossible.

## Попытки внешнего доступа / External access attempts

### Попытка 1 / Attempt 1: wg-nas_jetson_nano (WireGuard на EU VPS 45.95.2.49)

🇷🇺 CGNAT блокирует входящие TCP → клиент не подключается к Jetson.
**Результат: удалено с Jetson 2026-06-13.**

🇬🇧 CGNAT blocks incoming TCP → client cannot connect to Jetson.
**Result: removed from Jetson 2026-06-13.**

### Попытка 2 / Attempt 2: Добавление пира в AmneziaWG / Adding peer via `wg set`

🇷🇺 Amnezia перехватила изменения → перезапустила контейнер `amnezia-awg` → все ~25 VPN-клиентов (телефоны семьи) потеряли доступ.
**Результат: авария. НЕЛЬЗЯ трогать Amnezia-сервер через SSH.**

🇬🇧 Amnezia caught the change → restarted `amnezia-awg` container → all ~25 VPN clients (family phones) lost access.
**Result: outage. DO NOT touch the Amnezia server via SSH or `wg set`.**

### Reverse tunnel (ngrok, cloudflared)

🇷🇺 Трафик через серверы третьей стороны — неприемлемо для приватных данных.
🇬🇧 Traffic through third-party servers — unacceptable for private data.

## Решение / Decision

🇷🇺 **LAN-only как базовая домашняя модель.** Прямого port forwarding на домашнем роутере нет. Исторический план внешнего доступа через Tailscale (ADR-0004) заменён реализованным VPS reverse SSH tunnel (ADR-0005), который не трогает Amnezia и не требует входящих соединений к Jetson.

🇬🇧 **LAN-only as the base home model.** No direct port forwarding on the home router. The historical Tailscale external access plan (ADR-0004) was replaced by the implemented VPS reverse SSH tunnel (ADR-0005), which does not touch Amnezia and does not require incoming connections to Jetson.

🇷🇺 Сеть Jetson: профиль `nas_jetson_nano-lan` (eth0, статика `192.168.0.50/24`, gw `192.168.0.1`, autoconnect=yes).
🇬🇧 Jetson network: profile `nas_jetson_nano-lan` (eth0, static `192.168.0.50/24`, gw `192.168.0.1`, autoconnect=yes).

## Жёсткие правила / Hard rules

1. 🇷🇺 **Не трогать Amnezia-сервер через SSH/`wg set`** — роняет прод ~25 пользователей.
   🇬🇧 **Do not touch Amnezia server via SSH/`wg set`** — drops prod for ~25 users.
2. 🇷🇺 **Не открывать порты 8080/2283/8090 на роутере** без документа риска.
   🇬🇧 **Do not open ports 8080/2283/8090 on the router** without a risk document.
3. 🇷🇺 **Профиль `nas_jetson_nano-lan` не удалять** — корректная статическая конфигурация Jetson.
   🇬🇧 **Do not delete `nas_jetson_nano-lan` profile** — correct static Jetson network configuration.
4. 🇷🇺 SSH через USB всегда работает: `ssh admin@fe80::1%<ifIndex>` (IPv6 link-local).
   🇬🇧 SSH via USB always works: `ssh admin@fe80::1%<ifIndex>` (IPv6 link-local).
