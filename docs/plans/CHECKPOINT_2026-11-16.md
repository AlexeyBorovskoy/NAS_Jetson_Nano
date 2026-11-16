# Project Checkpoint — 2026-11-16

**Scope:** Deployment and acceptance testing of the new Swedish family VPN server (`NEW-VPS-FAST-01`), Let's Encrypt TLS issuance, and onboarding of isolated family accounts.

---

## 1. Swedish VPS Infrastructure

- **Host:** `45.140.13.178` (`broken-indigo.ptr.network`, `Ubuntu 24.04.1 LTS`, KVM Aeza, SSH alias `aeza-sweden`).
  - *Note:* the initial IP `82.148.227.55` was unreachable directly from Russian home Wi-Fi and LTE (ICMP/TCP timeouts); the owner rotated the VPS IP to `45.140.13.178`.
- **Domain:** `vpn.privet.dynv6.net` (`A 45.140.13.178`, no `AAAA` record, verified via `@1.1.1.1`).
- **Server stack:** official signed `sing-box 1.14.4` (`deb.sagernet.org`), `systemd` drop-in restricting capabilities to `CAP_NET_BIND_SERVICE` only, running as `sing-box` user.
- **Two active transports on port `443`:**
  1. **`hy2-in` (`Hysteria 2`, `UDP/443`, primary):** `alpn: ["h3"]`, `masquerade: "https://www.bing.com"`, integrated with Let's Encrypt TLS (`/etc/sing-box/tls/fullchain.pem`, `privkey.pem` `0640 root:sing-box`).
  2. **`vless-reality-in` (`VLESS + xtls-rprx-vision + REALITY`, `TCP/443`, fallback):** SNI `www.googletagmanager.com`.
- **Firewall (`ufw`):** default deny incoming; allowed `22/tcp`, `443/tcp`, `443/udp`, `80/tcp` (ACME HTTP-01).
- **Anti-SSRF:** `sing-box` `route.rules` rejects `ip_is_private: true` and private/CGNAT CIDRs.

---

## 2. Let's Encrypt TLS & Automated Renewal

- Installed `certbot 2.9.0`, issued ECDSA certificate for `vpn.privet.dynv6.net` (valid until `2027-02-14`, `openssl verify` → `OK`).
- Configured deploy-hook `/etc/letsencrypt/renewal-hooks/deploy/sing-box-tls.sh`: atomic sync to `/etc/sing-box/tls/`, `sing-box check`, service restart, and `journald` logging.
- Verified `certbot renew --dry-run` → `success` and active `certbot.timer`.
- Pre-TLS backup saved to `/root/backup-tls-20261116T083718Z/` (`chmod 700`, `SHA256SUMS.txt`).

---

## 3. Clients & Family Onboarding

- **Test device (`hagircbmsszlx4in`):** `FlClash 0.9.3 (com.follow.clash)`, `gvisor` stack, DNS hijack ON, IPv6 OFF, `Always-on` (`lockdown=0`), Doze whitelist.
- **Acceptance checks:** `T0`, `T1` (5/5), `T1-ALT` (`VLESS+REALITY`), `T3` (YouTube), `T4` (Telegram `@telegram`), `T6` (5+ min sleep), `T7` (no DNS/WebRTC/IPv6 leaks on `ipleak.net`), `T8` (Chrome `45.140.13.178`). `T2` (home LAN) and `T5` (LTE) deferred until back on home Wi-Fi with active LTE data.
- **Family accounts (5 isolated profiles stored outside Git under `C:\Users\Alexey\.ssh\new-vps-se\family\`):**
  - `olga-android`, `ulyana-android-1`, `ulyana-android-2`, `ivan-android`, `ivan-windows`.
  - Strict certificate verification (`skip-cert-verify: false`) and `DIRECT` bypass for home LAN and `.ru`/`.su`/`.рф`/`vk.com` domains.
  - Verified `FAMILY-SE-Olga-Android.yaml` on phone: `api.ipify.org` → `45.140.13.178`, `yandex.ru/internet` → local ISP IP (`84.52.101.142`, `DIRECT`).
- **Local reports & end-user guide (in ignored `artifacts/`):**
  - `artifacts/reports/new-vps-fast-2026-11-15/RESULT.md`, `TEST_RESULTS.csv`, `RUNBOOK.md`, `TLS_LE_AUDIT_2026-11-16.md`, `FAMILY_SETUP_GUIDE.md`, `FAMILY_SETUP_GUIDE.pdf`.

---

## 4. Owner Follow-up Actions

1. Rotate temporary credentials previously shared in chat (Aeza API key, `root` password, `dynv6` token).
2. Verify home LAN access (`http://192.168.0.1`, `http://192.168.68.1`) with VPN active (`T2`) once at home.
3. Distribute family `.yaml` profiles and `FAMILY_SETUP_GUIDE.pdf` (for `Hiddify` from Google Play).
