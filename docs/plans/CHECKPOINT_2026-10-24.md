# Checkpoint — 2026-10-24

[Русский](CHECKPOINT_2026-10-24.ru.md) · [Previous checkpoint](CHECKPOINT_2026-10-23.md)

Base: `main` at `4c482b5`. Today's subject — why the VPN does not work from home. The cause has been found, and a working workaround exists.

## Outcome

- **Why it does not work.** The home ISP breaks the path to the VPS, in three different ways:
  - XRay is cut on the **TLS fingerprint** (`fp=chrome`, large ClientHello);
  - UDP from `193.8.215.130` to home loses packets — AWG works neither in 2.0 nor in 3.1;
  - the second address `95.163.176.103` is fully closed.
- **Workaround.** XRay with the **`fp=firefox`** fingerprint works both at home and on LTE. The server needs nothing for this — only the client link changes.
- **Address for clients** — the DNS name `vpn.borovskoy.dynv6.net` → `193.8.215.130`. On the next block, one record changes, not the keys.
- **Owner's decisions:**
  - the family moves to XRay-firefox;
  - AWG 2.0 is switched off 2–3 days after the migration, then an announcement in «Боровские»;
  - the owner will reissue the new keys personally.

## Measurements from the home Wi-Fi

The workstation's sockets were bound to Wi-Fi (`IP_UNICAST_IF`); routes were not changed. Times are UTC.

| Path | Result | Boundary of conclusion |
|---|---|---|
| AWG 2.0 → `193.8.215.130:40568` (morning) | handshake present, large losses downstream; MTU excluded (MSS 1160 did not help) | one phone, one window |
| AWG 3.1, pilot → `193.8.215.130:7843` (10:17) | handshake holds; SYN 28 / SYN-ACK 54, 46 of 131 segments to the phone retransmitted; websites do not open. Works on LTE | the protocol does not matter — so the problem is in the path |
| XRay `fp=chrome` → `:443` (morning) | 333 of 339 connections break after the first ClientHello segment (1308 B) | |
| Ordinary TLS (Python) via `193.8.215.130:443` (11:03) | 444 KB in 0.8 s, twice | the address and TCP downstream are working |
| XRay `fp=firefox` → `:443` (≈11:40) | 3.2 MB in 30 s, 7 connections larger than 20 KB; owner: works at home and on LTE | one phone; whether the ISP's rule holds over time is unknown |
| `95.163.176.103` | TCP 22/443 — timeout, UDP — 0 of 3 | a complete block by address |
| `45.159.144.217` (AS203273, bought 24.10) | TCP handshake present, 0 bytes of TLS data, UDP 0 of 3. From Cloud.ru: TLS 444 KB, UDP 3 of 3 | the home ISP is cutting it, not AEZA |
| Cloud.ru VM → AEZA | TLS 444 KB through both addresses, UDP 3 of 3 | a cascade would have worked, but it was not needed |

## Changes on the VPS (with the owner's permission)

Rule 13 was checked before and after each change. Result:
- `amnezia-awg2` and `amnezia-xray` were not restarted (started 2026-10-04, 0 restarts);
- 23 AWG 2.0 peers are in place;
- only UDP 7843 was added externally.

| Change | When | Rollback |
|---|---|---|
| Full VPS dump, read only, with secrets — to the owner's local disk, outside git | 09:57–10:19 | — |
| AmneziaWG 3.1 pilot: container `amnezia-awg3`, image `amneziavpn/amneziawg-go:3.1.20260828` (`sha256:cbafc02b…`); network `amnezia-awg3-net` (bridge `amn3`, 172.29.173.0/24); UDP 7843; `/opt/amnezia-awg3`; one peer — the owner's pilot phone | 10:09 | `docker rm -f amnezia-awg3; docker network rm amnezia-awg3-net; rm -rf /opt/amnezia-awg3` |
| ufw: `7843/udp` plus 10 NAS service ports only from 172.29.173.0/24 (comment `via VPN only (awg3)`) | 10:09 | `ufw delete allow …` with the same rules |
| Third IPv4 `45.159.144.217`: added by the owner in the AEZA panel, the AEZA agent configured `enp0s3:1` itself. The default source of outgoing traffic remained `193.8.215.130` | 10:58 | delete in the panel |
| DNS: `vpn.borovskoy.dynv6.net A 193.8.215.130` (dynv6 REST, record 98668248, TTL 60). The zone apex was not touched (`95.163.176.103`) | ≈11:50 | delete the record with the same API |

