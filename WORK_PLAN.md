# Work Plan

> Current local checkpoint: [2026-10-09](docs/plans/CHECKPOINT_2026-10-09.md).
> VPS/VPN monitor tasks 1–7 and code-audit stages 16, 17, 22 are implemented and
> locally verified. Monitor task 8 (deployment) is pending separate owner authorization.
> Vostro recovery was merged into `main` as `de6df4f`; this does not mean deployment.

## Execution update — 2026-10-06

| Item | Local status | Evidence / next action |
|---|---|---|
| VPS/VPN monitor tasks 1–7 | Complete: collection/storage, queries/rendering, report sender, installer/systemd and documentation | 101 monitor tests; [implementation plan](docs/superpowers/plans/2026-10-04-vps-vpn-monitor.md) |
| VPS/VPN monitor task 8 | **Not deployed** | Separate deployment instruction and explicit authorization for read-only VPN counter access; do not modify Amnezia |
| Vostro tunnel recovery | Merged into `main`, `de6df4f` | Local integration; deployment and live connectivity verification remain separate |
| Code audit 16 | Complete locally | Default caller budgets include sequential fallback and OAuth refreshes; per-invocation curl deadline gate |
| Code audit 17 | Complete locally | Bounded file-page preparation; single disk probe; durable partial pause/resume progress and alerts |
| Code audit 22 | Complete locally | Synthetic tests for second-copy failure barriers and tracked secret detection |
| Agent artifacts | Project-local rule/configuration applied | `.agent-work/` for worktrees/archives/tmp; existing external credential stores remain in place |

## Priorities — 2026-10-09

End-of-day state and resume sequence: [checkpoint](docs/plans/CHECKPOINT_2026-10-09.md). SEC-2/DEP-1 complete locally; DP-2/E3 prepared without deployment. GitVerse CI #263 and the Cloud.ru test are verified. Full DR resumes at home on 10 October; no isolated target is available yet. The 500-credit budget below remains an earlier proposal, not measured spending.

**Next technical block: full disaster recovery on an isolated target.** Live GitVerse
CI and restoration of four Cloud.ru configuration files are verified, but full DR
remains open. Select the target, verify independent key access and backup contents,
restore both databases and data, validate applications and restart behavior, then
measure RPO/RTO. See [audit and acceptance criteria](docs/quality/BACKUP_RESTORE_TESTS.md).
Do not provision paid VMs or restore into production volumes before target selection.
An x86 target can test data/application recovery, but does not prove Jetson ARM64 OS recovery.

