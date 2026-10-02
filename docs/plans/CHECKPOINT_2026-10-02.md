# Project checkpoint 2026-10-02 — code audit and plan execution

> **Updated in the evening:** branch `quality/code-audit-2026-10` was fast-forwarded into `main` and published to GitHub and GitVerse (`main` = `master`). The device and the VPS were not touched; there was no rollout.
> Russian version — `CHECKPOINT_2026-10-02.ru.md`.

## 1. Done (all in the branch, the gates with the ratchet passed)

| Commit | What |
|---|---|
| `81c1638` | code audit `docs/audit/2026-10-02_code_audit/` + `scripts/quality/code_metrics.py`; the wrong CQ-03 scenario withdrawn |
| `d88dedb` | stage 5, CQ-15: the talk-alert self-check test fails via `assert` |
| `c3c6623` | stage 6, CQ-11: the NAS API compose check in CI is blocking |
| `9ee6c5a` | stage 3, CQ-10: `--max-time 10` on 8 curl calls to Telegram + gate section 7в (DeepSeek) |
| `6d0c8f7` | stage 4, CQ-03: `_head_size` records the reason (Sonnet) |
| `8a02001` | stage 1, CQ-01 (P1): the bot's HDD check via `blocking.run_io` (Sonnet) |
| `aaa6b07` | stage 2, CQ-05/07/04: exceptions do not go to the chat, reasons go to the log and `/health` (Sonnet) |
| `75e5c21`, `1f9cd90`, `210d0d4` | stage 8: the metrics ratchet — `--check/--update`, section 10 in `preflight.sh`, a CI step, 19 tests (Sonnet). Self-checked: a function with CC 23 turns the gates red |
| `b4691ba` | the ratchet caught our own work: the awk of section 7в moved into `tg_curl_timeout.awk`; two regressions accepted with reasons |
| `1c7eb98`, `51912d4`, `f3d951c` | stage 11, CQ-02: the `app/services/` layer, `test_layering.py`; private cross-module calls 13 → 0 (Sonnet) |
| `fc9c91a` | baseline after stage 11: a move is not new code (R3 does not tell them apart) |

Gates at `fc9c91a`: nas_api 221, llm_gateway 52, watchdog 44, backup_api 24+1 skip, stt 17, unit 22, the ratchet — no violations.

## 2. Addendum to the audit (REPORT §12, PLAN stages 15–24)

Following the assessment in the second prompt "full architecture audit", the behaviour passes, coupling and criticality were taken.
- **P1:** GW-6↑ — DeepSeek without a timeout became the fallback path after GigaChat (the bot gives up first);
  TO-02 — images: the gateway up to 420/600 s, the bot 300 s.
- **P2:** CC-01 — the "файлы" ("files") page exhausts the anyio pool on a hanging HDD; CC-02 — downloads
  are paused forever after an error in the middle of the guard; tests for `immich_hdd_second_copy.sh` and
  `check_no_secrets.sh` (critical, no tests).
- **CQ-18:** 27 of the 66 NAS API settings cannot be set through `.env` (including the image timeout — that is why
  stage 18 comes before 15).
- Rejected: TO-04 = the earlier SD-4 (for `Type=oneshot` the start timeout is disabled).
- An open question for the device: whether the disk roots are mounted into the API container (otherwise the HDD check
  in "что сломалось" ("what broke") checks nothing).

Prompt: `C:\Users\Alexey\Downloads\PROMPT-universal-code-audit.v3.md` (criticality, coupling,
mandatory behaviour passes, evidence levels).

## 3. Next

0. ✅ Done: branch pushed, merged into `main` (`3e56d3f`), CI green on `3e56d3f` (both new blocking checks — NAS API compose validation and the metrics ratchet — passed in CI for the first time). ✅ **GitHub Pages is built by our own workflow** `.github/workflows/pages.yml` (`90bdc41`): the built-in build had failed since 2026-10-01 because it could not clone the private submodule `tools/deepseek-worker`; the Pages source was switched to "GitHub Actions", build and deploy are green, the site returns 200.
1. Push the branch and merge into `main` — on the owner's word (rule no. 15 requires publishing).
2. Rollout of stages 1–4, 11 to the Jetson — only on "деплой" ("deploy"), per the runbook (live checks: "что сломалось",
   the gateway `/health`, a download). After the rollout an announcement to the group is not needed (nothing visible to the family),
   except for the local-command error text.
3. Next stages: 18 → 15 → 16, then 17 and 22.
4. The board: `m0158` (Vostro rules) is unanswered.
5. Attention: on resuming after the limit, a subagent reported a block "смена email пользователя" ("changing the user's email") in the
   tool output; nothing was done about it.
