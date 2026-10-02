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

## 12. Addendum (2026-10-02, evening): behaviour, coupling, criticality

> Basis — a comparison with the second prompt "full architecture audit". Only the stages
> applicable to Python and shell were taken from it: resources, multithreading, timeouts along
> call chains, as well as coupling of changes by git and criticality. The behaviour passes were
> run by Opus and Sonnet subagents, read-only. The lead re-verified every fact below against the code.
> Evidence levels: **C** — CONFIRMED, **L** — LIKELY, **P** — POSSIBLE, **FP** — checked and rejected.

### 12.1. Timeouts along call chains (TO-NN)

| ID | Where | Lvl. | Prior. | Essence and scenario |
|---|---|---|---|---|
| **GW-6↑** (26.09 — low) | `llm-gateway/app/main.py:729` | C | **P1** | `OpenAI(...)` without `timeout` (the SDK default is ≈600 s). New consequence: DeepSeek is the fallback path after GigaChat 429/5xx (`main.py:821-832`). The bot waits 150 s, the gateway — up to ~750 s, and the bot gives up first. This is the class of the 24.08 incident; the subagent's TO-01 is a duplicate of GW-6 |
| **TO-02** | `config.py:110` (300 s) versus `main.py:703+633` (300+120) and `+653` (180) | C | **P1** | image generation — the gateway up to 420 s, editing — up to 600 s, the bot waits 300 s. The bot replies "не получилось" ("it did not work out"), while the gateway later spends tokens for nothing |
| TO-03 | `main.py:496+536` versus `config.py:104` | C (low probability) | P3 | OAuth 30 + chat 120 = 150, exactly the bot's timeout — there is no strict "greater than" |
| TO-05 | `scripts/sber/check_gigachat_balance.sh:15` | C | P3 | `curl` to the gateway without `--max-time`; gate 7в checks only Telegram, while the class is wider |
| TO-06 | `scripts/setup/nas-offsite-backup.sh:34-41` | C (relevance — P) | P4→P2 | `ssh` without `ServerAliveInterval`: after a break, `ssh \| tar` hangs. Whether the unit works after ADR-0007 — verify on the Vostro |
| TO-07 | `services/stt/stt_server.py:70-75` | P | P3 | recognition has no timeout of its own; the single-threaded server keeps computing after the client leaves |
| TO-08 | `container-watchdog.service` (300 s) versus `docker()` at 120 s each | P | P4 | in a mass failure the watchdog does not fit into 300 s |
| ~~TO-04~~ | backup units without `TimeoutStartSec` | **FP** | — | for `Type=oneshot` the start timeout is disabled by default. On 26.09 this was already rejected as SD-4; the subagent reopened it, the lead rejected it on the earlier analysis |

CONCLUSION: the rule "the caller waits strictly longer than the callee" is recorded only as text in CLAUDE.md.
That is why the class comes back in every new branch of the code: Ollama was fixed, but the DeepSeek
fallback and the images — were not. What is needed is an automatic check, not another point fix (PLAN, stage 16).

### 12.2. Multithreading and resources (CC-NN)

| ID | Where | Lvl. | Prior. | Essence and scenario |
|---|---|---|---|---|
| **CC-01** | `routers/download_files.py:70` | C | **P2** | the synchronous `def download` runs in the anyio pool (40 threads) with no timeout on `/dl/hdd` (ntfs-3g). While the HDD hangs, every refresh of the "файлы" ("files") page leaves a permanently hanging thread; the pool is exhausted — the same class as CQ-01 |
| **CC-02** | `downloads.py:501-509` + `tick:471-480` | C | **P2** | the guard pauses downloads one by one, but writes `paused_gids` after the loop; `tick` catches only `HTTPError`. An error in the middle of the loop — the downloads are paused, but they are not in the ledger; when space frees up, they will **never** be unpaused |
| CC-03 | `downloads.py:471-476` | C | P3 | an exception other than `HTTPError` aborts the tick before `ledger.save`: the actions in aria2 have already been performed, while the tick's messages are lost |
| CC-04 | `telegram_bot.py:257-263` versus the supervisor (300 s) | L | P3 | a voice question: 45 s + queue + 120 + 150 s — more than 300 s. The supervisor cancels the loop, the `answered` key is already written → after the restart there is no reply, and the user does not learn about it |
| CC-06 | `downloads.py:241-246`, `telegram_bot.py:192-197`, `llm-gateway/main.py:178-184` | P | P3 | writing via tmp + `os.replace`, but without `fsync`. After a hardware reset (like 17.08) the gateway, by its own fail-closed (`main.py:168-172`), answers **503 to every question** |
| CC-07 | `main.py:517,672` | C | P3 | `_gigachat_flight_lock` without a timeout: waiting requests hold threads, and after the client leaves the tokens are still spent |
| CC-08 | `main.py:957-970` + healthcheck 3 s + the watchdog | P | P3 | `/health` synchronously calls the workstation (2 s per phase) → the container is unhealthy → the watchdog does `docker restart` in the middle of a provider call |
| CC-09 | `actions.py:183-202` and others | C | P3 | after a timeout `communicate()` does not kill the process. Two presses of "бэкап сейчас" ("backup now") — two `backup_databases.sh` in parallel (extends SD-3) |
| CC-12 | `blocking.py:21-27` | C | P3 | 6 disk keys out of 8 threads of the shared pool; one more key per path — and the CQ-01 class comes back. A separate pool for disks is needed |
| CC-05, CC-10, CC-11, CC-13, CC-14 | the subagent's analysis | C/P/L | P4 | orphaned tasks on shutdown; `create_task` without a saved reference; reading logs up to 10 MB in the event loop; no `Handler.timeout` in STT; `last_id` is advanced before processing |
| FP | `_LOCAL_LAST_ERROR`, `id(self.disk_free)`, a single `Ledger`/`Lock` | FP | — | no races: assignment is atomic under the GIL, the id is stable, there is a single writer |

