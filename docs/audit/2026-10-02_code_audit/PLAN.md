# Code audit plan 2026-10-02

> Current execution: [checkpoint 2026-10-06](../../plans/CHECKPOINT_2026-10-06.md).
> Stages **16, 17, 22 are implemented and verified locally**; no deployment.

## Acceptance update — 2026-10-06

| Stage | Implemented | Verification |
|---|---|---|
| 16 | Default network-budget table includes GigaChat→DeepSeek fallback, local probe and OAuth refresh per image step. Every literal curl invocation under `scripts` requires its own nonzero deadline, including SSH commands and substitutions | `test_timeout_hierarchy.py`: provider chains, multiline/non-Telegram curl, separate calls, quoted SSH, prose and zero deadlines |
| 17 | Async signed file-page preparation through one bounded disk probe; 503 on timeout; partial guard pause/resume progress and initial alerts persist even after RPC failure; cancelled/missing GIDs do not block recovery | `test_download_blocking.py`, `test_download_guard_failures.py`; NAS API **234 passed** |
| 22 | Second-copy failure barriers and secret scanner tested with synthetic directories, commands and a temporary Git repository | `test_critical_shell_scripts.py`: missing source/HDD, low space, non-destructive dry-run, synthetic tracked secret, allowed file reference and excluded untracked content |

Full acceptance also includes **101 monitor tests** and **27 unit-test scripts** in
the commit hook; metrics ratchet has no violations. HTTP phase timeouts are not
strict wall-clock deadlines, and gateway locks remain unbounded. FileResponse
streaming after preparation is outside that preparation timeout. Curl checking is
a documented heuristic; computed commands/options hidden in arrays need manual review.

Historical stage descriptions and earlier acceptance reports below are preserved.
Deployment remains a separate owner-authorized step; monitor task 8 was not performed.

> Basis — `REPORT.ru.md` (findings CQ-NN). Russian version — PLAN.ru.md. Each stage is a
> separate PR ≤ ~400 lines and ≤ 10 files; before the edit — a characterising test, green on
> the current code and failing under a deliberate break. Rollback of each stage — `git revert <commit>`;
> rollout to the Jetson — only according to the deployment runbook and on the owner's word (CLAUDE.md, rule no. 14).
> Executors per rule no. 16: **S** — a Sonnet subagent (implementation), **D** — DeepSeek (tests,
> mechanics), **L** — the lead (design, acceptance, rollout).
>
> Intersections with `WORK_PLAN.md`: stage 3 is part of item 2.8 (SH-2), stage 7 is a step towards 3.1
> (SD-2), stage 9 depends on 3.5 (QA-3). There is no need to duplicate the items: when the plan is accepted,
> the stages are entered into `WORK_PLAN` as sub-items.

## Order: from mechanics to structure

| # | stage | findings | files | metric before → after | characterising test before the edit | who | estimate |
|---|---|---|---|---|---|---|---|
| 1 | The bot's HDD check via `blocking.run_io` | CQ-01 | `routers/talk_bot.py`, test | copies of the HDD check 2 → 1; threads with a hanging disk N → 1 | 10 calls to `_check_hdd_mount` with a hanging probe → `blocking.busy()` one thread, replies "не отвечает" ("not responding") | S + D (test) | ~30 lines, 1 session |
| 2 | Exception texts do not go to the chat; reasons go to the log | CQ-05, CQ-07, CQ-04 | `talk_bot.py:198,539`, `llm-gateway/main.py:860-868` (+ a reason field in `/health`) | silent `except` in hotspots −2; exception-text leaks 1 → 0 | an exception with a path → no path in the reply; Immich 401 → a log entry; local model TLS error → reason in `/health` | S + D | ~60 lines, 1 session |
| 3 | `--max-time` in all Telegram sends from shell | CQ-10 | `vps_amnezia_monitor.sh`, `ddns_duckdns.sh` + a guard in `preflight.sh` | `sendMessage` calls without a timeout 2 → 0 | guard test: grep finds a `sendMessage` without `--max-time` → fail | D | ~20 lines; then a shared `tg_send()` per WORK_PLAN 2.8 |
| 4 | `_head_size`: "the network failed" ≠ "size unknown" | CQ-03 | `downloads.py:152-171`, `add_link` | broad `except` in `downloads.py` −1 | TLS/timeout in HEAD → a distinguishable outcome; no Content-Length → `None` as now | S + D | ~50 lines, 1 session |
| 5 | A test returning a list → `assert` | CQ-15 | `tests/unit/test_talk_alert_selftest.py` | tests with no checks 1 → 0 | a deliberate return of the `error` search in production code → the test is red both under pytest and directly | D | ~5 lines |
| 6 | Drop `|| true` from the NAS API compose check in CI | CQ-11 | `.github/workflows/quality-checks.yml:81` | non-blocking gates 3 → 2 | a branch with a deliberately broken compose → CI red | L | 1 line; shellcheck `|| true` — after clearing the warnings |
| 7 | A guard on hardcoded `../../config/.env` and the VPS IP + migrating 10 scripts to `layout.sh` | CQ-09 | 10 scripts, `install_usb_watchdog.sh`, a guard in `preflight.sh` | files with a hardcoded `ENV_FILE` 10 → 0; literal IPs outside `*.example` 7 → 0 (VPS installers — by decision) | a guard test + for each script a run with a substituted `/etc/nas-layout.env` | D (mechanics) + L | 2 PRs of ~5 files each |
| 8 | Metrics ratchet | all | `scripts/quality/code_metrics.py` (already written), `preflight.sh`, CI, `baseline.json` | — | a deliberate regression (`talk_bot.py` +1 function with CC 20) → the gate is red | L + D | see below |
| 9 | mypy with a baseline of 36 | CQ-12 | `preflight.sh`, CI | new mypy errors block | add a deliberate type error → red | D | after QA-3/QA-2 |
| 10 | Reconcile the 31 "callerless" shell scripts with the Jetson and the VPS | CQ-16 | documentation only (`docs/REPOSITORY_STRUCTURE.md` or the runbooks section) | unknown scripts 31 → 0 (each: works / installer / archive) | — (reading from the device, no edits) | L (live access — lead only) | 1 session, the Jetson is needed |

