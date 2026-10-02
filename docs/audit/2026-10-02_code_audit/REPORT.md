# Code audit 2026-10-02 — structure, hotspots, duplicated knowledge

> Commit `7637f41`, measured 2026-10-02. Read-only: production code was not changed.
> The previous audit (`../2026-09-26_full_audit/`) was about security and operations; its
> findings are not reopened here, they are referenced by ID (QA-2, SH-2, GW-2…). Russian
> version — `REPORT.ru.md`. Plan — `PLAN.md`. Numbers — `baseline.json`, raw output — `raw/`.

## 1. Summary

- **Project:** a home NAS on a Jetson Nano: three FastAPI services (NAS API with the Talk/Telegram
  bots and the downloader, LLM gateway, STT), a watchdog on the VPS, ~50 shell maintenance scripts, systemd, compose.
- **Stack (FACT, from the manifests):** Python 3.6 on the Jetson host (scripts, checked by `vermin`),
  Python 3.12 in containers (`services/*/Dockerfile`), bash, docker compose, systemd.
  Tests: pytest (5 suites) + 21 unit scripts, CI — `.github/workflows/quality-checks.yml`.
- **Size:** 103 production files, **10,116 lines of code** (Python 6,287, shell 3,829);
  tests 7,362 lines (0.73 per line of code). Top-10 files by size — **39.6 %** of the code.
- **Thresholds:** 7 modules in `fail`, 27 in `warn`; no import cycles; duplication in production
  code 2.6 % (6.3 % with tests).
- **Tests:** all green (344 pytest + 21 unit). Coverage of services and scripts — **68 %**
  (lines and branches together, `raw/coverage.txt`).

**Three main conclusions**

1. **The risk is concentrated in four files of the NAS API and the gateway**: `talk_bot.py`, `llm-gateway/app/main.py`,
   `telegram_bot.py`, `downloads.py` — 2,469 lines (24 % of the code) and **19 of 34** fix commits
   touching `services/`. The worst of them is `talk_bot.py`: it changes more often than any other (18 commits,
   8 fixes) and has the worst coverage (**47 %**).
2. **The cause of the growth is the absence of a service layer.** The FastAPI routers serve as each
   other's library: `talk_bot.py` calls **9 private functions** of other routers, `telegram_bot.py`
   calls the private `_build_health` of the Talk router. Every new bot capability therefore
   lands in `talk_bot.py` (mechanism K/C, §4).
3. **Fixes do not reach the copies.** Proven twice: the HDD hang fix (API-1) was not
   ported into the bot's HDD check — the path to a repeat of the 2026-09-20 incident is open (F-01); the
   host layout fix (`layout.sh`) did not reach 10 scripts or the built-in USB watchdog (F-09).

## 2. Metrics by package

FACT (`python scripts/quality/code_metrics.py`). "Catches/suppressions" — `except Exception`,
bare `except`, silent handlers (Python); `|| true` and `2>/dev/null` (shell).

| package | files | loc | fail | warn | max CC | catches/suppr. | dup. lines | commits (fix) | dated comm. |
|---|---|---|---|---|---|---|---|---|---|
| `services/nas_jetson_nano-api` | 23 | 3624 | 2 | 5 | 27 | 59 | 46 | 78 (40) | 32 |
| `scripts/monitoring` | 15 | 1750 | 3 | 4 | 19 | 73 | 87 | 47 (15) | 12 |
| `services/llm-gateway` | 1 | 900 | 1 | 0 | 26 | 16 | 12 | 14 (5) | 11 |
| `scripts/storage` | 10 | 581 | 1 | 3 | 6 | 47 | 47 | 38 (16) | 0 |
| `scripts/backup` | 10 | 569 | 0 | 1 | 8 | 10 | 6 | 19 (5) | 2 |
| `scripts/sber` | 9 | 434 | 0 | 0 | 9 | 14 | 0 | 15 (5) | 11 |
| `scripts/diagnostics` | 5 | 359 | 0 | 4 | 14 | 29 | 26 | 20 (6) | 0 |
| `scripts/quality` | 3 | 337 | 0 | 2 | 12 | 5 | 6 | 11 (5) | 7 |
| `services/watchdog` | 3 | 229 | 0 | 1 | 9 | 7 | 22 | 9 (5) | 3 |
| `services/backup-api` | 2 | 176 | 0 | 0 | 8 | 0 | 0 | 3 (1) | 1 |
| `services/downloads` (aria2 shell hooks) | 3 | 120 | 0 | 0 | 4 | 3 | 0 | 10 (7) | 3 |
| `services/stt` | 1 | 97 | 0 | 0 | 8 | 1 | 0 | 1 (0) | 3 |
| other `scripts/*` (9 packages) | 18 | 940 | 0 | 7 | 10 | 48 | 14 | 44 (17) | 7 |

