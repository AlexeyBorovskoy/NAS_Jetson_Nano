# Full project audit — 2026-09-26

> Repository state: `main` @ `ade78aa`, working tree clean. Live measurements — Jetson and VPS,
> 2026-09-26 05:25–05:34 UTC, read-only. Production logic was not changed during the audit.
> Remediation plan — `WORK_PLAN.md` in the root. Russian version — `REPORT.ru.md`.

## 1. Coverage

| Domain | Who | How |
|---|---|---|
| NAS API and bots (`services/nas_jetson_nano-api`) | Sonnet subagent (read-only) | review, ruff, bandit, 3 reproductions |
| LLM gateway, watchdog, backup-api | Sonnet subagent | review, ruff, bandit, 4 reproductions |
| Host scripts, systemd, aria2 hooks | Sonnet subagent | review, `bash -n`, vermin, 3 reproductions |
| Deploy, compose, CI, dependencies, secrets in git | Sonnet subagent | review, `git ls-files`, `git log -p -S`, check_no_secrets |
| Analyzers and coverage | DeepSeek executor → lead | DeepSeek hit its permission limits (only pytest ran), the lead ran the rest |
| Live Jetson/VPS resources | lead | `docker stats`, fd, logs, swap, ufw, traffic |
| Finding verification | lead | every critical claim checked against code or by command; 2 findings refuted |