## Structural stages (after 1–8)

| # | stage | findings | approach | characterising test | estimate |
|---|---|---|---|---|---|
| 11 | The `app/services/` layer in the NAS API | CQ-02 | move `_read_meminfo/_read_loadavg/_read_uptime_seconds/_read_thermal/_docker_ps_json` (system), `_immich_get` (photos), `_ocs_post/_admin_auth/_OCS_HEADERS` (talk), `_build_health` into public functions `app/services/{system,immich,talk_ocs,health}.py`; routers and bots call the services. **The logic does not change**, only the location and the names | architecture test: no module imports a `_`-name from another module, and no non-router module imports `app.routers.*`; plus the current 212 NAS API tests | 2–3 PRs of ~150 lines each |
| 12 | Bot texts separate from decisions | CQ-14 (part), C in `talk_bot.py`, `telegram_bot.py`, `downloads.py` | reply texts → `app/texts.py` (pure functions); `_handle_image_request`, `_dispatch`, `_route_paused` remain the decision machine | pin the exact texts of 429/403/422/success for images (currently the test checks only the fact of refusal) | 2 PRs |
| 13 | Bot state as a type | CQ-06 and E in `telegram_bot.py` | `_STATE` → a dataclass with all keys; `llm_failed_last` → the return value of `ask()`, not a field | test: two concurrent `ask` calls (one with a gateway failure) → the memory records only the successful one | 1–2 PRs, **REQUIRES A HUMAN DECISION**: the format of the bot's `/status` changes if the keys are renamed |
| 14 | Split up `llm-gateway/app/main.py` | CQ-14 | along the axes: `providers/{giga,deepseek,ollama,cloudru}.py`, `budget.py` (together with GW-1/GW-2 from WORK_PLAN 3.3), `images.py`; **do not split the personal-data redaction** | the current 47 gateway tests + a test: each provider receives already-redacted text | 3 PRs; take only together with GW-1/2 |

## Execution status (2026-10-02, branch `quality/code-audit-2026-10`)

Done and accepted by the lead (tests in place, `preflight` with the ratchet passed):
stage **1** — `8a02001`, **2** — `aaa6b07`, **3** — `9ee6c5a`, **4** — `6d0c8f7`, **5** — `d88dedb`,
**6** — `c3c6623`, **8** — `75e5c21`…`210d0d4` and `b4691ba`, **11** — `1c7eb98`, `51912d4`, `f3d951c`
(private cross-module calls 13 → 0) and `fc9c91a`.
Not started: 7, 9, 10, 12, 13, 14. No rollout to the Jetson was done.

## Addendum: stages for the findings of report §12