370 functions in total: longer than 60 lines — 3, more complex than CC 12 — 15. Python: 56 broad
catches, 50 silent ones.

## 3. Hotspots

`hotspot = (commits / max) × (Σ CC / max)`, for shell complexity = loc/10. ⚠️ **The history window is
4 months** (first commit 2026-05-31 after `filter-repo`), so the signal from shell scripts is weak.

| # | file | score | commits (fix) | loc | max CC (function) | coverage |
|---|---|---|---|---|---|---|
| 1 | `services/nas_jetson_nano-api/app/routers/talk_bot.py` | 0.930 | 18 (8) | 685 | 16 `_handle_image_request:749` | **47 %** |
| 2 | `services/llm-gateway/app/main.py` | 0.778 | 14 (5) | 900 | 26 `chat:1028` | 66 % |
| 3 | `services/nas_jetson_nano-api/app/downloads.py` | 0.486 | 10 (7) | 447 | 18 `_reconcile:389` | 88 % |
| 4 | `services/nas_jetson_nano-api/app/telegram_bot.py` | 0.480 | 11 (5) | 437 | 27 `_dispatch:249`, nesting 6 | 88 % |
| 5 | `scripts/monitoring/nas_jetson_nano-talk-alert.py` | 0.220 | 8 (3) | 300 | 15 `check_cloudru_consumption:299` | **31 %** |
| 6 | `scripts/quality/preflight.sh` | 0.054 | 9 (5) | 216 | — | — |
| 7 | `scripts/monitoring/nas_jetson_nano-container-watchdog.py` | 0.052 | 4 (1) | 126 | 19 `main:110` | not measured¹ |
| 8 | `services/watchdog/vps/nas_liveness.py` | 0.047 | 4 (2) | 121 | 9 | 92 % |
| 9 | `scripts/sber/check_cloudru_consumption.py` | 0.031 | 3 (2) | 153 | 9 | 78 % |
| 10 | `scripts/monitoring/nas_jetson_nano-daily-report.sh` | 0.030 | 5 (3) | 217 | — | — |

¹ A test exists (`tests/unit/test_container_watchdog.py`), but the module is loaded by path through
`importlib`, and `coverage --source` does not see it. This is a limitation of the measurement, not an absence of tests.

CONCLUSION: points 1–4 stand an order of magnitude apart from the rest — this is where the work is.

## 4. Findings

New findings — `CQ-NN`. Priority: P1 — a repeat of a known incident or data corruption,
P2 — wrong behaviour with no signal, P3 — expensive edits, P4 — no scenario constructed.