1. **New Habr Part 2 article:** update the evidence queue in the plan and materials log while retaining the original spine of six evidenced cases. Candidate additions: OOM/hook/repository-hygiene incidents and fixes (first attach each to evidence), GitVerse CI preparation, verification of E3 (factual health explanation with no LLM actions), and measured agent economics. The owner writes the final article under the contest's AI-use rules.
2. **Cloud.ru grant reactivated by owner confirmation on 2026-10-09:** 4,000 bonus credits through 6 November. This is owner-confirmed, not independently verified in the cabinet; verify project/SKU eligibility in the calculator first. Official terms exclude Foundation Models, Container Apps, GPU/ML Inference, and Marketplace [Cloud.ru grant terms](https://cloud.ru/docs/billing/ug/topics/concepts__start_grant). Proposal, not spending authorization: test backup/restore of a minimal encrypted config set in Object Storage, capped at 500 credits with 3,500 reserved. A secondary option is an isolated CPU-only watchdog VM after calculator confirmation. This is not production off-site backup of family data. Automatic paid fallback and ruble top-up are not authorized.

Acceptance: NAS API **266 passed**, VPS/VPN monitor **101 passed**, **30 unit-test
scripts** in the commit hook; metrics ratchet has no violations. HTTP phase timeouts
are not strict wall-clock deadlines; FileResponse streaming after preparation remains
outside the preparation deadline. Historical entries below retain their dated evidence.

> Source — the 2026-09-26 audit (`docs/audit/2026-09-26_full_audit/REPORT.md`). Only
> **confirmed** and actionable items are listed here. Russian version — `WORK_PLAN.ru.md`.
> Assignee per rule #16: **D** — DeepSeek (mechanical work by card), **C** — Claude (lead),
> **O** — owner (sudo on the device, decisions). Complexity: S / M / L.

> Reconciled with code, tests, deployment evidence, and the 2026-09-26 checkpoint on
> **2026-10-01**. ✅ means implemented and evidenced; historical audit reports remain unchanged.

## Wave 1 — live system, now

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 1.1 | ✅ **API-1 (2026-09-27):** HDD `os.statvfs`/`exists` calls run through shared `blocking.run_io` in `asyncio.to_thread` with a timeout; timeout means `disk_down` | C | S | `test_blocking_io.py`: a hanging disk does not hold the loop, `/healthcheck` responds, downloads/storage/system covered |
| 1.2 | ✅ **OPS-2 (2026-09-30):** the Jetson daily report and Vostro offsite backup load `VPS_HOST` from root-owned `/opt/nasa/config/.env`; deployed scripts contain no literal VPS address | C | S | [live evidence](docs/plans/OPS2_VPS_CONFIG_DEPLOY_2026-09-30.md): systemd report sent Telegram message 349; offsite backup completed successfully |
| 1.3 | ✅ **OPS-1 (2026-09-30):** the host watchdog is installed and enabled; every 2 min it starts eligible `homecloud_*` containers with restart policy `always`, restarts `unhealthy` ones, honours global/per-container pause markers and the maintenance label, and alerts the owner in Telegram | C | M | [live evidence](docs/plans/OPS1_WATCHDOG_DEPLOY_2026-09-30.md): maintenance skip observed; timer recovery in 123 s; Telegram delivery accepted |
| 1.4 | **CF-2:** Docker log rotation — `log-opts` `max-size=10m`, `max-file=3` in `daemon.json` (+ default in compose) | C + O (sudo, Docker restart in a maintenance window) | S | `docker inspect` shows `max-size` |
| 1.5 | ✅ **HK-1 (2026-09-26):** `on_complete.sh` stages downloads in `.incoming`, uses `mv -n`, and retries with the next suffix on a collision | D (test) + C | S | concurrent file and directory tests preserve both downloads; [live checkpoint](docs/plans/CHECKPOINT_2026-09-26.ru.md#2-сделано-и-в-бою-проверено-по-делу-не-по-файлам) confirms two same-name MathCAD downloads |

## Wave 2 — security

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 2.1 | ✅ **GW-3 (2026-10-01):** `TOKEN_RE` recognizes Russian secret labels (пароль, ключ, код, пин, секрет), case-insensitively, with `:`, `=`, or whitespace separators | C | S | endpoint tests cover every Russian label, all separators, case, English compatibility, and whole-word boundaries |
| 2.2 | ✅ **API-2/3 (2026-09-30):** API HEAD requests use checked manual redirects; the Jetson `NAS-DL-EGRESS` barrier rejects aria2 IPv4 traffic to `10/8`, `172.16/12`, `192.168/16`, `127/8` and `169.254/16` and is refreshed every 2 min | C | M | [live evidence](docs/plans/API23_EGRESS_DEPLOY_2026-09-30.md): private redirect not followed; container→`192.168.0.1` rejected with counter hit; public control passed |
| 2.3 | ✅ **SH-1 (2026-10-01):** `cloudru_iam_token_example.sh` passes the HTTP response to fixed Python code through stdin instead of interpolating it into a heredoc | D | S | a fake response containing `'''` and a file-write expression remains JSON data and cannot execute code |
| 2.4 | ✅ **CI-1 / SEC-1 (2026-10-01):** Trivy action is pinned to the immutable SHA for `v0.36.0`; gitleaks checks full Git history using the repository config, without `--no-git` or a fail-open fallback | C | S | static policy tests enforce the SHA/history contract; CI creates and removes a synthetic secret in a temporary repository and requires gitleaks to find it in history |
| 2.5 | **DP-2 (2026-10-09): locally prepared, not deployed.** API UID 10001, no socket/CLI fallback; isolated container-list GET proxy; API restart disabled | D (specified API changes) + C (proxy/security/review) | M | NAS API 266 passed; 8 proxy/policy tests; Compose config valid; [rollout boundaries](docs/10_SECURITY_PRIVACY.md). Mounted permissions and ARM64 smoke-test required |
| 2.6 | ✅ **DP-1 / DEP-2 (2026-10-01):** all 22 external Jetson/VPS Compose image references are immutable `tag@sha256`; pins reuse measured live content, and the digest gate is blocking for both Compose trees | D (inventory) + C | S | [evidence](docs/plans/DP1_DEP2_IMAGE_PINNING_2026-10-01.md): registry manifests resolve; 7 gate tests; every Compose file renders; full gate green |
| 2.7 | ✅ **DEP-1 (2026-10-09), local:** 5 direct pins, universal hashed lock, mandatory binary/hash Docker install; unused passlib removed, python-jose retained | D (auth review) + C (lock/review) | S/M | Clean Python 3.12: 266 passed, pip check OK; wrong hash rejected; 31 ARM64 wheels verified. [Procedure](docs/21_LOGGING_API.md); not deployed to Jetson |
| 2.8 | **SH-2 / HK-2:** a shared `tg_send()` in `scripts/lib/` — token not in argv; temp file on the VPS via `mktemp` | D + C | M | grep check: no `bot${TELEGRAM_BOT_TOKEN}` in argv |
| 2.9 | ✅ **SEC-2 (2026-10-09):** tracked Markdown is scanned; exemptions apply per value and findings redact values; token-shaped examples replaced with placeholders | D (11 tests) + C (scanner/review) | S | 19 critical-shell tests pass; tracked scan clean; example/mock prose and safe same-line assignments cannot hide synthetic secrets |

## Wave 3 — reliability and quality

> The SEC-2 check on 2026-10-09 exposed a separate existing defect: download hooks
> expand DL_MV/DL_WGET paths without quoting. With project-local TEMP, targeted tests
> gave 8 passed / 3 failed. Quoting was fixed on 2026-10-09: all three MV calls and
> DL_WGET are quoted; test executable names explicitly contain spaces. Targeted
> checks: 11 pytest and 16 unit tests pass. Repeated `preflight.sh --quick` passed:
> 28 regression scripts, NAS API 251 passed, VPN monitor 101 passed;
> ShellCheck/Compose skipped in quick mode. No deployment performed.
> SEC-2 metrics pass with the new scanner module
> included and baseline unchanged.

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 3.1 | **SD-2:** remove literal paths from 14 units → `${NAS_JETSON_NANO_PROJECT_DIR}` / `/etc/nas-layout.env`; guard in the gate | D + C | M | grep-guard: no `/home/admin`, `/opt/nasa` in `systemd/*.service` |
| 3.2 | **SD-1:** `nas-offsite-backup.sh` — check that `$WORKDIR` is non-empty before `restic backup` | D | S | test "empty stream → exit 1" |
| 3.3 | **GW-1 / GW-2:** a single normalized user key; budget reservation under a lock before the call | C | M | case does not bypass the limit; N parallel requests do not exceed the limit by more than one in flight |
| 3.4 | **SD-3:** `flock` on `/mnt/hdd2tb` in every HDD walk script | D + C | S | two runs: the second is refused immediately |
| 3.5 | **QA-1/2/3:** vermin in CI; rename the `app` packages or isolate the run; `tests/unit` collected via pytest | D | S/M | CI green, a combined run without false failures |
| 3.6 | **API-4/5:** close the Telegram client; caps on state lists and the outbox | D | S | close test, eviction test |
| 3.7 | rotate `jms583-health.log`, delete `nasa-api.jsonl.*` after the migration | C + O | S | — |
| 3.8 | ✅ **BK-1 / BK-2 (2026-09-26):** backup-api validates `backup_id`, constrains the target to the backup root, rejects unsafe/dotted names and symlinks, and runs as UID 10001; the service remains intentionally undeployed | C | S | backup-api suite: 24 passed, 1 skipped; traversal, unsafe-name, symlink, and non-root checks |

## Wave 4 — articles and publication

Publication work starts with evidence collection during Waves 2–3; final drafts follow the
technical fact freeze. Publishing to an external platform remains an owner action.

| # | Item | Who | Complexity | Tests / verification |
|---|---|---|---|---|
| 4.1 | **ART-HABR-2:** prepare the updated evidence queue for the new Habr Part 2; retain the six-case spine and verify every date, metric, incident, commit, and architecture claim; prepare only redacted screenshots. The owner writes the final article under contest AI-use rules | C + O (owner writes final text and publishes) | M | [`HABR_PART2_ARTICLE_PLAN_2026-09.md`](docs/articles/HABR_PART2_ARTICLE_PLAN_2026-09.md) DoD is complete; facts trace to [`HABR_PART2_MATERIALS.md`](docs/articles/HABR_PART2_MATERIALS.md); secret/identifier scan and image-redaction checklist pass |
| 4.2 | **ART-DEV-1:** plan approved 2026-10-02 — [DEVTO_PUBLICATION_PLAN_2026-10.md](docs/articles/DEVTO_PUBLICATION_PLAN_2026-10.md); start with a fact table, then reconcile with Habr and write a separate English article: seven sections, three stories, 2,000–2,500 words; date August snapshots and do not treat Hackaday as a ready DEV.to draft | C + O (final edit and publish) | M | approved-plan DoD complete; claims have source, date and status; live state and plans distinguished; links, redacted images and preview checked; `publication_status.md` records the actual URL only after owner publication |

## Owner decisions

- 1.4: Docker restart — a maintenance window (all services for ~1 min).
