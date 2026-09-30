# Work Plan

> Source — the 2026-09-26 audit (`docs/audit/2026-09-26_full_audit/REPORT.md`). Only
> **confirmed** and actionable items are listed here. Russian version — `WORK_PLAN.ru.md`.
> Assignee per rule #16: **D** — DeepSeek (mechanical work by card), **C** — Claude (lead),
> **O** — owner (sudo on the device, decisions). Complexity: S / M / L.

## Wave 1 — live system, now

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 1.1 | ✅ **API-1 (2026-09-27):** HDD `os.statvfs`/`exists` calls run through shared `blocking.run_io` in `asyncio.to_thread` with a timeout; timeout means `disk_down` | C | S | `test_blocking_io.py`: a hanging disk does not hold the loop, `/healthcheck` responds, downloads/storage/system covered |
| 1.2 | ✅ **OPS-2 (2026-09-30):** the Jetson daily report and Vostro offsite backup load `VPS_HOST` from root-owned `/opt/nasa/config/.env`; deployed scripts contain no literal VPS address | C | S | [live evidence](docs/plans/OPS2_VPS_CONFIG_DEPLOY_2026-09-30.md): systemd report sent Telegram message 349; offsite backup completed successfully |
| 1.3 | ✅ **OPS-1 (2026-09-30):** the host watchdog is installed and enabled; every 2 min it starts eligible `homecloud_*` containers with restart policy `always`, restarts `unhealthy` ones, honours global/per-container pause markers and the maintenance label, and alerts the owner in Telegram | C | M | [live evidence](docs/plans/OPS1_WATCHDOG_DEPLOY_2026-09-30.md): maintenance skip observed; timer recovery in 123 s; Telegram delivery accepted |
| 1.4 | **CF-2:** Docker log rotation — `log-opts` `max-size=10m`, `max-file=3` in `daemon.json` (+ default in compose) | C + O (sudo, Docker restart in a maintenance window) | S | `docker inspect` shows `max-size` |
| 1.5 | **HK-1:** atomic move in `on_complete.sh` (`mv -n` + retry with the next suffix or `flock` on the directory) | D (test) + C | S | concurrent test of two hooks with the same name: both files intact |

## Wave 2 — security

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 2.1 | **GW-3:** Russian secret triggers in `TOKEN_RE` (пароль, ключ, код, пин, секрет), separator — `:`/`=`/space | C | S | a set of Russian phrases with a password/code is redacted |
| 2.2 | ✅ **API-2/3 (2026-09-30):** API HEAD requests use checked manual redirects; the Jetson `NAS-DL-EGRESS` barrier rejects aria2 IPv4 traffic to `10/8`, `172.16/12`, `192.168/16`, `127/8` and `169.254/16` and is refreshed every 2 min | C | M | [live evidence](docs/plans/API23_EGRESS_DEPLOY_2026-09-30.md): private redirect not followed; container→`192.168.0.1` rejected with counter hit; public control passed |
| 2.3 | **SH-1:** `cloudru_iam_token_example.sh` — response via stdin, not via heredoc | D | S | a fake response with `'''` does not execute code |
| 2.4 | **CI-1 / SEC-1:** trivy on tag+SHA; gitleaks without `--no-git` (history) | C | S | the job fails on a test secret in the branch history |
| 2.5 | **DP-2:** NAS API not as root; `docker.sock` via socket-proxy with `GET /containers/json` only | C | M | `test_api_access` + manual `/v1/containers` |
| 2.6 | **DP-1 / DEP-2:** pin image versions (netdata, portainer, samba, beszel, nextcloud, immich); gate check "no `:latest`" | D (inventory) + C | S | gate-grep |
| 2.7 | **DEP-1:** pin NAS API dependencies (`==` + lock with hashes); evaluate replacing `python-jose`/`passlib` | C | S/M | `service-tests` green after pinning |
| 2.8 | **SH-2 / HK-2:** a shared `tg_send()` in `scripts/lib/` — token not in argv; temp file on the VPS via `mktemp` | D + C | M | grep check: no `bot${TELEGRAM_BOT_TOKEN}` in argv |
| 2.9 | **SEC-2:** `check_no_secrets.sh` scans `*.md` with a narrow allowlist | D | S | a test secret in a `.md` is caught |

## Wave 3 — reliability and quality

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 3.1 | **SD-2:** remove literal paths from 14 units → `${NAS_JETSON_NANO_PROJECT_DIR}` / `/etc/nas-layout.env`; guard in the gate | D + C | M | grep-guard: no `/home/admin`, `/opt/nasa` in `systemd/*.service` |
| 3.2 | **SD-1:** `nas-offsite-backup.sh` — check that `$WORKDIR` is non-empty before `restic backup` | D | S | test "empty stream → exit 1" |
| 3.3 | **GW-1 / GW-2:** a single normalized user key; budget reservation under a lock before the call | C | M | case does not bypass the limit; N parallel requests do not exceed the limit by more than one in flight |
| 3.4 | **SD-3:** `flock` on `/mnt/hdd2tb` in every HDD walk script | D + C | S | two runs: the second is refused immediately |
| 3.5 | **QA-1/2/3:** vermin in CI; rename the `app` packages or isolate the run; `tests/unit` collected via pytest | D | S/M | CI green, a combined run without false failures |
| 3.6 | **API-4/5:** close the Telegram client; caps on state lists and the outbox | D | S | close test, eviction test |
| 3.7 | rotate `jms583-health.log`, delete `nasa-api.jsonl.*` after the migration | C + O | S | — |
| 3.8 | **BK-1:** if backup-api is going to be enabled — sanitize the file name + `USER`; otherwise remove the "production" code until the RFC | C | S | traversal tests |

## Owner decisions

- 2.2: the network barrier changes iptables on the Jetson — a window and consent are needed.
- 1.4: Docker restart — a maintenance window (all services for ~1 min).
- 3.8: backup-api — fix it or remove it.