The 3.1 pilot sits on a separate network, so the non-standard SNAT of the `amn0` subnet does not affect it. That rule is set by `vps-vpn-snat-fix.service`: in August, client egress was deliberately moved to `95.163.176.103`.

## Keys

- No new keys were issued.
- For existing XRay clients, links with `fp=firefox` to the DNS name were created. They are kept outside git, on the owner's local disk; the owner distributes them.
- One family member has no XRay client of their own: a copy of the owner's key was issued for now (a shared client that cannot be revoked separately). Their own key comes with the reissue.

## Retractions and errors

- **Retracted:** the morning conclusion of the October 24 addendum to the October 23 checkpoint, «the cause has not been established» — the causes have been established for XRay (fingerprint) and for AWG (UDP losses downstream on the home path).
- **Error of test order.** I advised buying the third IP before running the free discriminating test — a TLS download through the old address with an ordinary client. That test would have shown that the address was not at fault.
- **Access error.** One `curl` check from the Cloud.ru VM went out under the alias `vdk-cloud`, that is, as the neighbouring project's user `vdkadmin`, not as `nas`. It was only an outbound request; nothing was changed. Reported to atc (m0355).

## Performers and costs

- DeepSeek, 3 tasks, **$0.111**:
  - AWG 3.1 config module `scripts/vpn/awg3_conf.py` (36 tests);
  - UDP relay with a budget guard `scripts/vpn/udp_relay_guard.py` (13 tests);
  - public reference.
  - Both modules were accepted by the lead, but they remain in DeepSeek's working copies and are not merged into `main`; the relay is not needed yet.
- Claude subagents: Sonnet ×3 (AWG 3.1 information, review of the pilot scenario, Cloud.ru Compute API), Haiku ×2 (Cloud.ru prices, comparison of VPS in Russia). The tool does not show the cost.
- Cloud.ru: nothing was created; the request to atc about the relay was cancelled (m0354 → m0355). The Compute tariff (version 261014): outgoing traffic 0.00366 ₽/MB — for family traffic (about 19 GB per day) the relay is not worthwhile there.
- AEZA: the third IPv4 was bought by the owner; it is useless for home.

## Queue

1. The owner distributes the XRay-firefox links. Before distributing — check the link to the DNS name once on the owner's own phone.
2. A separate XRay client for the family member who currently uses a copy of the owner's key.
3. 2–3 days after the migration — switch off `amnezia-awg2` (the image and `/opt/amnezia` are in the dump), then an announcement in «Боровские».
4. Delete `45.159.144.217` in the AEZA panel.
5. Removing `95.163.176.103` is a separate task: first migrate SNAT (`vps-vpn-snat-fix`), the DNS zone apex, the Jetson `VPS_HOST` and the Vostro tunnel.
6. The `amnezia-awg3` pilot — keep it until the keys are reissued, then decide.
7. The owner will reissue the dynv6 token; the current one in the project records is considered compromised.
8. From the October 23 checkpoint, not touched today: replacing the Cloud.ru FM model before 02.11; the result of the OBS-1 daily acceptance.

Detailed log (outside git): `docs/local/AWG31_MIGRATION_PLAN.ru.md` §8–9, `.agent-work/tmp/home-vpn-20261024/RESULT.ru.md`, `.agent-work/tmp/awg3-migration-20261024/`.
