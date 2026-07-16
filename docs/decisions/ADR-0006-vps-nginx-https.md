# ADR-0006: HTTPS для VPS nginx — самоподписанный сертификат
# ADR-0006: HTTPS for VPS nginx — Self-signed Certificate

**Дата / Date:** 2026-06-25
**Статус / Status:** Accepted
**Автор / Author:** AlexeyBorovskoy

---

## Контекст / Context

🇷🇺 До 2026-06-25 VPS nginx обслуживал Nextcloud и Immich только по HTTP. Android-приложениям (Immich, Nextcloud, DAVx⁵) необходимо HTTPS для стабильной работы вне дома.
🇬🇧 Before 2026-06-25 VPS nginx served Nextcloud and Immich on HTTP only. Android apps (Immich, Nextcloud, DAVx⁵) require HTTPS for stable operation outside the home network.

🇷🇺 **Ограничения:**
🇬🇧 **Constraints:**

- 🇷🇺 Порт 443 занят Amnezia xray — нельзя освободить / 🇬🇧 Port 443 occupied by Amnezia xray — cannot be freed
- 🇷🇺 Нет доменного имени → Let's Encrypt недоступен / 🇬🇧 No domain name → Let's Encrypt unavailable
- 🇷🇺 VPS совместно используется с Amnezia VPN (~25 клиентов), нельзя трогать существующую конфигурацию / 🇬🇧 VPS shared with Amnezia VPN (~25 clients), existing config must not be changed

🇷🇺 **Варианты:**
🇬🇧 **Options:**

1. 🇷🇺 Tailscale — конфликт VPN-профиля с Amnezia на Android / 🇬🇧 Tailscale — VPN profile conflict with Amnezia on Android
2. 🇷🇺 Let's Encrypt на кастомном домене — требует домен и публичный порт 80/443 / 🇬🇧 Let's Encrypt on custom domain — requires domain and public port 80/443
3. 🇷🇺 **Самоподписанный сертификат на alt-портах** — работает без домена, без конфликта с Amnezia / 🇬🇧 **Self-signed certificate on alt-ports** — works without domain, no Amnezia conflict

---

## Решение / Decision

🇷🇺 Добавить HTTPS к `nas_jetson_nano_nginx` Docker контейнеру на нестандартных портах:
🇬🇧 Add HTTPS to `nas_jetson_nano_nginx` Docker container on non-standard ports:

| Сервис / Service | HTTP (было / before) | HTTPS (добавлено / added) |
|---|---|---|
| Nextcloud | :8080 | :8443 |
| Immich | :2283 | :2443 |
| LLM Gateway | :8090 | :9443 |

🇷🇺 **Сертификат:** OpenSSL self-signed, RSA 2048, SAN с VPS IP, срок 10 лет.
🇬🇧 **Certificate:** OpenSSL self-signed, RSA 2048, SAN with VPS IP, 10-year validity.

🇷🇺 Файлы: `/opt/nas_jetson_nano/nginx/ssl/nas_jetson_nano.crt` + `nas_jetson_nano.key` (chmod 600)
🇬🇧 Files: `/opt/nas_jetson_nano/nginx/ssl/nas_jetson_nano.crt` + `nas_jetson_nano.key` (chmod 600)

🇷🇺 Скрипт: `scripts/setup/install_nginx_vps.sh` — идемпотентный.
🇬🇧 Script: `scripts/setup/install_nginx_vps.sh` — idempotent.

🇷🇺 Nextcloud trusted proxy через `occ`:
🇬🇧 Nextcloud trusted proxy via `occ`:

```bash
docker exec -u www-data homecloud_nextcloud php occ config:system:set trusted_proxies 0 --value='127.0.0.1'
docker exec -u www-data homecloud_nextcloud php occ config:system:set trusted_proxies 1 --value='193.8.215.130'
docker exec -u www-data homecloud_nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data homecloud_nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
```

---

## Последствия / Consequences

### Положительные / Positive

- 🇷🇺 Android-приложения работают вне дома через HTTPS / 🇬🇧 Android apps work remotely via HTTPS
- 🇷🇺 HTTP-эндпоинты сохранены (обратная совместимость) / 🇬🇧 HTTP endpoints preserved (backward compatibility)
- 🇷🇺 Нет влияния на Amnezia VPN контейнеры / 🇬🇧 No impact on Amnezia VPN containers

### Отрицательные / Negative

- 🇷🇺 Самоподписанный сертификат → предупреждение в браузере/приложении при первом подключении / 🇬🇧 Self-signed certificate → browser/app warning on first connect
- 🇷🇺 Нет автоматической ротации сертификата (10 лет — ручная замена) / 🇬🇧 No automatic certificate rotation (10 years — manual replacement)
- 🇷🇺 Нет HSTS (требует доверенного сертификата) / 🇬🇧 No HSTS (requires trusted certificate)

### Нейтральные / Neutral

- 🇷🇺 DAVx⁵ поддерживает `Accept untrusted certificate` — принять 1 раз в настройках / 🇬🇧 DAVx⁵ supports `Accept untrusted certificate` — accept once in settings

---

## Будущее / Future

🇷🇺 Когда появится доменное имя:
🇬🇧 When a domain name is available:

1. 🇷🇺 Настроить Let's Encrypt через certbot / 🇬🇧 Configure Let's Encrypt via certbot
2. 🇷🇺 Обновить nginx конфиги на порт 443 / 🇬🇧 Update nginx configs to port 443
3. 🇷🇺 Добавить HSTS / 🇬🇧 Add HSTS
4. 🇷🇺 Удалить самоподписанный сертификат / 🇬🇧 Remove self-signed certificate

```bash
certbot --nginx -d subdomain.example.com
```
