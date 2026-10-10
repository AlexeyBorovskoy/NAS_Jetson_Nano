# Checkpoint — 2026-10-10

[Русский](CHECKPOINT_2026-10-10.ru.md) · [Work plan](../../WORK_PLAN.md) · previous: [2026-10-09](CHECKPOINT_2026-10-09.md)

Recorded on the evening of 2026-10-10 before the workstation was shut down. Two sessions worked on the
project: Codex (board agent `nas`) and Claude Code (`nas-claude`). **[Codex]** marks Codex's results as
logged in `docs/articles/HABR_PART2_MATERIALS.md` and the article plan; Claude did not re-verify them.

## 🔴 Key state: the device is ahead of git

- `main` = `origin/main` = `gitverse/main` = `gitverse/master` = **`922161d`**.
- The working tree holds **24 uncommitted entries** from Codex (13 modified, 11 new): API compose,
  `storage.py`, `home_health.py`, new `backup_metadata.py` and `scripts/monitoring/nas_backup_metadata.py`,
  `scripts/network/ssh_vostro_proxy.sh`, `scripts/quality/evaluate_*.py`, tests and `tests/fixtures/`,
  `WORK_PLAN*` (with the new CPP-1), article and security docs, `ds_worker.toml`.
- **[Codex] DP-2/DEP-1 and live E3 were deployed to the Jetson on 2026-10-10**, but the matching files are
  not in git. Git is currently **not a superset of the device**. Do not clean or reset the working tree on E:.
- Three Codex files have Russian text saved as literal `?????` (PowerShell write without UTF-8):
  `HABR_PART2_ARTICLE_PLAN_2026-09.md` — 10 lines, `HABR_PART2_MATERIALS.md` — 29,
  `docs/handoff/DEEPSEEK_WORKER.md` — 29 (`grep -c '??????'`). Only Codex can restore them;
  **do not commit these files until restored**.

## Done on 2026-10-10

| Block | Result | Verification boundary |
|---|---|---|
| DP-2/DEP-1 + E3 [Codex] | Jetson ARM64, API as UID 10001, API 200 / restart 503 / proxy 403; owner confirmed the E3 Telegram reply; stat-only dump snapshot (Nextcloud 2.6 MB, Immich 19.1 MB, 7 h old, 14 files; refreshed every 5 min, older than 15 min = unknown) | Code not in git; rollback prepared, not executed; repeat reply after the metadata fix not confirmed; systemd in E3 is unknown |
| GitVerse CI #264 [Codex] | `922161d`, success, 1 min 30 s | — |
| Spektr / ds-worker episode [Codex] | Primary JSON: 46 turns against a limit of 45, **18** rejected commands (not 17); six counted attempts $0.280097 | NAS did not rerun Spektr's application tests |
| Decisions API [Codex] | 25/25 easy and 24/25 boundary synthetic tasks; health semantics 4/12 with a false "fault" on timeout (confidence ~0.933) — **the model is not accepted as a health-status source** | Synthetic data; not proof of general accuracy |
| Home → corporate resource [Codex] | Jetson → VPS → Vostro → DNS + TCP to a corporate SSH port | Transport only; recovery after a drop or reboot not tested |
| Habr article part 2 | Codex: long draft (~55k characters) and editor notes (`docs/articles/HABR_PART2_LONG_PROTOTYPE_2026-10-10.md`, `…_EDITOR_NOTES_…`, DOCX in `artifacts/articles/habr-2026-10-10/`). Claude: independent check of ~60 claims — no substantive discrepancies (`.agent-work/tmp/claude-factcheck-20261010.md`) | The draft is research material, not publishable text (see below) |
| Offline pack for the owner | `C:\Users\Alexey\Desktop\Хабр часть 2 — материалы к статье\` (outside git): draft and fact-check, outlines, 12 case cards, dated numbers table, verified code excerpts, 15 diagrams, 8 exemplar-article analyses, Part 1 critique response, rules | No screenshots of live systems |
| Part 1 critique response | All 9 comments (live page on 2026-10-10: 14K views, 23 bookmarks, +6, no new comments); status of every point and of the author's three promises: 2 TB HDD ✅, orchestrator 🟡, GPU and Immich ML ❌ | — |
| Habr rule #4 | Verified verbatim on 2026-10-10: texts generated **or edited** by neural networks are not allowed; AI cover images, supplementary images and a small share as a supplement to the author's text are. Tekhnotekst-8 bans AI entirely and is closed (articles up to 2026-04-17) | The owner writes the article text himself |
| Claude ↔ Codex channel | Added `nas-claude` to `E:\agent_coordination\coord.py` (backup `coord.py.bak.1791641830`): the board hides an agent's own messages, so `nas → nas` never arrived | Shared neighbour tool; the `nas` hook was re-tested after the edit |
| Plan | CPP-1 added to `WORK_PLAN*` — a future Python/C++ experiment on one component, after reliability work [Codex] | Not started |

## Next steps (in order)

1. **Codex restores** the corrupted lines in the three files (and says so on the board, `nas → nas-claude`).
2. **Review Codex's uncommitted code** (E3, `backup_metadata`, compose/`storage.py`, `evaluate_*`, Vostro proxy) — read-only, report; then a full `preflight.sh`, and **one lead** commits a verified, specific set (no wide staging) so git is again a superset of the device. Push only with the owner's permission.
3. 2026-10-11: the owner works on the article text offline. Afterwards: take the listed screenshots
   (`06 Схемы и скриншоты/00_Что_здесь_и_что_снять.md` in the pack) and refresh the pack once Codex's files are restored.
4. **Full DR on an isolated stand** — still open (planned for 2026-10-10, not done).
5. Board: `m0260` (geoserver, Digital Twin infrastructure) unanswered since 2026-10-08; `m0289` — `work`'s answer for the article still pending.
6. Cleanup with the owner's permission: the ds-worker worktree and branch `nas-habr-code-excerpts-20261010`; 27 worktrees in total.

## Workers and cost

- Codex — deployment, E3, experiments, article draft. Claude — coordination, fact-check, offline pack, diagrams, critique response.
- Claude subagents (Sonnet, model set explicitly): exemplar articles and rules, case cards, draft fact-check — ≈660k tokens of the Claude limit.
- DeepSeek on 2026-10-10 (`ds-worker report --since 2026-10-10`): 5 attempts, **$0.1171**, 94.12% cache, 0 retries; of that, code excerpts for the pack — $0.0526 (accepted manually after a line-by-line check).

## Risk and rollback

Main risk: code on the device is not in git; losing the working tree would make the DP-2/DEP-1 deployment
unreproducible. Do not run `git stash`, `checkout --` or `clean` in the main checkout. Rolling back DP-2 on the
device follows Codex's prepared plan and only with the owner's permission. This commit contains only the
checkpoint documents — revert with a plain `git revert`.
