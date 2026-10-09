# Checkpoint — 2026-10-09

[Русский](CHECKPOINT_2026-10-09.ru.md) · [Work plan](../../WORK_PLAN.md)

## Verified state

- GitVerse CI #263 passed for `83590f7`, 11:08:18–11:12:08 UTC (3m50s). It does not validate the new checkpoint commit.
- Cloud.ru encrypted restore: four real configuration files, 9,710 bytes, hashes 4/4 and modes 4/4; restic check passed. No databases, `.env` or family data uploaded; restored only to a test directory.
- SEC-2 scans tracked Markdown with narrow value-based exemptions and redacted diagnostics. It does not audit all Git history.
- Download hooks now quote DL_MV and DL_WGET; paths containing spaces pass tests.
- DP-2: API UID/GID 10001 without docker.sock; isolated status proxy permits only container listing. Prepared locally, not deployed; production directory permissions and image builds remain unverified.
- DEP-1: five direct pins, universal SHA256 lock for 32 packages; each target installs 31. Clean Python 3.12.15 hash-only binary install and pip check passed. All 31 Linux ARM64 wheels downloaded; no ARM64 execution yet. A deliberately invalid hash was rejected offline.
- E3 distinguishes missing evidence from faults; unavailable Docker cannot yield a green status. Live deployed behavior remains unverified.

Owner confirmed 4,000 grant credits through 6 November and a 90 RUB balance. Cabinet access, exact SKU eligibility and actual grant deductions remain unverified. Test S3 repositories are retained. No automatic top-ups or new paid VMs authorized.

## Validation

`bash scripts/quality/preflight.sh --quick`: 30 unit-test scripts; NAS API 266 passed; VPN monitor 101; gateway 56; watchdog 44; backup API 24 passed / 1 skipped; STT 17. Metrics ratchet passed. Quick mode skips ShellCheck and Compose; the changed Compose was separately validated with `docker compose --env-file config/.env.example -f docker/compose/docker-compose.nas_jetson_nano-api.yml config --quiet`. The clean dependency environment also passed all 266 API tests.

Changed areas: SEC-2 scanner/tests, download hooks, API/Compose and new docker-status proxy, dependency lock/tests, security/restore/API documentation, work plans and article evidence. Ignored evidence is in `.agent-work/tmp/`: `dep1-REPORT.json`, `dep1-preflight-20261009.log`, `cloudru-real-config-20261009-REPORT.json`, `gitverse-live.log`.

## Resume

1. Verify git status, main SHA and CI triggered by this checkpoint commit.
2. At home on 10 October, select an isolated full-DR target (none is available yet). Verify independent key access and backup completeness, restore both databases and data, validate applications/restarts, measure RPO/RTO. Never restore into production volumes. Follow [acceptance criteria](../quality/BACKUP_RESTORE_TESTS.md).
3. Before authorized DP-2 deployment, verify bind-mounted log/state permissions for UID 10001, build images and test API/proxy on the target architecture. Do not restore direct socket access or sudo to work around failures.
4. Verify live E3 after authorized deployment. VPN monitor task 8 also remains undeployed; do not modify Amnezia.
5. Use the article plan and evidence journal; do not claim full DR or grant deductions verified.

## Ownership, risk and rollback

DeepSeek handled own-code tests/mechanical fixes, auth review and drafts from sanitized facts; the lead handled architecture, host access, diff review and independent validation. Today's seven-attempt series cost **$0.315716**, weighted cache 91.23%, automatic retries 0; one FAILED and one REWORK. This is not total project cost.

No production deployment occurred. Future DP-2 risks include directory permissions and deliberately prohibited Docker operations. A future deployment rollback requires separate authorization and the previous verified image/Compose. Local rollback can use git revert, preserving linear history. Do not automatically delete test S3 repositories or ignored artifacts.