Not covered: the Android part (`docs/android`), `archive/`, documentation as such (separate work under rule #15 is under way), load measurements (no test bench).

## 2. Tools and tests

| Tool | Result |
|---|---|
| `pytest tests/nas_api` / `llm_gateway` / `watchdog` | 160 / 44 / 44 — all green |
| the same set **in one process** | 43 false failures — `app` package conflict (finding QA-2) |
| `pytest tests/unit` | does not collect (finding QA-3) |
| `coverage` per service (separately) | **69 %**: `talk_bot.py` 50 %, gateway `main.py` 69 %, `downloads.py` 87 %, `telegram_bot.py` 85 % |
| `ruff` E,F | 16 minor (7 unused imports) |
| `ruff` B,S,ASYNC,BLE | 35 broad `except`, 13 `urlopen`, 5 blocking calls in async, 7 `raise` without `from` |
| `bandit -ll` | 7 × B310 (`urlopen`) — expected, not defects |
| `mypy` (NAS API) | 45 type errors, none of them real defects (spot-checked) |
| `vermin --target=3.6-` over `scripts/` | clean |
| live: `docker stats`, fd, ufw, vnstat | see section 4 |

## 3. Confirmed defects

Class: **C** — confirmed (reproduced or proven by code), **L** — likely.

| ID | Sev | Where | Issue | Class |
|---|---|---|---|---|
| API-1 | critical | `downloads.py:130-137`, `routers/storage.py:24-44`, `routers/system.py:61-75` | synchronous `os.statvfs`/`exists` on the HDD in the event loop: a hung ntfs-3g (as on 20.09) stops the whole process — HTTP, `/healthcheck`, the bot, downloads. **The supervisor `db458f7` does not save it from this.** The right technique already exists in `talk_bot.py:254` | C |
| GW-3 | high | `llm-gateway/app/main.py:82` | the secrets filter only knows English words: «пароль от роутера: …», «код …» go to the cloud as is | C (repro.) |
| API-2 | high | `downloads.py:140-147` | `_head_size` follows redirects without checking: a public link leads to an internal address (SSRF). aria2 itself also follows redirects — only the network barrier is reliable | C (repro.) |
| API-3 | high | `downloads.py:150-161,247-262` | DNS rebinding between the address check and the download | C (repro. with a fake resolver) |
| HK-1 | high | `services/downloads/on_complete.sh:37-56` | name-selection race: two simultaneous downloads with the same name — the second silently overwrites the first (`max-concurrent-downloads=2`) | C (repro.) |
| SD-1 | high | `scripts/setup/nas-offsite-backup.sh:13-19` | an empty `tar` stream + `restic backup` with no check = a "successful" empty snapshot | C (repro.) |
| SH-1 | high | `scripts/sber/cloudru_iam_token_example.sh:24-26` | the server response is substituted into Python code through an unquoted heredoc — code execution | C (repro.) |
| SD-2 | high | 14 units in `systemd/` | hardcoded `/home/admin/nas_jetson_nano`, `/home/admin/nasa`, `/opt/nasa` instead of the layout — the class of defect that broke SSD recovery for 11 days | C |
| OPS-1 | high | Docker on the Jetson | a container stopped with `docker kill`/`stop` is **not brought up** by `restart: always`; there is no watchdog. Verified by a live test on 2026-09-26: 134 s in `Exited (137)` | C (live) |
| OPS-2 | high | `/usr/local/sbin/nasa-send-report-telegram.sh:12`, `scripts/setup/nas-offsite-backup.sh:13` | the VPS address is hardcoded (`95.163.176.103`, blocked by the provider since 18.09): the daily report has been failing since 23.09 | C (live) |
| DP-1 | high | `docker-compose.monitoring.yml:36-66` | Netdata: `pid:host` + `SYS_ADMIN` + `docker.sock` + the `:latest` image — nearly root on the host with an uncontrolled version | C |
| DP-2 | high | `services/nas_jetson_nano-api/Dockerfile` + compose `:19` | the API runs as root and holds `docker.sock` (`:ro` does not restrict the Docker API) | C |
| CI-1 | high | `.github/workflows/quality-checks.yml:121` | `trivy-action@master` — execution of third-party floating code in CI | C |
| SEC-1 | high | `quality-checks.yml:95,112,117` | gitleaks with `--no-git`: history is not scanned, although the comment promises it | C |
| DEP-1 | high | `services/nas_jetson_nano-api/requirements.txt` | all dependencies are `>=`, with no lock; `python-jose`/`passlib` with a CVE history and no maintenance — in the authentication service | L (versions not verified without network) |
| BK-1 | high* | `services/backup-api/app/main.py:157-166` | path traversal in upload; *the service is not deployed (not in compose/systemd) — critical when enabled | C (repro.) |
| GW-1 | medium | `llm-gateway/app/main.py:238-259` | the limit is looked up via `lower()`, the counter is not: case in `user` bypasses the personal quota | C (repro.) |
| GW-2 | medium | `llm-gateway/app/main.py:262-314` | budget checked before the call, accounted after: parallel requests exceed the limit (×10 in the repro.) | C (repro.) |
| CF-2 | medium | all compose files, `/etc/docker/daemon.json` | container logs without `max-size` — unbounded growth | C (live) |
| DEP-2 | medium | compose: netdata, portainer, samba, beszel, nextcloud, immich | floating tags (`latest`, `apache`, `release`) — non-reproducible deploy | C |
| API-4 | medium | `telegram_bot.py:73` | the bot's `httpx.AsyncClient` is never closed | C |
| API-5 | medium | `telegram_bot.py:198,302`; `downloads.py` outbox | state lists and the outbox have no cap during a long outage | C |
| QA-1 | medium | `.github/workflows/*` | vermin (Python 3.6 on the host) is not in CI, locally it is only a warning | C |
| QA-2 | medium | `services/*/app` | two packages named `app`; a combined test run produces 43 false failures | C (repro.) |
| QA-3 | medium | `tests/unit/*` | `pytest tests/unit` does not collect the tests; 15 regression tests run only when invoked directly | C |
| SD-3 | medium | backup/restore scripts on `/mnt/hdd2tb` | no `flock` — nothing prevents two ntfs-3g walks (the hang mechanism of 20.09) | L |
| SH-2 | medium | 6 monitoring scripts | the Telegram token in the `curl` URL — visible in `ps` | C |
| HK-2 | medium | `send-report-telegram.sh:46-56`, `install_usb_watchdog.sh:65-75` | a predictable `/tmp/…-$$.env` with a token on the VPS | L |
| SEC-2 | medium | `scripts/security/check_no_secrets.sh:29` | `*.md` is excluded from the secrets check entirely | C |
| GW-6 | low | `llm-gateway/app/main.py:721-740` | the DeepSeek client has no explicit timeout | L |
| API-6…9, BK-3, CF-4…7, CI-2, SD-5, SH-3 | low | see the subagent appendices | docstrings, N+1 in `/v1/users`, global httpx logger level, JWT exception text in the response, pinning actions to SHA, and the like | C/L |

### Refuted during verification (kept as a record)

| ID | Agent claim | Why it is wrong |
|---|---|---|
| SD-4 | "the backup units have no `TimeoutStartSec` — systemd will kill them after 90 s" | all three are `Type=oneshot`, and their start timeout is disabled by default |
| CF-1 | "Beszel on the VPS listens on `0.0.0.0:8091` — open to the internet" | ufw allows 8091 only from `172.29.172.0/24` and `10.8.1.0/24`; from home the port is closed (verified). Remains low: defense in depth |
| (own) | "test 1: aria2 crashed and came back up in 9 s" — the lead | aria2 is PID 1 in the container, `kill -9` from inside does not take it; the process did not crash. Repeated with `docker kill` → found OPS-1 |

## 4. Performance and leaks (live measurements 2026-09-26)

| What | Measurement | Conclusion |
|---|---|---|
| NAS API memory | 70 → 66 MB in 9 min, fd 22 → 21 | no leak visible |
| aria2 memory | 70 → 120 MB of the 192 limit, fd 143 → 169 (2 active torrents) | watch it: with a 192 MB limit an OOM is possible on large swarms |
| host swap | 881 → 1096 MB in 9 min, swapping under way | memory pressure grows along with downloads |
| Netdata | 215–229 MB of 320, 114 threads, 16 % CPU | the heaviest observer on a 4 GB device |
| Docker logs | without `max-size` (OPS/CF-2) | unbounded growth |
| `jms583-health.log` | 53 thousand lines since June, no rotation | slow growth |
| old `nasa-api.jsonl.*` | ~60 MB since August, never deleted | litter after the rename |
| VPS | CPU idle, no steal, ~610 Mbit/s outbound, no loss | the phone's slow VPN is not VPS capacity (see section 9) |

## 5. Security

- **Strengths (verified):** JWT and roles — the test walks every route; the gateway service token is compared in constant time; atomic journal writes; the gateway's `save_path` is protected against traversal; the aria2 hooks validate paths and names; no secrets found in the git history (targeted `git log -p -S`); Portainer only on `127.0.0.1`.
- **Weak points:** PII leakage past the Russian-language filter (GW-3); SSRF in downloads (API-2/3) — only a network barrier for the aria2 container treats it; `docker.sock` in two containers with broad privileges (DP-1/2); the supply chain (CI-1, DEP-1, DEP-2); the CI secrets check does not do what it promises (SEC-1); SH-1 — code execution in a diagnostic script.

## 6. Architecture

1. **One event loop for four subsystems** (API, Telegram, Talk, downloads). Any blocking call stops all four (API-1). The supervisor treats "crashed/went silent" but not "hung synchronously" — this must be written down as a limitation and closed by moving I/O into threads with a timeout.
2. **Self-healing is incomplete:** inside a process — the supervisor (present), journal reconciliation with aria2 (present); between containers — nothing (OPS-1): Docker does not bring up what was stopped from outside and does not react to `unhealthy`.
3. **git ↔ device divergence** still produces defects: hardcoded paths (SD-2), old copies of scripts in `/usr/local/sbin` with the VPS address baked in (OPS-2).
4. **The gateway is the right single egress point to the cloud**, but budget accounting is not atomic (GW-2).

## 7. Test quality

Coverage 69 %. Recent incidents are well covered (downloads 87 %, bot 85 %, aria2 reconciliation, journal concurrency). Weak — `talk_bot.py` (50 %), API routes (51–63 %). There are no tests for: the SSRF redirect and rebinding, a blocking disk, the hook race, an empty backup source, Russian secrets, the budget race, backup-api at all. Test infrastructure: the `app` package conflict (QA-2), `tests/unit` outside pytest (QA-3), vermin outside CI (QA-1).

## 8. Technical debt (not defects)

35 broad `except`, 45 mypy errors, unused imports, `/proc/uptime ... and time()` in `storage.py:56`, two path styles in the units, secrets in `environment:` instead of `secrets:`, a private submodule with no explanation in the README.

## 9. Separate question: slow VPN on the phone

Measured through the same tunnel from the workstation: 33 Mbit/s, 60–100 ms latency to the VPS, 1.0–1.6 s to open a site (TLS through Frankfurt). The VPS is not loaded. Some Russian sites cut foreign IPs (`gosuslugi.ru` — timeout from the VPS, `wildberries.ru` — 498). Recommendation — split tunneling in the AmneziaVPN app on the phone; control tooling on the VPS already exists (`vnstat`, the Beszel agent).

## 10. Unknowns and blockers

- The dependency versions of the NAS API that are actually in the image were not checked against a CVE database (the audit had no network).
- Exploiting API-1 on a real hung ntfs-3g was not reproduced (deliberately — it takes the HDD down).
- SD-3 (parallel HDD walks) — by code only.
- The cause of QA-3 (`tests/unit` not collecting) — DeepSeek's hypothesis about a `sys.stdout` substitution, not verified.
- Fixes on the device with `sudo` (OPS-1, OPS-2) are blocked by the agent's permission classifier — the owner performs them.
