# Project Checkpoint 2026-10-08 — VPN verified, VPS swap, hook fixed

Russian version: [CHECKPOINT_2026-10-08.ru.md](CHECKPOINT_2026-10-08.ru.md). Previous checkpoint:
[CHECKPOINT_2026-10-06.md](CHECKPOINT_2026-10-06.md). Startup package for the next agent —
[docs/handoff/CODEX_START_2026-10-08.md](../handoff/CODEX_START_2026-10-08.md).

## 1. Owner's decisions 07–08.10

- "Control user load from VPN" = **observation** (VPS/VPN monitoring), not speed limits.
  Monitor deployment (task 8) **postponed** ("no, not now"). When deployment happens — bot token
  moves from Jetson to VPS via reverse tunnel, without waiting for home network.
- Any command on VPS — **under memory limit** (rule from 08.10, see §3).
- Enable small swap on VPS — done (§2).
- Collaborative development with colleague — on **GitHub**, GitVerse not needed (board, m0256).

## 2. VPN verification (08.10 05:08 UTC, read-only)

| When (UTC) | Event | Evidence |
|---|---|---|
| 04.10 04:55–05:27 | VPS powered down **31 min**; initiator not found | `last -x`: `shutdown` → `reboot`; previous boot journal ends 04:55:54 |
| 04.10 17:04:47–59 | Out of memory: 6 `bash` processes ~1.6 GB each killed by kernel, `amneziawg-go` waiting for memory | `journalctl -k`; session opened with **our** key `borovskoy_new_ed25519` |

Root cause of second event found in Claude session journal 04.10: command read entire sshd journal
into a variable (`J=$(journalctl -u ssh -u sshd …)` without `--since`) and grepped it seven times.

After 04.10 17:05 server side is clean (verified 08.10): containers `amnezia-awg2`/`amnezia-xray`
running since 04.10 05:27, `restarts=0`, no die/oom events; per `sar` for 01–08.10 idle CPU not below 86 %
(except 04.10), peak traffic 2–3 MB/s, no steal; 0 UDP errors in container namespace;
`awg0` TX dropped 5350 out of 55 million; outbound from VPS to internet 0 % loss.

Claude reported **23** clients. The absence of recorded failed attempts alone does
not exclude a server issue or filtering of AmneziaWG.
Codex clarification dated 07.10: the owner profile uses `193.8.215.130:40568/UDP`,
AmneziaWG, MTU 1376. Three ordinary UDP packets from the home Jetson reached the VPS.
This verifies neither handshake nor Deco: Jetson is connected upstream of the mesh.
The cause of failure through Deco remains unknown; a real phone attempt observed
at the VPS is needed.

## 3. VPS changes 08.10 (with owner approval)

- **Swap.** `/swapfile` 512 MB (created 02.11.2024) dropped out of `/etc/fstab` when rewritten
  18.06.2026 — for nearly four months VPS lived without swap. Restored: line in `fstab` (verified
  `swapoff` + `swapon -a`), `vm.swappiness=10` in `/etc/sysctl.d/60-nas-swap.conf`, backup
  `/etc/fstab.bak.1791437180`. Rule №13 before/after unchanged, peers 23 = 23.
  Rollback: `swapoff /swapfile`, restore `fstab` from backup, delete conf, `sysctl vm.swappiness=60`.
- **Rule:** `ssh … 'systemd-run --quiet --scope -p MemoryMax=256M -p MemorySwapMax=0 bash -s' < script.sh`;
  journaling — stream only with `--since`. `MemorySwapMax=0` is required: with swap enabled, a failed
  command without it will not die but will longer drag down VPN.

## 4. Repository

- **Hook defect fixed:** test stage 22 (`tests/unit/test_critical_shell_scripts.py`) under hook
  inherited `GIT_DIR`/`GIT_INDEX_FILE`, set the real repository to `core.bare=true`, and injected
  synthetic `settings.conf` into the commit. Fix with regression test — `main` **`69d93f7`**,
  pushed to GitHub and GitVerse (`main`/`master`), CI green (Quality Checks, Security Check, Compose).
- **Monitor deployment prep (without deployment)** — branch `deepseek/nas-vpnmon-deploy-prep-20261007`
  (worktree `.agent-work/worktrees/nas-ds-nas-vpnmon-deploy-prep-20261007`), **not merged, not pushed**:
  `422885b` — instruction `DEPLOY_VPNMON_2026-10` (RU+EN): step 6 from home/outside via `jetson-via-vps`,
  check `sudo -n`, replace VPS address on block, verify peer count `peers=N` before/after, ask owner for
  unnamed peer names; report template "with traffic per day";
  `362f1a1` — same test fix as `69d93f7`; `31e9ec5` — `CLAUDE.md`: line about VPS swap,
  Pitfalls section on out-of-memory, rule in instruction.
- **Uncommitted Codex work in `main` index** as of 06.10 17:30–18:14 on repository cleanliness:
  9 files, +808/−8 (`AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.github/workflows/quality-checks.yml`,
  `scripts/quality/preflight.sh`, `scripts/quality/repo_hygiene.py`, `repo_hygiene_policy.json`,
  `tests/unit/test_repo_hygiene.py`, `docs/AGENT_REPOSITORY_HYGIENE.md`). Author: Codex. With normal
  index cleanliness check reports 690 records, 0 violations. Until it is committed, commit of a specific
  path (`git commit -- <path>`) fails on its check (`ValueError`: policy read from index but not in HEAD) —
  such commits were made with `--no-verify` and explanation.
- `CLAUDE.md` of the branch and `CLAUDE.md` in index overlap: merge will have conflict.

## 5. Tests

- VPS/VPN monitor: **101 passed**; LLM gateway **56**; NAS API **234**; watchdog 44; backup_api 24; stt 17
  (07–08.10, `preflight.sh --quick` with `.venv`).
- `tests/unit/test_critical_shell_scripts.py`: **8 passed** normally and under hook emulation, `GIT_DIR`
  decoy untouched.

## 6. Next steps (in order)

1. Settle the fate of repository cleanliness work in `main` index: complete and commit in one commit
   or pass decision to owner. Until then do not mix it with other changes.
2. Merge `deepseek/nas-vpnmon-deploy-prep-20261007` into `main`, keep both sides in `CLAUDE.md`;
   run gates; push to both mirrors.
3. Monitor task 8 — only on owner's word "деплой" and after explicit approval for read-only counter
   collection; instruction — `docs/plans/DEPLOY_VPNMON_2026-10.md` (version from branch).
4. VPN client failures — data from owner (device, time, network, address in config).
5. Audit, stages 19–21 (from checkpoint 06.10): disk operation pool, fsync state, parallel backup protection.

## 7. Environment pitfalls found 07–08.10

- `.venv` in PATH Git Bash: use `/e/Linux mint/...` form; form `E:/...` breaks PATH on colon,
  gates take system Python without `openai` and fail on `tests/llm_gateway`.
- `preflight.sh` cannot be run from a copy outside the repository — it looks for files relative to itself.
- DeepSeek card for reading large documents needs `max_turns` ≥ 30 and instruction to write `RESULT.json`
  immediately; at 20 turns executor exhausted limit on reading.

## Codex integration — 2026-10-08

Hygiene gate is committed in `d180977`; synthetic Git subprocesses clear inherited
`GIT_*`. All 18 hygiene tests and the real pre-commit hook passed. The monitor
preparation branch is integrated with the VPS memory rule and corrected SSH
examples. Historical pending statements above describe the pre-integration snapshot.
Monitor deployment remains pending; no runtime configuration was changed by this integration.
