# Follow-up plan for the owner's article draft — 2026-10

[Русский](DEVELOPMENT_PLAN_2026-10_OWNER_GOALS.ru.md) · [Work plan](../../WORK_PLAN.md) ·
[Combined plan A–H](DEVELOPMENT_PLAN_2026-09_SBER_ERA.md) · [Checkpoint 2026-10-12](CHECKPOINT_2026-10-12.md)

Compiled on 2026-10-12 from the owner's draft for the second article («Предложения по статье 2» — "Suggestions for article 2", 2026-10-11).
The structure repeats the draft: **part A** — what the solution must provide, **part B** — what the
owner wants to add. For each item: what already exists (with evidence), what is missing, the task,
the priority. Statuses were verified against project documents and by a live Jetson measurement on 2026-10-12 06:17 UTC
(read-only, via the VPS tunnel). External facts (Immich, Home Assistant, Frigate, model pricing)
were verified on the web on 2026-10-12; full reports with sources are in section 8.

**How to read.** Priority: **P0** — now, **P1** — quick wins for the family, **P2** — reliability
deeper down, **P3** — major features, **P4** — smart home. Effort: S (a day), M (a week), L (more).
Worker per rule #16: **C** — Claude (the lead), **S** — a Sonnet subagent, **D** — DeepSeek,
**O** — the owner (sudo, money, decisions, family).

## 0. What emerged on 2026-10-12 — before any plan