| ID | file:line | mechanism | metric | what breaks | scenario | prio. | edit risk | how it is verified |
|---|---|---|---|---|---|---|---|---|
| CQ-01 | `routers/talk_bot.py:251-258` vs `app/blocking.py:21-27` | D, duplicate | timeout 3.0 s vs 5.0 s; no deduplication | the API-1 fix is bypassed through the bot | ntfs-3g hangs (as on 2026-09-20) → every "@бобик что сломалось" ("@бобик, what broke?") leaves a permanently hanging `os.stat` thread. The default pool on Jetson is 8 threads (4 cores + 4), and it is shared with `blocking.run_io` → after 8 questions `/storage`, `/system` and downloads wait for threads that do not exist | **P1** | low: replace with `blocking.run_io("hdd-mount", …)` | new test: 10 calls with a hanging probe → one thread (like `test_blocking_io.py`) |
| CQ-02 | `talk_bot.py:63,143-150,198,213,304,343`; `telegram_bot.py:167,410-411` | I, C, K | 3 imports and 10 calls to private names of other modules | no service layer: routers are each other's library | renaming `_read_meminfo` in `system.py` or editing `_immich_get` breaks the bot, although the router's public API did not change; the router's tests will not catch it | P3 | medium (move to `app/services/`) | import test: routers do not import `_`-names from each other |
| CQ-03 | `downloads.py:170-171` | G | `except Exception: return None` | a network failure = "size unknown", the cause is invisible | TLS/timeout on HEAD → the download is accepted without checking whether the file fits on the HDD (`choose_target`, branch `size is None`, only checks that there is any room); an overflow is caught later by the `_guard` space watchdog. ~~"a large file may land on the 229 GB SSD that holds Immich"~~ — **retracted 2026-10-02**: while preparing the fix, `choose_target` (`downloads.py:95-105`) was read — per the owner's decision of 2026-09-26 downloads **always** go to the HDD, the SSD is not used. The scenario was built from the function name, not its code | P3 (was P2) | low: behaviour unchanged, only the cause is logged | test: an exception in HEAD is distinguishable from a missing Content-Length |
| CQ-04 | `llm-gateway/app/main.py:860-868` | G | `except Exception: return False` | the reason for leaving the local model is not visible | the tunnel to the workstation breaks with TLS/DNS → questions silently go to the external cloud, `/health` shows only `false`; it repeats the "silent departure outside" class from the 23.08 checkpoint | P2 | low (log + reason field in `/health`) | test: exception → reason in `/health` |
| CQ-05 | `talk_bot.py:537-539` | G | exception text in the reply | error details in the chat | a local command fails → `🐕 Ошибка локальной команды: <текст исключения>` ("🐕 Local command error: <exception text>"): paths, addresses, sometimes URLs with parameters go into the Talk room | P2 | low | test: an exception carrying a path → no path in the reply |
| CQ-06 | `talk_bot.py:69-92,485-499,557,565-574` | E, F | `_STATE` — a module dict with keys created on the spot; `llm_failed_last` is written in 5 places, read in `remember()` | the result is passed through a field | today it is protected by the fact that there is no `await` between the write and the read (comment 567-569). Any `await` between them, or concurrent handling → the dialogue memory records someone else's outcome | P3 | medium | `test_bobik_answer.py:163` (sequential case only) |
| CQ-07 | `talk_bot.py:196-202` | G | silent `except` with no log | Immich "unavailable" with no reason | API key expired / 401 / parse error — one and the same reply, the journal is empty | P3 | low | — |
| CQ-08 | `telegram_bot.py:440-450` | G | `except Exception` + `offset` is always advanced | a failed message is lost for the user | a bug in `_dispatch` on a particular message → no reply, the user is told nothing. Advancing the offset is a deliberate protection against a "poison" message, but there is no notification | P3 | low | there is no test with an exception in `handle_update` |
| CQ-09 | 10 scripts with `ENV_FILE="${SCRIPT_DIR}/../../config/.env"` (`backup_databases.sh:15`, `storage_preflight.sh:8`, `storage_health.sh:11`, `docker_health.sh:11` and others); `install_usb_watchdog.sh:21-22`; `app/config.py:39,123,147` | D, duplicate | 6 `.env` parsers; the VPS address is hardcoded in 7 files | layout migration (`/etc/nas-layout.env`) | `layout.sh` was created precisely after a hardcoded path broke SSD recovery for 11 days. The built-in USB watchdog (`install_usb_watchdog.sh:22`) sends its alert through a hardcoded `95.163.176.103` — OPS-2 did not cover it | P2 | low per file | grep-guard: no `../../config/.env` and no literal IP outside `*.example` |
| CQ-10 | `vps_amnezia_monitor.sh:22`, `ddns_duckdns.sh:29` | duplicate, diverged | ≥9 implementations of sending to Telegram; timeouts 10/15/none | the unit hangs when Telegram is unreachable | without `--max-time` curl waits for the TCP timeout; the next run's timer does not start while the previous one hangs. Extends SH-2 (that one is about the token in argv) | P2 | low — a shared `tg_send()` (already plan 2.8) | test: every `sendMessage` call has `--max-time` |
| CQ-11 | `.github/workflows/quality-checks.yml:38,81`, `shellcheck.yml:29` | gate with `|| true` | 3 checks do not block | shellcheck warnings and a wrong NAS API compose pass CI | an edit to the NAS API compose that breaks parsing will go through green | P3 | low | a deliberate break in a branch → CI red |
| CQ-12 | `services/nas_jetson_nano-api` | H | mypy: **36 errors** in 8 files (16 — `telegram_bot.py`) | types are checked nowhere | dicts with string keys (`stringly_typed`: `downloads.py` 119, `talk_bot.py` 115, `main.py` 84) — a typo in a key is caught by nothing | P3 | — | mypy in the gate with a baseline of 36 |
| CQ-13 | `telegram_bot.py:64` vs `talk_bot.py:398-426`; `telegram_bot.py:55-61` vs `bobik_gate.py` | D | two grammars for addressing "бобик", two grammars for "что сломалось" ("what broke") | the same phrase in Talk and Telegram behaves differently | **a deliberate decision by the owner on 2026-09-19** ("пусть флудит" ("let it spam") in Telegram). The risk is a future "unification" without knowledge of the context | P4 | — | a table of phrases with the expected behaviour for both channels |
| CQ-15 | `tests/unit/test_talk_alert_selftest.py:77-96` | N | the test **returns** a list of problems instead of failing | under pytest the check is always green | right now the file is run directly, and `main()` (p. 106) turns the list into a failure. When QA-3 is fixed (collecting `tests/unit` via pytest), the check "production code has not gone back to searching for the substring `error`" will quietly stop checking | P3 | low: `assert not problems` | found by the DeepSeek executor, verified here |
| CQ-16 | 31 of 64 `*.sh` (list — §8a) | L | no references from systemd, scripts, compose or CI | the git inventory ≠ what runs | 24 scripts are mentioned only in documentation, 2 — nowhere (`setup_portainer.sh`, `vps_amnezia_monitor.sh` — the latter, according to a comment, sits in cron on the VPS, outside git). An edit to a "dead" installer is verified by nothing; an edit to a "live" script that does not actually work wastes time | P3 | — (reconcile with the device first) | — |
| CQ-17 | `services/downloads/on_complete.sh:6`, `on_stop.sh:5`; 8 scripts with `set -uo pipefail` without `-e` | G | the aria2 hooks have only `set -u` | an error in the middle of a hook does not stop it | in `config_backup.sh`, `restore_drill.sh`, `preflight.sh` the absence of `-e` is deliberate (they collect all errors). For the aria2 hooks the reason is not recorded: a failed `mv` in `on_complete.sh` will not stop the following steps | P4 | low | `test_download_hooks.py` (exists) |
| CQ-14 | `llm-gateway/app/main.py` | A | 900 loc, 7 axes of change in one file, `chat` CC 26 | expensive edits | any edit to a provider, the budget or images touches a single file with 13 broad catches | P3 | medium | the existing 47 gateway tests |

