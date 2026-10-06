# Project checkpoint 2026-10-06 — monitor and audit

Russian version: [CHECKPOINT_2026-10-06.ru.md](CHECKPOINT_2026-10-06.ru.md).
This records local implementation and verification; no Jetson/VPS rollout was performed.

## Implemented

- VPS/VPN monitor tasks **1–7**: collection and SQLite accounting, report queries
  and HTML rendering, resumable Telegram delivery, installer/systemd and documentation.
  Source: [implementation plan](../superpowers/plans/2026-10-04-vps-vpn-monitor.md).
- Vostro tunnel recovery integrated into `main`: merge **`de6df4f`**. This is code
  integration, not evidence of deployment or restored live connectivity.
- Code-audit stages **16, 17, 22**: sequential provider/OAuth budget checks,
  per-invocation curl deadline gate, bounded file-page preparation, durable partial
  download-guard operations/alerts, synthetic second-copy and secret-scanner tests.
  Source: [audit plan](../audit/2026-10-02_code_audit/PLAN.md).
- All new agent artifacts belong inside the project: `.agent-work/worktrees/`,
  `.agent-work/archives/`, `.agent-work/tmp/`, `ds_board/`, `artifacts/`.
  Existing external credential stores and the cross-project coordination board remain in place.

## Verification

- NAS API: **234 passed**.
- VPS/VPN monitor: **101 passed**.
- Commit hook: **27 unit-test scripts**; metrics ratchet has no violations.
- Changed shell scripts pass syntax checks; `git diff --check` is clean.

Run with the project virtual environment and Git Bash available:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/nas_api
.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor
bash scripts/quality/preflight.sh --quick
git diff --check
```

## Pending and limitations

Monitor task **8 is not deployed**. Deployment requires a separate owner instruction
and explicit permission for strictly read-only VPN counter collection. Do not modify
Amnezia, firewall, SSH/network settings or neighbouring services.

HTTP phase/inactivity timeouts do not enforce a strict wall-clock deadline;
gateway lock waits remain unbounded. File-page preparation returns 503 after a disk
probe timeout and reuses at most one in-flight probe, but subsequent FileResponse
opening/streaming is outside that preparation deadline.

Curl checking is a heuristic for literal calls, continuations, substitutions and
quoted SSH commands. Computed command names/options hidden in arrays need manual review.
Telegram report delivery can repeat a part if its acknowledgement is lost; it does
not guarantee exactly-once delivery.

Rollback before rollout: reverse the relevant local patch/commit. A future monitor
rollback disables only the monitor and preserves its database/configuration.

## Next safe step

After publishing this checkpoint to both Git mirrors, the next local audit block
is stages 19-21: a dedicated disk pool, fsync for state, and process termination/
concurrent-backup protection. These stages were not implemented in this iteration.
Keep deployment separate; follow task 8 only after its required authorization.
Remaining audit stages and September-plan items remain open without their own evidence.
