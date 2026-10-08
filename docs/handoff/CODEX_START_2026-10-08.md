# Codex start in NAS_Jetson_Nano — handoff from 2026-10-08

Russian version: [CODEX_START_2026-10-08.ru.md](CODEX_START_2026-10-08.ru.md). Document replaces outdated
`docs/prompts/CODEX_BOOTSTRAP_PROMPT.md` (30.08) for current startup. No secrets here — only paths.

## 1. Read before first action (in order)

1. `AGENTS.md` — shared agent rules (version from working copy, with §9 "Artifacts" and §10 "Cleanliness").
2. [`docs/plans/CHECKPOINT_2026-10-08.md`](../plans/CHECKPOINT_2026-10-08.md) — where the project is now.
3. `CLAUDE.md` — operational state, component table, Pitfalls and Hard Rules №1–18.
   Written for Claude but **project knowledge canon** for Codex too: recorded defects and prohibitions.
4. `docs/32_QUALITY_GATE.md` — gates; `docs/AGENT_REPOSITORY_HYGIENE.md` — cleanliness (in index).
5. When delegating mechanics — `docs/handoff/DEEPSEEK_WORKER.md` (DeepSeek executor, `ds-worker`).

Reference, read-only: Claude's project memory lives outside the repository —
`C:\Users\Alexey\.claude\projects\e--Linux-mint-virtual-VM-shared-NAS-Jetson-Nano\memory\` (`MEMORY.md` — index).

## 2. Hard rules that must never be broken

- **Language with owner — Russian.**
- **VPN on VPS (rule №13):** do not touch or restart `amnezia-*` containers; before and after any work
  on VPS — containers not restarted, only 22/443/40568 udp outbound, peer count not decreased.
- **Any command on VPS — under memory limit** (owner, 08.10):
  `ssh … root@VPS 'systemd-run --quiet --scope -p MemoryMax=256M -p MemorySwapMax=0 bash -s' < script.sh`.
  Logs — stream only with `--since`, never into shell variable: 04.10 that is how VPN was choked.
- **Deployment — only on owner's word "деплой".** VPS/VPN monitor (task 8) also requires separate
  explicit approval for read-only counter collection.
- Do not print or commit secrets; name file and line, never value. Before push —
  `bash scripts/security/check_no_secrets.sh`.
- Destructive (`rm -rf`, format, `DROP`, delete others' files and worktree) — only with
  owner approval. `/mnt/hdd2tb` (NTFS, 1.4 TB archive) do not format or traverse in parallel.
- Live Jetson runs on **old layout**: repository `~/nasa`, containers `homecloud_*`, units
  `nasa-*`; `git pull` on device — only by deployment instruction.
- Documentation — in pairs `X.md` (EN) + `X.ru.md` (RU); new document without pair is not ready (rule №15).

## 3. Workstation environment

| What | Where / how |
|---|---|
| Repository | `E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano`, branch `main`; remotes `origin` (GitHub) and `gitverse` (`NAS_HOME`) |
| Python for tests | `.venv\Scripts\python.exe`; in Git Bash — `export PATH="/e/Linux mint/virtual_VM/shared/NAS_Jetson_Nano/.venv/Scripts:$PATH"` (form `E:/` breaks PATH) |
| Gates | `bash scripts/quality/preflight.sh --quick`; hook `.githooks/pre-commit` enabled (`core.hooksPath`) |
| Publication | `git push origin main`; GitVerse — `bash scripts/sber/gitverse_mirror_push.sh` (pushes `main` and `master`) |
| GitHub CLI | `C:\tools\gh\bin\gh.exe`, logged in as `AlexeyBorovskoy` via keyring. Token nearly admin — do not share |
| DeepSeek | `ds-worker new/run/status/review`, config `ds_worker.toml`, history `ds_board/` (outside git) |
| Project board | `python E:\agent_coordination\coord.py list --agent nas --open`; project tag — `nas` |
| Artifacts | only within project: `.agent-work/{worktrees,archives,tmp}/`, `artifacts/` (AGENTS.md §9) |

## 4. Access (paths, no values)

| Where | How |
|---|---|
| VPS `95.163.176.103` | `ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103` or alias `vps-nas` |
| VPS, if address blocked | `-o HostKeyAlias=95.163.176.103 root@193.8.215.130` or `vps-nas-alt` (block alternates between addresses) |
| Jetson from home | `ssh admin@192.168.0.50` (rule №17) |
| Jetson from outside | alias `jetson-via-vps` / `jetson-via-vps-alt` (reverse tunnel on VPS `:10022`) |
| sudo on Jetson | password — `NEXTCLOUD_ADMIN_PASSWORD` in `~/nasa/config/.env` **on device**; do not print |

Aliases described in `~/.ssh/config` of the station and in `docs/plans/VOSTRO_BASTION_HOME_ACCESS.md`.

## 5. First commands and expected result

```bash
git status --short            # expect a clean working tree after integration
git config --get core.bare    # false; true = hook defect recurred, fix: git config core.bare false
git log --oneline -3          # latest integration commits
git worktree list             # branch deepseek/nas-vpnmon-deploy-prep-20261007 and old deepseek/* — do not delete without check
python E:\agent_coordination\coord.py list --agent nas --open
```

## 6. Work queue

1. **Repository hygiene:** integrated in `d180977`. Synthetic tests clear `GIT_*`;
   ordinary execution (18 tests), an isolated real Git hook and the main repository
   hook passed without bypass.
2. **Monitor preparation:** `deepseek/nas-vpnmon-deploy-prep-20261007` is integrated.
   Hygiene guidance and the VPS memory rule are preserved; SSH instructions apply
   memory limits. This integrates documentation, not deployment.
3. VPS/VPN monitor, task 8 — **awaits owner**, do not start yourself.
4. VPN client failures — profile identified; observe a phone attempt through Deco at the VPS.
5. Audit, stages 19–21 — `docs/audit/2026-10-02_code_audit/PLAN.md`.

## 7. Prompt for first Codex launch

```text
You are Codex in the NAS_Jetson_Nano project. Reply to the owner in Russian. First read
docs/handoff/CODEX_START_2026-10-08.md and everything from its section 1, then run commands
from section 5 and report status: what is in main index, how does branch
deepseek/nas-vpnmon-deploy-prep-20261007 differ, are there open requests on the board for nas.
Review the current queue before changes; deployment remains separately authorized.
On VPS — only under systemd-run with MemoryMax=256M and MemorySwapMax=0; do not touch Amnezia.
```