Rejected during verification: "duplicates in `NAMES_DROPPED` on a repeated call to `_name_patterns()`" —
the function is called once at import (`main.py:133`), no scenario constructed. The budget race is
an already known **GW-2**, not a new finding.

## 5. TOP-10 by "harm / cost of the edit" ratio

1. **CQ-01** — one line of a call, closes the repeat of an incident.
2. **CQ-05** — remove `{exc}` from the reply, the log already exists.
3. **CQ-10** — `--max-time` in two places (until the shared `tg_send`).
4. **CQ-04** — log + reason in `/health`.
5. **CQ-03** — distinguish "no size" from "the network failed" (lowered to P3, see the retraction in the table).
6. **CQ-11** — drop `|| true` from the NAS API compose (shellcheck — after clearing the warnings).
7. **CQ-09** — a guard on hardcoded paths and IPs, then migrate 10 scripts to `layout.sh`.
8. **CQ-07, CQ-08** — log the reason / notify the user.
9. **CQ-12** — mypy with a baseline (a ratchet, not fixing all 36).
10. **CQ-02** — the `app/services/` layer: expensive, but it removes the cause of `talk_bot.py`'s growth.

## 6. Layer map

FACT (NAS API import graph, `baseline.json`): no declared layers. In practice:

```
main.py → routers/* (11 routers)
routers/talk_bot.py → routers/{photos,storage,system,talk} (+ private names), dialog, bobik_gate
telegram_bot.py → downloads, download_links, stt, routers/talk_bot (lazy import, private function)
routers/health.py → telegram_bot.STATUS (global state, lazy import)
downloads.py, routers/storage.py, routers/system.py → blocking
everything → config (fan-in 15)
```

