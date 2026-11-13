# Project Checkpoint — 2026-11-13

**Status:** `CORPORATE_VPS` and `G1` (isolated local HTTPS backend) completed; home validation **`P0b`** and **`G2`** window approval scheduled for `2026-11-14`.  
**Working artifacts (gitignored):** `artifacts/vpn-audit-20261112/`, `artifacts/vpn-corporate-validation-2026-11-13/`, `artifacts/reports/amnezia-https-study-2026-11-13/`.

---

## 1. Verified State (`OBSERVED`, 2026-11-12/13)

1. **VPS Read-Only Audit (`B1–B5`):**
   - Three IPv4 addresses on the Austrian VPS (`Ubuntu 24.04.4 LTS`, ~1.9 GiB RAM): `193.8.215.130` and `95.163.176.103` (`AS210644`), `45.159.144.217` (`AS203273`); IPv6 `2a12:5940:665a::2/48`.
   - `amnezia-awg2` (`40568/udp`, 23 peers), `amnezia-xray` (`Xray 25.8.3`, VLESS+TCP+REALITY, `0.0.0.0:443` / `[::]:443`, `Mounts=[]`, 11 clients in `server.json` / 10 entries in `clientsTable`), `amnezia-awg3` (`7843/udp`, `3.1.20260828`, no `I1` in server config).
   - Production `amnezia-awg2`, `amnezia-awg3`, `nasa_nginx`, `beszel_hub`, and `sshd` remain untouched.

2. **Corporate Validation (`C1–C6`, `2026-11-13`):**
   - `C2`: `10/10` direct TCP connections to `193.8.215.130:443` over `Ethernet` (`51.22–70.03 ms`).
   - `C3`: `10/10` cold `Xray 25.8.3` (`fp=firefox`, localhost SOCKS) → `HTTP 200` (egress `95.163.176.103`).
   - `C5`: `5/5` flows inside the VPS `tcpdump` window confirmed exact delivery of the `672`-byte TLS `ClientHello` with zero retransmissions.
   - Working `AWG2` (`10.8.1.6`) and routes remained intact throughout.

3. **Stage `G1` (Isolated HTTPS Backend, `2026-11-13`):**
   - Created `webtest.borovskoy.dynv6.net A → 45.159.144.217` (verified on `ns1..ns3.dynv6.com`; root `borovskoy.dynv6.net` `95.163.176.103` unchanged, no `AAAA` added).
   - Issued trusted Let's Encrypt certificate (`certbot 2.9.0`, manual `DNS-01`, `CN=YE1`, valid until `2027-02-11`, manual renewal) in `/opt/amn-https-lab/certbot/`.
   - Deployed `caddy-lab.service` (`Caddy v2.11.9`, `SHA-512` verified) strictly on `127.0.0.1:18443` (`admin off`, HTTP/1.1 + HTTP/2, HTTP/3 disabled, key `640 root:caddy-lab`).
   - Local HTTPS checks (`/`, `/health` `AMN-HTTPS-LAB-OK-v1`, `/test/64k.bin`, `/test/1m.bin`, `/missing-test-path`, TLSv1.3 `Verify return code: 0`) passed. Zero new public listeners.

4. **`G2` Pre-Authorization Prep (`READ-ONLY`):**
   - Backed up `/opt/amnezia/xray` and container/network metadata to `/root/backups/xray-pre-g2-20261113/` (`SHA-256` 6/6 match, isolated `CONFIG_VALIDATION_PASS`: `xray run -test` = `Configuration OK`).
   - Prepared `CHANGE_DIFF.md`, `ROLLBACK.md` (two-tier rollback + `systemd-run` / `flock`), `PORT_PLAN.md`, `CLIENT_MATRIX.csv`, and unified morning plan `UNIFIED_HOME_RESEARCH_PLAN_20261114_RU.md`.

---

## 2. Next Steps (`2026-11-14`, at home)

1. **`P0b` on separate Android (`HOME_WIFI → LTE → HOME_WIFI`):**
   - Keep the owner's main Windows laptop (running a third-party management VPN for Codex/SSH) completely untouched.
   - Test `193.8.215.130:443` (`fp=firefox`), `AWG2`/`AWG3`, and `45.159.144.217:443` if needed on the separate Android (mobile data OFF during Wi-Fi; Wi-Fi OFF during LTE).
2. **`G2` Window (only upon explicit owner approval):**
   - Address-bind **only `amnezia-xray`** to `193.8.215.130:443`, `95.163.176.103:443`, and `[2a12:5940:665a::2]:443` to free `45.159.144.217:443`.
3. **Comparative Lab `G3` (`W0 → R0 → R1 → R1-NATIVE`):**
   - Execute on `45.159.144.217:443` per `AMN-HTTPS-RESILIENCE-2026-11-13` (v1.1).