| # | stage | findings | approach | characterising test before the edit | prior. |
|---|---|---|---|---|---|
| 15 | Gateway provider timeouts below the bot's timeout | GW-6↑, TO-02, TO-03 | `OpenAI(..., timeout=DEEPSEEK_TIMEOUT)` (90 s); images — either `TALK_BOT_IMAGE_TIMEOUT` ≥ the sum of the gateway's steps (450/650 s), or a shared request deadline in the gateway; GigaChat OAuth — 15 s. **CQ-18 first**: `talk_bot_image_timeout` cannot currently be set through `.env` | a gateway with a slow DeepSeek stub → the reply arrives before the bot's timeout | **P1** |
| 16 | A timeout-hierarchy check | the TO class | test: a table "caller → all callee chains (with sequential steps and fallback paths)", the inequality `caller > sum(callee)`; generalise gate 7в from Telegram to any `curl` in `scripts/**/*.sh` (TO-05) | the test is red on the current code (TO-02) | P1 |
| 17 | The "файлы" ("files") page and the download guard | CC-01, CC-02, CC-03 | `download` → `async def` + `blocking.run_io` with a timeout and a 503; in `_guard`, append to `paused_gids` after each pause, catch `RuntimeError` on every download; in `tick` — `except Exception` with a log and **always** `ledger.save` | a hanging `stat` → a 503 and one thread; an error on the third pause → all three in `paused_gids` | P2 |
| 18 | Explicit settings passing | CQ-18 | test: every `Settings` field of the NAS API and the gateway is either passed in compose or listed explicitly as "default only" with a reason; add the needed ones to compose (`TALK_BOT_IMAGE_TIMEOUT`, `STT_TIMEOUT`, …) | the test is red: 27 fields | P3 |
| 19 | A separate pool for disks | CC-12 | `ThreadPoolExecutor(4)` in `blocking.run_io` | N keys hang → DNS and `to_thread` stay alive | P3 |
| 20 | `fsync` for state files | CC-06 | a shared `atomic_write()` (flush + fsync of the file and the directory) for the download ledger, the bot state and the gateway accounting; on a corrupt file the gateway restores from `.bak` instead of answering 503 to everything | a corrupt accounting file → the gateway answers | P3 |
| 21 | Processes and the backup button | CC-09 | `proc.kill(); await proc.wait()` on timeout; an `asyncio.Lock` "a backup is already running" → 409 | two requests in a row → one process | P3 |
| 22 | Tests for critical scripts that have none | §12.4 | `immich_hdd_second_copy.sh` (no source / no HDD / too little space → code ≠ 0 and nothing is copied; no `--delete`), `check_no_secrets.sh` (a secret is caught, a `*_FILE` path is not) | — these are the tests | P2 |
| 23 | Verification against the device (read-only) | the §12.2 question, TO-06 | whether the disk roots are mounted into the API container; whether the off-site unit on the Vostro is alive after ADR-0007 | — | — |
| 24 | The ratchet: a move ≠ new code; coverage of changed files | §12.5, the v3 prompt | matching functions by body hash; the coverage of a changed file not below baseline, and for critical ones — a test for any edit | a deliberate move → not a violation | P4 |

Order: **18 → 15 → 16** (without 18, TO-02 cannot be fixed by a setting), then 17 and 22, then 19–21.

Stage **18 is implemented locally**: Compose now forwards 15 NAS API settings
and the gateway's `GIGACHAT_MODEL_COMPLEX`, preserving defaults. Of 66 NAS API
fields, 54 are in Compose and 12 remain fixed with reasons in
`tests/unit/test_settings_compose.py`. The test inspects AST without importing
services and catches missing settings, stale exemptions and wrong source variables.
Before the fix it failed on 15 API settings and one gateway setting.
Examples are in `config/.env.example`; the real `.env` was not changed.
Stage 18 preserved the 300 s image timeout; stage 15 below changes it to 650 s.

Verification: `.venv/Scripts/python.exe tests/unit/test_settings_compose.py` — 5 passed;
NAS API — 221, gateway — 52; full `preflight.sh` using `.venv` and Git Bash — exit 0,
no metrics violations (local ShellCheck unavailable; Compose skipped in the gate).
Both Compose files were separately checked with `config --format json` and a synthetic
env file: 650/125 s overrides and model passed through; safety defaults remain true.
Future deployment risk: previously ignored `.env` values now take effect; review them
without exposing secrets before deployment. Rollback: reverse the stage 18 patch in
Compose, example and test; no runtime rollback needed because no device was changed.

Stages 15 and 17 change behaviour for the family (waiting times, a 503 reply instead of a hang) — after
the rollout, an announcement to the group (rule no. 18).

### Stage 15 — local implementation

- DeepSeek: `DEEPSEEK_TIMEOUT=90`, forwarded through Compose and the example;
  `max_retries=0` replaces two SDK retries; the context manager closes the client.