| # | Finding | Confirmed by | What follows |
|---|---|---|---|
| 1 | ✅ **Three Jetson power-offs without a clean shutdown (2026-09-29 ≈ 8 h, 2026-10-06 ≈ 2.5 h, 2026-10-11 ≈ 9 h) — the owner cut the power himself** (owner's answer, 2026-10-12) | `journalctl --list-boots`: no shutdown lines from `systemd[1]` and no `Journal stopped`; current boot — `TEGRA_POWER_ON_RESET` | No power outage; D1 (UPS) stays deferred. Risk — a hard power-off with the NTFS archive mounted → REL-10. The 2026-08-17 and 2026-09-18 resets remain "power or PMIC watchdog", indistinguishable |
| 2 | ✅ **The reboot alert (D2) did not work from 2026-09-20 — fixed and deployed on 2026-10-12** | It was `Loaded: error (Invalid argument)`: systemd 237 rejects `Type=oneshot` + `Restart=on-failure`. Deployed with sudo by the owner's permission: `systemd-analyze verify` clean, `LoadState=loaded`, live run `Result=success`, the alert about the 2026-10-11 boot reached the owner in Telegram | Old unit kept as `/etc/systemd/system/…boot-alert.service.bak.1791793669`; gate check — `test_systemd237_units.py` |
| 3 | 🟠 **Four family members' passwords were in the public repository** (since 2026-06-28/29) | Found by DeepSeek during the cleanup inventory; values are not placeholders (checked by mask). **2026-10-12 (owner: "delete"):** memos removed from the repository (`2eb8664`), the owner keeps copies in `docs/local/family-setup/` (outside git); the secret scanner now catches "Пароль: …" — all 18 memo lines | The passwords remain in git history → **they must be changed** (SEC-3). Rewriting history would change 357 commits and break 277 hash citations in 59 documents — owner's decision |
| 4 | 🟠 **The device is ahead of git** — confirmed by measurement | sha256 of three API files in the container = the working tree (Codex's uncommitted code of 2026-10-10), ≠ `HEAD` | The working tree is the only copy of the deployed code (as in the 2026-10-10 checkpoint) |
| 4a | ✅ **GIT-1 mostly closed on 2026-10-12** (Codex unavailable — done by the lead) | `0136af1`: the deployed code matches the device (sha256 after line-ending normalisation); `396ca11`: the gate passes with a declared ratchet exception | Remaining: refactor `home_health.py`/`backup_metadata.py` for the ratchet with a new rollout, and Codex's evaluation tools (not committed) |
| 4b | 🟠 **The gate silently skipped tests** | `preflight.sh` runs `tests/unit` as `python file`; 4 pytest-style files without `__main__` executed nothing — `test_container_watchdog.py` and `test_dl_egress_guard.py` since 2026-09-30 | Fixed in `396ca11` + check `test_unit_tests_runnable.py` |
| 4c | 🟠 **The 2026-10-10 Decisions experiment is revoked** | The Russian case context in `evaluate_health_semantics.py` and its fixtures was saved as `?????`: the model saw numbers and question marks | Do not quote "4/12" until re-run; re-check 24/25 on the boundary set (4 corrupted lines) |
| 4d | 🟠 **E3 may report a disk as mounted when it did not come up** (Sonnet review 2026-10-12, logic confirmed in code) | In the container `/mnt/storage` is a bind mount of `/mnt/storage/downloads`; "mounted" = path `st_dev` ≠ container root `st_dev`. If the SSD is not up before the container starts, Docker creates the directory on the SD card and the check sees "another device" | REL-9 |
| 5 | ✅ Everything else is healthy | 16 containers (was 13: + Docker status proxy, speech recognition, downloads), 0 unhealthy, no failed units; database dumps of 2026-10-12 03:14; SSD 13%, HDD 79% (396 GB free), SD root 43%; Immich 7 068 photos + 647 videos; RAM available 1.3 GB | — |

Separately: from Wi-Fi `192.168.0.14` the Jetson did not answer ARP on 2026-10-12, although its `eth0 192.168.0.50` was up — the measurement went via the VPS. The cause was not investigated (the laptop's network might not have been the home one).

## 1. Part A — what the solution must provide

| Owner's goal | What already exists | What is missing | Tasks |
|---|---|---|---|
| **A1. Resilience: power, reboots** | SSD auto-recovery (since 2026-09-19, verified by a manual run); the OPS-1 container watchdog (recovery in 123 s, 2026-09-30); persistent journal (since 2026-08-23); everything comes up by itself — on 2026-10-11 after 9 h of downtime the 16 containers came back healthy | UPS (D1 deferred); the reset alert is broken; the external watchdog D3 is in git, not deployed; the SSD pull test has not been done | REL-1, REL-2, REL-3, REL-4 |
| **A2. Protection from the external network; control from the corporate network; corporate resources from home** | Outward on the VPS only 22/443/40568; services — only from the VPN; API with JWT and roles, CORS off, gateway with a token (stage C, 2026-09-19); the Vostro bastion with VPS address selection (2026-10-05); the chain Jetson → VPS → Vostro → corporate resource (transport verified on 2026-10-10) | SSH login with a password (C9); recovery of the corporate chain after a drop is not tested; the family's passwords are in git | SEC-3, ACC-1 |
| **A3. Without internet and during network failures** | At home everything works over the LAN; a block on one VPS address is survived by choosing the second one; the local model on the workstation | The Telegram bot goes mute without the internet (by design); the local model is not the main path (`prefer_local=false`); behaviour without WAN is described and tested nowhere | REL-7 |
| **A4. Speed** | Network measurements of 2026-09-12 (wired 87–92 Mbit/s, Wi-Fi 100, via VPN 46–53), disks (SSD 250/172 MB/s, HDD 106/92), local model response 0.6–0.9 s | No load tests; no baseline of service response times (p50/p95) | REL-5, REL-8 |
| **A5. Architecture for growth** | Host layout `/etc/nas-layout.env`; quality gate and metrics ratchet; CI on GitHub and GitVerse; services in separate containers; pinned images (22 `tag@sha256`) | Literal paths in 14 units (SD-2); migration of the device to the new naming (Part B); no `deploy.sh` with version verification | ARCH-1 |
| **Review, tests, fault injection** | Audits of 2026-08-30, 2026-09-19, 2026-09-26, code review of 2026-10-02; monthly restore drills (DRILL OK 2026-09-19); DB restore verified on 2026-08-09; synthetic failures (stage 22) | Full DR on a dedicated stand; a fault-injection programme on the live system; load | REL-4, REL-5, REL-6 |
| **Move to C++** | Plan CPP-1 (2026-10-10): measure first, port only the bottleneck | No measurements | CPP-1 |

## 2. Part B — what to add

| Wish | What already exists | Research finding of 2026-10-12 | Tasks |
|---|---|---|---|
| **B1. Family bot-orchestrator in Telegram** | `@бобик` in the family group «Боровские» (since 2026-09-19): aria2 downloads (SSD ≤ 20 GB / HDD), voice messages (Vosk, since 2026-09-26), "что сломалось" ("what broke") (E3), questions to GigaChat/DeepSeek/the local model; the family did not take to Talk | The orchestrator = an intent router to tools (photos, calendar, downloads, home health); tools are added one by one | FAM-5 |
| **B2. Full Immich, face recognition** | The ML kit for the workstation (D4, runbook) has been ready since 2026-09-12; the blocker is the disabled Windows hypervisor | On the Jetson Nano ML is **impossible**: Immich backends are CUDA ≥ 12.3 / compute ≥ 5.2, ARM NN (Mali), RKNN, OpenVINO, ROCm; Tegra/JetPack 4 is not supported. The working path is the workstation; Immich (since v1.122, ours is v2.7.5) accepts several ML addresses with fallback | FAM-3 |
| **B3. Photo bank of several TB** | The archive is connected as `/HDD-2TB` (Nextcloud) and `hdd2tb` (Samba); the 2026-09-20 inventory was cut short: 271k files ≈ 1.24 TB, ≈ 91k photos, Nikon RAW 420 GB | The Immich external library is read-only; RAW is supported (NEF/CR2/ARW/DNG). Risks: a parallel scan over ntfs-3g (the 2026-09-20 incident) — set parallelism 1; space for previews — estimates diverge (≈ 45–50 GB by typical preview size versus 140–250 GB by secondary sources) — measure on a single directory; the first indexing takes a day or more | FAM-4 |
| **B4. Daily "like Google" collections** | None (stage H3 in the plan) | Immich itself builds "memories"; `GET /memories` → the bot sends an album once a day (`sendMediaGroup`, 2–10 files) to the group. A quick win | FAM-1 |
| **B5. Family calendar and schedule** | Nextcloud Calendar + DAVx⁵ on the phones; the bot does not know the calendar | `caldav` in the bot container: reminders and "what do we have tomorrow?". Syncing with Google/Yandex Calendar — only if the family lives by them, and after our own check | FAM-2 |
| **B6. Free models** | GigaChat (free for individuals: Lite 250 + Pro 40 + Max 25 + Ultra 50 million tokens over 12 months), DeepSeek (cents), the local qwen3.5:4b; OpenRouter — second opinion only | There are no free ChatGPT/Claude/Gemini APIs, or they are unavailable from Russia; Cloud.ru FM has no free tier ("free until 31.10" was a 2025 promotion); OpenRouter likely blocks Russian IPs since 2026-06-27 (secondary sources) — verify ourselves. The current set does not need changing | AI-1 |
| **B7. GPU** | Workstation RTX 3050 Ti 4 GB; Kaggle experience; the Cloud.ru grant excludes GPU | Kaggle (~30 h/week), Colab — open data and tests only; family photos — on the workstation only. No free GPU changes the architecture | AI-2 |
| **B8. Smart home** | Nowhere | **Not on this Jetson**: RAM is taken by family services; Frigate dropped JetPack 4 support (PR #16670, 2025-02-18), and nothing newer than JetPack 4.6 will come to the Nano. Put it on a separate device: an old Inspiron N5110 (₽0, 2nd-generation i3/i5, 4–8 GB — enough for Home Assistant and Zigbee) or an N100 mini-PC (≈ 22k ₽, needed for video) | HOME-0…4 — ⏸ deferred by the owner on 2026-10-12 ("not relevant now") |

## 3. Consolidated queue

| Pr. | ID | Task | Who | Effort | Benefit | Acceptance |
|---|---|---|---|---|---|---|
| P0 | **SEC-3** | ✅ 2026-10-12: memos removed from the tree, the scanner catches text passwords. **Remaining:** change 4 passwords (Nextcloud/Immich) and give the family new memos; rewrite history only if the owner decides (cost: 357 commits, 277 citations in 59 documents) | O (family) + C | S | High | Old passwords don't log in; the scanner catches a synthetic "Пароль: …" in `.txt` (test exists) |
| P0 | **REL-1** | ✅ 2026-10-12: D2 unit fixed (`Type=simple`, `StartLimit*` in `[Unit]`), gate check, deployed with sudo, the live run delivered the alert | C + D (test) + O (sudo) | S | High | Done; after the next reboot the alert arrives on its own |
| P0 | **REL-2** | ✅ 2026-10-12: the three power-offs were the owner's; D1 (UPS) is not revisited | O + C | S | — | Recorded |
| P1 | **REL-10** | Safe shutdown: before cutting power — `sudo poweroff` or an owner-only bot command ("бобик, выключи NAS" with confirmation). A hard power-off with `ntfs-3g` mounted can leave the volume dirty — a risk to the only copy of the archive | S + D (tests) + C | S | High | After a command shutdown the journal has shutdown lines from `systemd[1]`, D2 does not fire |
| P0 | **GIT-1** | ✅ 2026-10-12: deployed snapshot committed as `0136af1`, `?????` restored (from numbers and the EN summary, marked as such), gate fixed. **Remaining:** refactor `home_health.py` and `backup_metadata.read_snapshot` (cc 27) for the ratchet + rollout; Codex's evaluation tools — restore the Russian context, simplify functions, re-run the experiment, commit | S (refactor) + D (tests) + C | M | High | Full `preflight.sh` green without `NAS_METRICS_ALLOW`; container hashes = `HEAD` |
| P1 | **REL-9** | E3: take mount state not from `st_dev` inside the container but from a host snapshot (cron already writes dump metadata every 5 min — add `mountpoint` and size for `/mnt/storage`, `/mnt/hdd2tb`); no snapshot or older than 15 min — "unknown" | S + D (tests) | S | High | Test: a directory on the root device → not "mounted"; REL-4 drill "SSD did not come up" → the bot tells the truth |
| P1 | **REL-3** | An alert on units in `failed` **and** with a load error (`LOAD=error`) — it would have caught REL-1 on the very first day (D4 of the A–H plan) | S (per the lead's design) + D (tests) | S | High | A broken test unit → a message to the owner |
| P1 | **FAM-1** | "On this day" once a day: Immich `GET /memories` → an album to the shared family group (owner's decision 2026-10-12); on request "бобик, что было в этот день" ("bobik, what happened on this day") | S + D (tests) | S | High for the family | The collection arrived at 09:00 MSK; an empty day — silence, not an error |
| P1 | **FAM-2** | Calendar: the family lives in **Google and Yandex calendars** (owner's decision 2026-10-12). The bot reads them read-only — Google via the secret iCal address (no OAuth), Yandex via CalDAV or the export link; a morning summary and reminders in the shared group; the links are secrets kept in `config/.env` | S + D | S–M | Medium | An event created in Google or Yandex calendar → a reminder in the group |
| P1 | **FAM-3** | Face recognition: enable the hypervisor on the workstation (admin + reboot), ML per runbook D4, in Immich — the workstation's address via a reverse tunnel; batch indexing while the workstation is on | O (hypervisor) + C | M | High | Faces on ~7.7k assets; with the workstation off Immich works without ML |
| P2 | **REL-4** | Fault injection by scenarios: power cut, SSD pulled, HDD pulled, WAN loss, VPS unreachable, workstation off, Telegram unreachable. For each — expected behaviour, time measurement, alert | C + O (window, physical actions) | M | High (and for the article) | A table "scenario → what we saw → recovery time → alert" |
| P2 | **REL-5** | Load: parallel photo upload to Immich, a Samba stream, N simultaneous questions to the bot, API p50/p95; in a window, without replacing production services | C + S | M | Medium | A report with the numbers and the limit at which the Jetson starts to fail |
| P2 | **REL-6** | Full DR on a dedicated stand (already in the plan, criteria — `docs/quality/BACKUP_RESTORE_TESTS.md`) | C + O (stand) | L | High | Both databases and the applications raised on the stand, RPO/RTO measured |
| P2 | **REL-7** | Autonomous mode: describe and test "a home without internet" (LAN services, Samba, Immich at home; the bot is silent; the local model); show the family what works | C | S | Medium | The REL-4 scenario "no WAN" is passed, a memo in `docs/` |
| P2 | **REL-8** | Speed baseline: a table of measurements with dates (network, disks, bot response, Immich), repeated quarterly | D (collection from documents) + C (measurements) | S | Medium | The table in `docs/` |
| P2 | **ACC-1** | Corporate access: SSH login by key only (C9, carefully — the only path), verifying recovery of the chain after a drop and a reboot | C + O | S–M | Medium | `sshd -T` → `passwordauthentication no`; the chain came up by itself after a restart |
| P2 | **ARCH-1** | Extensibility: SD-2 (paths in units), `deploy.sh` with SHA verification (F2), a window for Part B (F1) | D + C | M | Medium | No `/home/admin` in `systemd/*`; deployment verifies versions |
| P2 | **CPP-1** | Python/C++ experiment per the 2026-10-10 plan | D + C | M | For the article | Measurements and a decision, including a negative one |
| P3 | **FAM-4** | Photo bank: finish the H1 inventory strictly one directory at a time; the pilot — **one** directory as an Immich external library (read-only, parallelism 1), measure preview space and time; decision H2 by the numbers | C (ntfs-3g — lead only) + O | L | High | The pilot numbers; decision H2 recorded |
| P3 | **FAM-5** | Bot-orchestrator: a single intent layer → tools (photos, calendar, downloads, health); a classifier in Russian (E1) | S + D | L | High | The bot picks the tool without keywords in 9 of 10 test phrases |
| P3 | **AI-1** | Models: keep GigaChat + DeepSeek + the local one; check OpenRouter availability from Russia without VPN; update `docs/29` (IP block, Pro/Ultra quotas) | D | S | Low–medium | The document updated with a measurement date |
| P3 | **AI-2** | GPU: the workstation is primary; Kaggle — open data only (benchmarks, training an intent classifier on synthetic data) | C | S | Low | The rule recorded in `docs/29` |
| ⏸ | **HOME-0** | Reconnaissance (₽0): the meter's model (photo), what of Yandex is already at home, whether an open port is needed for Alice (cloud mode `yandex_smart_home`) | O + S | S | — | A list of devices and the answer about the port |
| ⏸ | **HOME-1** | Hub on a separate device: Home Assistant (Container) + Zigbee2MQTT on the Inspiron N5110 + a Zigbee coordinator (≈ 3.7–6k ₽) + lamps | O (purchase) + C | M | Medium | The lamp turns on from HA and on a schedule |
| ⏸ | **HOME-2** | Alice: HA devices → Alice, speaker control | C | M | Medium | «Алиса, включи свет» ("Alice, turn on the light") works |
| ⏸ | **HOME-3** | Meter without touching the sealed unit: PZEM-004T + ESPHome at the input of one's own panel | O (electrician) + C | M | Medium | Hourly consumption in HA |
| ⏸ | **HOME-4** | Video: Frigate on a separate mini-PC with its own disk (1080p ≈ 20–40 GB per day per camera); **not** on the HDD with the archive | O (purchase) + C | L | Under question | The owner's decision after HOME-1 |

**Order.** P0 — before any new features (a week). P1 — in parallel, this is what the family will
notice. P2 — in maintenance windows; REL-4 and REL-5 give both reliability and article chapters. P3 after P1.
The smart home (⏸, formerly P4) was deferred by the owner on 2026-10-12 — the research is kept for when he decides.
**Done on 2026-10-12:** REL-1, REL-2, most of GIT-1 and SEC-3 (except changing the passwords).

## 4. The article, part 2 — what is done and what lies ahead

**Done:** the offline pack on the desktop (2026-10-10): Codex's long draft (~55k characters) and a check of ~60
claims, 12 case cards, dated numbers, 15 diagrams, analyses of 8 exemplar articles, a response to the Part 1 critique;
the owner's draft (2026-10-11); the article draft based on the draft (2026-10-12, `Черновик статьи по моей
заготовке — 2026-10-12.md` — "Article draft based on my outline — 2026-10-12.md" — in the same pack).

**What is missing for the structure of the draft:**

| Section of the draft | In the materials | Needs to be obtained | Task |
|---|---|---|---|
| Point A — "real tests and results" | Audits, test counts, drills, the 123 s watchdog, DP-2 (403/503), VPS blocks | A fault-injection table, load, full DR | REL-4, REL-5, REL-6 |
| "The scheme of accepting testers" | The quality gate, agent roles (diagrams in the pack) | A fresh screenshot of a gate run and GitVerse CI | — |
| Move to C++ | Plan only | CPP-1 measurements | CPP-1 |
| Features B1–B5 | The bot, downloads, voice — live | Collections, calendar, faces — after P1 | FAM-1…3 |
| Smart home | The 2026-10-12 research | The owner's decision on HOME-0/1 | HOME-0 |
| Honest stories | 12 cards | New ones: the alert that could not fire (REL-1); three silent resets (REL-2) | REL-1, REL-2 |

⚠️ Publish the password story (SEC-3) only **after** the passwords are changed and the history purged.
⚠️ Habr rule #4 (verified on 2026-10-10): text generated or edited by a neural network is forbidden.
The draft is material for the owner to rewrite, not text for publication.

## 5. Documentation and cleanup

| ID | What | Status |
|---|---|---|
| DOC-0 | Local cleanup: 28 DeepSeek working copies deleted (uncommitted content — in `.agent-work/archives/worktrees-2026-10-12/`, 419 KB; two branches with unique commits kept, patches saved), 37 merged `deepseek/*` branches deleted, temporary builds and caches deleted — `.agent-work` 914 → 234 MB | ✅ 2026-10-12 |
| DOC-1 | Entry documents (README, `docs/index.md`, `00_OVERVIEW`, `PROJECT_CONTEXT`) are partially stale — per the `STALE_DOCS_REPORT` | P1, D + C |
| DOC-2 | EN/RU pairs: of 290 documents, 15 are paired, 166 bilingual in one file, 109 monolingual. Translation — as a series of DeepSeek cards **after** DOC-3 (fewer files — cheaper) | P2, D; agree the budget (shared account) |
| DOC-3 | Cleanup of tracked files per the `CLEANUP_CANDIDATES` list (≈ 50 to delete, 13 to delete with link fixes, ≈ 55 — the lead's decision; screenshot duplicates in 2–6 places) | Awaiting the owner's confirmation |
| DOC-4 | `CLAUDE.md`: move the August "Operational state" section into the checkpoints, leave a dated table of the current state | P2, C |
| DOC-5 | The rest of the local cleanup: the 2026-10-06 archive (230 MB, 13 zip files of old agent working copies) — the owner's decision; hundreds of empty `tmp*` in `.agent-work/tmp` with locked permissions — `takeown` from an administrator; 6 unmerged branches `fix/*`, `quality/*`, `worktree-agent-*` — to sort out | Awaiting the owner |

## 6. Owner decisions

1. **SEC-3:** ✅ "delete" (2026-10-12) — removed from the tree. **Open:** when to change the family passwords; whether to rewrite history (cost — section 0, item 3; recommendation: change the passwords and leave history alone).
2. **REL-2 / D1:** ✅ the owner cut the power; no UPS needed.
3. **REL-1:** ✅ sudo granted, deployed on 2026-10-12.
4. **FAM-3:** enable the hypervisor on the workstation (admin + reboot) — open.
5. **FAM-1:** ✅ to the shared group.
6. **FAM-2:** ✅ Google and Yandex calendars.
7. **HOME-0/1:** ✅ smart home deferred ("not relevant now").
8. **DOC-3 / DOC-5:** confirm the list of tracked files to delete; delete the 2026-10-06 archive? — open.
9. **DOC-2:** budget for the document-translation series (DeepSeek, shared account with Belgorod) — open. Article drafts are not put into the repository (owner's decision 2026-10-12); pushing commits to GitHub and GitVerse allowed on 2026-10-12.

## 7. Risks and rollback

The plan is a document; the system does not change with it. Every device change is a separate deployment per the
project rules (backup, proven rollback, the "the new code runs" check), rule #13 for the VPS.
The smart home is not installed on the Jetson and does not touch the VPN network.

## 8. Sources

- The owner's draft: `Предложения по статье 2.md` ("Suggestions for article 2"; desktop pack, 2026-10-11).
- Inventory of goals across documents (DeepSeek, 2026-10-12, accepted manually after selective verification) and
  Sonnet research with web sources: `.agent-work/tmp/plan-2026-10-12/` (outside git):
  `OWNER_GOALS_INVENTORY.md`, `research_photos_calendar.md`, `research_smart_home.md`,
  `research_models_gpu.md`, `STALE_DOCS_REPORT.md`, `CLEANUP_CANDIDATES.md`.
- Live Jetson measurement 2026-10-12 06:17–06:40 UTC (read-only): checkpoint 2026-10-12.
- Key external sources: docs.immich.app (ML acceleration, external libraries), github.com/blakeblackshear/frigate PR #16670,
  home-assistant.io (Docker requirements), developers.sber.ru (GigaChat quotas for individuals).