**Open question — verify against the device.** The NAS API compose in git mounts only
`/mnt/hdd2tb/Downloads` and `/mnt/storage/downloads`. If the device has no override of its own, then
`home_health._hdd_mount_probe` and `/v1/storage` for the disk roots always answer "не смонтирован"
("not mounted"), that is, they check nothing. This contradicts the E3 rollout of 20.09, so no conclusion
is drawn — only the question.

### 12.3. Coupling of changes by git

File pairs with ≥ 3 joint commits. Mass commits (> 12 files) are excluded; the window is 392 commits.

| pair | together | share | conclusion |
|---|---|---|---|
| `nas_jetson_nano-api/app/config.py` ↔ `docker-compose.nas_jetson_nano-api.yml` | 9 | 0.69 | **hidden coupling → CQ-18** |
| `config.py` ↔ `routers/talk_bot.py` | 9 | 0.69 | every new bot capability brings a new setting — a consequence of CQ-18 |
| `llm-gateway/app/main.py` ↔ its compose | 7 | 0.70 | the same mechanism of passing settings |
| `llm-gateway/app/main.py` ↔ `routers/talk_bot.py` | 5 | 0.42 | **an explicit contract** on the 429/422/403 codes (`main.py:287-299,1329` ↔ `talk_bot.py:487,808-822`) — normal |
| `daily-report.sh` ↔ `send-report-telegram.sh`; the three USB scripts | 4/4; 3/3 | 1.0 | in effect a single module (see also §7) |

**CQ-18 (C, P3).** The compose has no `env_file`: the variables are listed by hand. Because of this
**27 of the 66 NAS API settings cannot be set through `.env`** — the value is silently ignored there.
Among them are `talk_bot_safety_gate`, `stt_timeout`, `talk_bot_image_timeout` (and it is exactly the one
that has to be changed for TO-02), `voice_*`, `aria2_rpc_url`. This mirrors the 20.09 pitfall with
`TELEGRAM_PROXY`. Wiring in `env_file` wholesale is not a way out: something else from the shared `.env`
would leak into the container. The solution is a test: every `Settings` field is either passed in compose
or listed explicitly as "default value only".

### 12.4. Criticality × test protection

The hotspot formula (change frequency × complexity) does not see files that change rarely and are
simple, but where an error means data loss or a security hole. Criticality 3 is explicitly assigned to
26 files: backup and restore, mounting, the second copy of photos, personal-data redaction,
authorisation, SSRF/egress, the secrets gate. **Without a single test** (the file name does not occur in `tests/`):

- `scripts/backup/immich_hdd_second_copy.sh` — **the only second copy of the photos** (it closed
  P0 on 22.09). Verified by reading: `rsync -a` without `--delete` (what was deleted on the SSD stays on the HDD —
  that is safe); the checks "the source exists / the HDD exists / ≥ 20 GB free" are in place. There is no test;
- `scripts/security/check_no_secrets.sh` — the secrets gate, 8 commits, on 30.08 it broke every commit;
- `scripts/backup/setup_config_backup.sh`, `install_restic.sh`, `scripts/storage/install_mount_service.sh`, `setup_disk.sh`.

There is a test, but the behaviour is not covered: `backup_databases.sh`, `config_backup.sh`, `restore_drill.sh`,
`ssd_hotplug_recovery.sh` (8 commits, was broken for 11 days), `storage_preflight.sh`.

### 12.5. A known limitation of the ratchet

Rule R3 counts any function in a new file as new code. That is why a move without changes
(stage 11: `build_health`, `docker_ps_json` — the bodies match by AST up to the module name)
had to be accepted explicitly: `--update` with the reason in commit `fc9c91a`. The improvement — match
functions across files by body hash.
