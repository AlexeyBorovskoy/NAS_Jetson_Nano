# API-2/3 — SSRF and downloader egress deployment evidence

Date: 2026-09-30. Device timestamps are UTC. Tests used only read-only HTTP HEAD
requests; no router, VPN or production-service configuration was changed.

## Result / Результат

API-2/3 is complete. The NAS API no longer delegates HTTP redirects to the
client automatically: every destination is parsed and DNS-checked before a
bounded manual HEAD request. Independently, the aria2 Docker subnet is attached
to a host-level IPv4 rejection chain refreshed by the two-minute watchdog timer.

API-2/3 завершён. NAS API больше не передаёт редиректы HTTP-клиенту автоматически:
каждый адрес разбирается и проверяется через DNS до ограниченного ручного HEAD.
Независимо от этого Docker-подсеть aria2 подключена к host-level IPv4-барьеру,
который обновляется двухминутным timer watchdog.

## Code evidence / Код

- Commit `132b606`: `_head_size()` uses `follow_redirects=False`, validates the
  initial URL and every `Location`, checks DNS, and allows at most three redirects.
- Tests prove that an internal `Location` is never requested and that a checked
  public redirect can return its Content-Length.
- Commit `6e27ddf`: first-install application of `dl_egress_guard.sh` no longer
  fails when its stale-rule search correctly finds no rows.
- Static guard tests cover all five blocked ranges, established-flow handling,
  both parent chains, Docker network discovery, persistence wiring and the clean
  first-install path.

## Live Jetson evidence / Живые доказательства Jetson

- Deployed revision: `6e27ddf`.
- Downloads network: `homecloud-downloads_default`, container address
  `172.26.0.2`, subnet `172.26.0.0/16`, IPv6 disabled.
- `NAS-DL-EGRESS` contains `REJECT` rules for `10/8`, `172.16/12`,
  `192.168/16`, `169.254/16`, and `127/8`, preceded by
  `ESTABLISHED,RELATED RETURN`.
- Exactly one source-subnet jump exists in each parent: `DOCKER-USER` and `INPUT`.
- Private probe from `homecloud_downloads`:
  `wget --spider http://192.168.0.1/` returned non-zero in 1,231 ms; the
  `192.168.0.0/16` rule counter increased from 0 to 2 packets.
- Public control from the same container:
  `wget --spider http://example.com/` returned zero.
- A repeated systemd application logged
  `dl-egress: барьер ... на месте`, returned `Result=success`/status 0, and did
  not duplicate either parent jump.
- Rebuilt `homecloud_nasa_api` is `healthy`; host `/healthcheck` returned HTTP 200;
  the running image contains the checked manual-redirect implementation.

## Verification / Проверка

- Focused API/guard suite: 74 passed.
- Full repository gate: regression 19; LLM gateway 44; NAS API 212; watchdog 44;
  backup API 24 passed/1 skipped; STT 17.
- Non-blocking local warnings remain unchanged: ShellCheck and local Docker were
  unavailable; three non-Immich `:latest` tags remain tracked as DEP-2.

## Residual limits / Остаточные ограничения

- The host rule is IPv4-only. This is adequate for the observed downloads network
  because Docker reports IPv6 disabled. Enabling IPv6 requires an equivalent
  nftables/ip6tables policy first.
- A DNS name could theoretically rebind between the API's resolution check and
  its socket connection. aria2 remains protected at the host layer; complete API
  process isolation would require its own egress namespace/proxy policy.
- The combined systemd service deliberately ignores a guard command failure so
  container recovery still runs. Operators must verify the `dl-egress` journal
  line and actual iptables rules, not infer firewall health from service success.