No cycles. There is a direction violation: the bot's domain module (`telegram_bot.py`) depends on
a router (`routers/talk_bot.py`), and the router `health.py` depends on a domain module. CONCLUSION: the routers
play the role of "services"; this is the root cause of CQ-02 and of `talk_bot.py`'s growth.

## 7. Duplicated knowledge

| knowledge | copies | diverged? | evidence |
|---|---|---|---|
| "HDD is alive" check | 2 | **yes**: 3.0 s without deduplication vs 5.0 s with deduplication | CQ-01 |
| sending to Telegram | ≥9 (6 shell `tg_send`/curl, 3 Python, + a path through the VPS) | **yes**: `--max-time` 10 / 15 / none; `parse_mode=HTML` not everywhere; cooldown only in `usb_error_monitor.sh` | CQ-10 |
| where `.env` and `VPS_HOST` live | 6 parsers + 10 hardcoded `ENV_FILE` | **yes**: `layout.sh` strips only `"`, `read_env()` in the alert scripts — `"` and `'`; `nas-offsite-backup.sh:11` defaults to `/opt/nasa` without `NAS_PREFIX`² | CQ-09 |
| the watchdog's `send_telegram` | 2 (`watchdog_job.py:27-37` = `nas_liveness.py:131-141`) | no, byte for byte; the duplicate is deliberate (different images, comment `watchdog_job.py:28`) | — |
| `read_env()` of the alert scripts | 2 (`boot-alert.py:76-84` = `talk-alert.py:51-59`) | no; deliberate | — |
| `statvfs` arithmetic | 2 (`storage.py:28-31`, `system.py:61-68`) | no | — |
| redaction of personal data and secrets | 1 (`llm-gateway/app/main.py:80-144`) | — | **no duplication**, the single exit to the outside is centralised |

² The script runs on the Vostro, and the path is overridden through `NAS_TUNNEL_ENV`, so changing the
prefix on Jetson does not break it. There is a divergence, there is no harm.

## 8. Test network

- Coverage (`raw/coverage.txt`, 5 pytest suites + 21 unit scripts, `--branch`): **68 %**.
  Worst: `talk_bot.py` 47 %, `talk-alert.py` 31 %, the routers `logs/photos/system/actions/
  storage` 47–57 %, `logging_setup.py` 30 %, NAS API `main.py` 45 %.
- `pytest tests/unit` **collects no tests at all** (`ValueError: I/O operation on closed file`) —
  the 21 scripts are run directly only; this is the known **QA-3**, and the coverage of the `bobik_gate.py`
  guard (86 %) is visible only when run directly.
- No tests for behaviour when `handle_update` raises (CQ-08), for concurrent writes of
  `llm_failed_last` (CQ-06), or for the image error texts (`test_bot_image_path.py` checks
  only the fact of refusal).
- Check density (ast over 43 `tests/**/test_*.py` files): **405 test functions, 987
  checks, 14.5 per 100 non-empty lines**. There is exactly one test with no check at all (CQ-15). 6 files in
  `tests/unit` are written in the script style with their own check functions and a counter, and give 0 —
  these are not empty tests but a different format (direct execution catches them).
- Signs of flakiness: `time.sleep` — 2 files (`test_gateway_contract.py`,
  `test_bobik_health.py`), clocks without substitution — 2 (`test_cloudru_consumption_alert.py`,
  `test_giga_balance_alert.py`), `skip`/`xfail` — 7 occurrences in 6 files. No network calls
  to the outside were found.
- **27 checks compare Russian reply text** (`assert "<phrase>" in …`). For the bot this is
  partly justified (the text is the behaviour), but editing a wording breaks tests without changing the logic.

### 8a. Shell inventory (DeepSeek executor, selectively verified)

- 64 scripts: 50 have `set -euo pipefail`, 8 lack `-e`, the aria2 hooks have only `set -u`.
  `|| true` — 69 lines in 31 files, `2>/dev/null` — 131 lines in 34 files.
- Called by: systemd — 18 (of which 3 under the **installed name** `/usr/local/sbin/nas_jetson_nano-usb-*.sh`,
  `deploy_usb_fix.sh:25-34`), from other scripts — 20, from CI — **exactly one** (`check_no_secrets.sh`).
