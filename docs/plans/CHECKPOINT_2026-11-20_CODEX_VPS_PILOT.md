# Checkpoint 2026-11-20: Codex CLI pilot

[Русский](CHECKPOINT_2026-11-20_CODEX_VPS_PILOT.ru.md), [previous checkpoint](CHECKPOINT_2026-11-16.md)

Limited Codex CLI pilot on the Sweden VPN host: pinned version 0.171.0, one unprivileged account, separate scoped policy, bounded session.

- G0-A earlier: synthetic S01–S10 passed, but same-UID read canary failed and resource-coverage gap was documented; OAuth was not attempted.
- Owner-approved G0-S2: five selected configuration/launcher files and hard aggregate user-slice limits; cooperative queue is SOFT, not hard single-agent admission.
- First R1-01 failed before the tool command: managed deny-read conflicted with the CLI runtime bootstrap.
- After approved single-policy R1-fix, R1-01 failed again before tool execution: bwrap tried to create a directory on a read-only filesystem.

A startup failure is not proof of working read protection. Only the pilot session was stopped; no further policy weakening. Remaining R1/R2 tests were NOT RUN. Server before/after guards and listener comparison passed; no Android E2E/throughput test.

Pilot unit and user slice inactive: no runtime socket or cgroup; persistent aggregate resource configuration retained. A fresh kernel cap readback passed while active; not a current cgroup or complete workload test.

Verdict: NO-GO for G1. No real ChatGPT/Google login, API keys/billing, second contour, IDE server, or project migration. Private evidence/configuration stay local, intentionally outside Git.

Next: only separately approved diagnosis or change; no automatic third relaxation; OAuth only after critical tests accepted and G1 separately approved.
