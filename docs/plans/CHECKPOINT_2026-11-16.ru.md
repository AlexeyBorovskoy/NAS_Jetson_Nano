# Контрольная точка проекта — 2026-11-16

**Контекст:** Развёртывание и приёмка нового шведского семейного VPN-сервера (`NEW-VPS-FAST-01`), выпуск TLS-сертификата Let's Encrypt и подключение тестовых семейных учётных записей.

---

## 1. Инфраструктура на шведском VPS

- **Хост:** `45.140.13.178` (`broken-indigo.ptr.network`, `Ubuntu 24.04.1 LTS`, KVM Aeza, SSH-алиас `aeza-sweden`).
  - *Примечание:* исходный IP `82.148.227.55` оказался недоступен напрямую с домашнего Wi-Fi и LTE в РФ (таймауты ICMP/TCP), после чего владелец сменил IP VPS на `45.140.13.178`.
- **Домен:** `vpn.privet.dynv6.net` (`A 45.140.13.178`, `AAAA` отсутствует, проверено через `@1.1.1.1`).
- **Серверное ПО:** официальный `sing-box 1.14.4` (`deb.sagernet.org`), `systemd` drop-in с ограничением привилегий (`CAP_NET_BIND_SERVICE` only), запуск под пользователем `sing-box`.
- **Два активных транспорта на порту `443`:**
  1. **`hy2-in` (`Hysteria 2`, `UDP/443`, основной):** `alpn: ["h3"]`, `masquerade: "https://www.bing.com"`, переведён на сертификат Let's Encrypt (`/etc/sing-box/tls/fullchain.pem`, `privkey.pem` `0640 root:sing-box`).
  2. **`vless-reality-in` (`VLESS + xtls-rprx-vision + REALITY`, `TCP/443`, запасной):** SNI `www.googletagmanager.com`.
- **Firewall (`ufw`):** открыты только `22/tcp`, `443/tcp`, `443/udp`, `80/tcp` (для ACME HTTP-01); входящие по умолчанию `deny`.
- **Анти-SSRF:** `route.rules` в `sing-box` отклоняет `ip_is_private: true` и приватные/CGNAT-подсети.

---

## 2. TLS Let's Encrypt и автоматическое продление

- Установлен `certbot 2.9.0`, выпущен ECDSA-сертификат для `vpn.privet.dynv6.net` (до `2027-02-14`, цепочка `openssl verify` → `OK`).
- Настроен deploy-hook `/etc/letsencrypt/renewal-hooks/deploy/sing-box-tls.sh`: обновление `/etc/sing-box/tls/`, проверка `sing-box check`, перезапуск `sing-box` и запись в `journald`.
- Проверено `certbot renew --dry-run` → `success`, таймер `certbot.timer` активен.
- Резервная копия до TLS-изменений: `/root/backup-tls-20261116T083718Z/` (`chmod 700`, `SHA256SUMS.txt`).

---

## 3. Клиенты и семейное тестирование

- **Тестовый телефон (`hagircbmsszlx4in`):** `FlClash 0.9.3 (com.follow.clash)`, стек `gvisor`, `Перехват DNS: ON`, `IPv6: OFF`, `Always-on` (`lockdown=0`), белый список Doze.
- **Пройденные проверки:** `T0`, `T1` (5/5), `T1-ALT` (`VLESS+REALITY`), `T3` (YouTube), `T4` (Telegram `@telegram`), `T6` (сон 5+ мин), `T7` (отсутствие утечек DNS/WebRTC/IPv6 на `ipleak.net`), `T8` (Chrome `45.140.13.178`). `T2` (домашний LAN) и `T5` (LTE) отложены до возвращения в домашнюю сеть и появления мобильного трафика.
- **Семейные учётные записи (5 изолированных профилей, секреты хранятся строго вне Git в `C:\Users\Alexey\.ssh\new-vps-se\family\`):**
  - `olga-android`, `ulyana-android-1`, `ulyana-android-2`, `ivan-android`, `ivan-windows`.
  - В семейных профилях настроена строгая проверка сертификата (`skip-cert-verify: false`) и прямой маршрут `DIRECT` для домашней сети и РФ-доменов (`.ru`, `.su`, `.рф`, `vk.com`).
  - Профиль `FAMILY-SE-Olga-Android.yaml` проверен на телефоне: `api.ipify.org` → `45.140.13.178`, `yandex.ru/internet` → локальный IP (`84.52.101.142`, `DIRECT`).
- **Локальные отчёты и инструкция для семьи (в ignored `artifacts/`):**
  - `artifacts/reports/new-vps-fast-2026-11-15/RESULT.md`, `TEST_RESULTS.csv`, `RUNBOOK.md`, `TLS_LE_AUDIT_2026-11-16.md`, `FAMILY_SETUP_GUIDE.md`, `FAMILY_SETUP_GUIDE.pdf`.

---

## 4. Открытые действия для владельца

1. Отозвать ранее показанные в чате временные токены/пароли (Aeza API-ключ, `root`-пароль, `dynv6` токен).
2. После возвращения домой проверить открытие `http://192.168.0.1` и `http://192.168.68.1` при включённом VPN (`T2`).
3. Раздать семейные `.yaml` профили и `FAMILY_SETUP_GUIDE.pdf` (клиент `Hiddify` из Google Play).