- GigaChat OAuth: 15 s. Bot text default 240 s > 15+120+90=225.
- Image default 650 s > upload180 + generation300 + download120 + 3×OAuth15=645.
  The conservative case refreshes at every step; the usual case refreshes once.
- Telegram supervision now refreshes heartbeat before each batch update;
  poll allowance includes getFile45 + download45 + voice queue120 + STT120 +
  sendChatAction45 + LLM240 + sendMessage45 + margin30 = 690 s with defaults.
  Downloads retain 300 s. This is a necessary dependency of longer LLM waits.
- Before the fix: 3 new gateway and 3 poll tests failed. After: 4 gateway tests
  (including synthetic image/edit with three refreshes) and 3 poll tests pass offline.
- DeepSeek received only a read-only public-code inventory in an isolated worktree:
  `nas-stage15-timeout-inventory-20261002`, independently reviewed and accepted (`DONE`),
  three runs, approximately $0.103. Design and integration stayed with the lead;
  a separate reviewer found the missing `sendChatAction` operation.

Files: `services/llm-gateway/app/main.py`, `services/nas_jetson_nano-api/app/{config,telegram_bot}.py`,
both Compose files (`llm-gateway`, `nas_jetson_nano-api`), `config/.env.example`,
`tests/llm_gateway/test_provider_timeouts.py`, `tests/nas_api/test_poll_timeout_budget.py`,
`CHANGELOG.md`, PLAN/CHECKPOINT RU/EN pairs. Verification commands (separate processes):
`.venv/Scripts/python.exe -m pytest -q tests/llm_gateway` and
`.venv/Scripts/python.exe -m pytest -q tests/nas_api`; full gate:
`bash scripts/quality/preflight.sh` with `.venv/Scripts` and Git Bash on PATH.
Result: gateway **56 passed**, API **224 passed**, watchdog 44, backup 24+1 skip,
STT 17; full preflight exit 0, no metrics violations, clean `git diff --check`.
Two gate warnings: ShellCheck absent and Compose skipped; both Compose files
were separately validated with `config --format json` and an isolated synthetic
env file (defaults 240/650/90 and overrides 245/655/12).
One STT test initially reported a connection error; isolated and full reruns passed.

Limits/risks: HTTPX/SDK timeouts bound network phases/inactivity, not total request
duration. `_gigachat_flight_lock`/`_token_lock` waits remain unbounded (CC-07);
there is no global deadline or cancellation after the client stops waiting.
DeepSeek/OAuth fail earlier; the bot waits longer. Before a future rollout, review
old explicit 150/300 values in `.env` because they override the new defaults;
do not expose secret values. Privacy, mounts, networks and real `.env` files are unchanged.
Rollback: reverse only stage 15, preserving stage 18; no runtime rollback needed.
Next after the 2026-10-06 acceptance: review/publish locally verified stages 16/17/22;
deployment separately, then an announcement to the family after rollout.

## The ratchet (stage 8) — how to build it in, not build it alongside

- The gates already exist: `.githooks/pre-commit` → `scripts/quality/preflight.sh`, CI `quality-checks.yml`.
  The new check is a `code_metrics.py --check docs/audit/2026-10-02_code_audit/baseline.json` mode
  inside `preflight.sh`, not a separate workflow.
- Check rules: (1) the number of files in `fail` does not grow; (2) a modified file that already violates
  a threshold does not worsen its own `cc_max`, `func_loc_max`, `broad_catch+silent_catch`; (3) a new function —
  CC ≤ 10, length ≤ 40; (4) an exception — an explicit `--allow-regression <file> --reason "…"`,
  visible in the history.
- Self-check: a branch with a deliberate violation → `preflight.sh` and CI are red; without that the
  stage is not closed (rule no. 14: "a check without a defect history is ballast").
- Safeguards in `CONTRIBUTING.md`: a new bot command — a new function in `app/services/`,
  not a branch in `_dispatch`; texts — in `app/texts.py`; a new copy of "where `.env` lives" is forbidden,
  only `layout.sh`/`nas_layout.py`.

## Do not do

Rewrite `bobik_gate.py`, unify the "бобик" grammars of Talk/Telegram, split the personal-data
redaction, move the "deliberate" duplicates of the watchdog and `read_env()` into a shared module,
clean out the dated comments (the rationale is in `REPORT.ru.md` §9).

## Question for the owner

Which stages to take? The lead's proposal: **1–6 in one pass** (mechanical, each with a test,
~170 lines in total, closing P1 and all P2 except CQ-09), then **8** (the ratchet, so that the
structural stages are not rolled back), then **11**. Stages 7 and 10 require access to the Jetson;
13 — decisions about the `/status` format.