- A search-by-filename trap: `nas_jetson_nano-daily-report.sh` is called as
  `${NAS_SBIN_PREFIX}-daily-report.sh` (`send-report-telegram.sh:13`) and is not found by name.
- **31 candidates with no caller**: 24 are mentioned only in docs (almost all `install_*`,
  `setup_*`, the `restic_*` examples, `sber/*`), 5 — in docs and tests, 2 — nowhere; another 4 are called
  only from such candidates themselves. This is a queue for reconciliation with the device, and **not a list to delete**:
  installers are run by hand according to runbooks.

### 8b. Dead Python code

**No violations found.** Verified: for every function, class and method in `services/**/*.py`
and `scripts/**/*.py` the occurrences of the name (`\bимя\b` ("\bname\b")) were counted across all `.py/.sh/.yml/.service/.ps1`
outside `docs/archive/research/kaggle/tools`. 37 `@router.*/@app.*` handlers were excluded as
framework-invoked; among the rest there is not a single name without a reference, except `do_POST`
(`services/stt/stt_server.py:98`), which is called by `http.server`. Limitation of the method: a reference
from tests only counts as usage.

## 9. What must NOT be touched

- **`bobik_gate.py`** — the security guard (ADR-0011), coverage 86 %, case table inside.
  Moving the dicts out or "unifying" them with the gateway's `_COMPLEX_PATTERNS` is not allowed: the tasks differ
  (admission to a tool vs model selection).
- **Different "бобик" grammars in Talk and Telegram** (CQ-13) — an owner's decision, not a defect.
- **Personal-data redaction in the gateway** (`main.py:80-144`) — the only point of exit to the outside;
  splitting it up to reduce the loc of `main.py` is a leak risk for the sake of a metric.
- **Deliberate duplicates** of the watchdog's `send_telegram` and `read_env()` — different images and different hosts
  (Python 3.6 on Jetson). A shared module would add coupling between images with no benefit.
- **`downloads.py`** (coverage 88 %, 63 tests on SSRF and reconciliation) — touch only via CQ-03.
- **Dated comments** (92 items) — the project deliberately keeps a chronicle next to the code
  (CLAUDE.md, rule no. 15). I do not consider this a finding.

## 10. Uncertain

- The metrics were taken by a **self-written** `scripts/quality/code_metrics.py`: lizard/radon/jscpd/vulture are not
  installed, and installing them without consent is not allowed. The cyclomatic metric is close to McCabe (the definition is in
  `baseline.json`) but not identical to radon; the shell metrics are rough (the first version of the script overestimated
  the length of a function in `preflight.sh` from 30 to 199 lines — fixed, re-verified by hand).
- The history window is 4 months — the ranking of shell-script hotspots is unreliable.
- The thread pool in CQ-01: `min(32, cpu+4)` = 8 with 4 cores — according to the Python documentation; it was not
  measured on the Jetson (the audit does not touch the live system).
- The coverage of `nas_jetson_nano-container-watchdog.py` was not measured (loaded by path).
- The "deadness" of shell scripts (CQ-16) is determined from git. On the Jetson there lives an old deployment
  (`~/nasa`, names `nasa-*`), on the VPS — cron outside git; what actually works cannot be established
  without access to the devices.
- The DeepSeek executor worked without python (in its sandbox, execution requires confirmation) and did not
  read files with `secret`/`token` in the name (a `ds_worker.toml` prohibition). Its count of `|| true` and
  `2>/dev/null` is by lines, not by occurrences; my script counts the same way, and the numbers agree
  (`jms583_health.sh`: 14 and 14).

## 11. Appendix

`raw/pytest.txt`, `raw/unit.txt`, `raw/coverage.txt`, `raw/ruff_stats.txt` (13 remarks),
`raw/mypy.txt`, `raw/mypy_nas_api_full.txt`; `baseline.json` (all metrics by file).
Subagent analyses: hotspots and duplication — the summary is in §4 and §7; every fact used was
re-verified against the code (`talk_bot.py:198,254,539`, `downloads.py:170`, `main.py:868`,
`telegram_bot.py:446-450`, `blocking.py:21-27`, `install_usb_watchdog.sh:22`,
`vps_amnezia_monitor.sh:22`, `ddns_duckdns.sh:29`).
