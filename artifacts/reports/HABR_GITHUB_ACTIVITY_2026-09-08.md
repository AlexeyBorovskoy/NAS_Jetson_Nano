# Habr + GitHub activity — NAS_Jetson_Nano

> Snapshot: **2026-09-08**. No secrets. Sources: live Habr page/comments, `gh api`, repo docs.

---

## 1. Habr — Part 1

| Field | Value |
|---|---|
| URL | https://habr.com/ru/articles/1062914/ |
| Author | [Alexey_git](https://habr.com/ru/users/Alexey_git/) |
| Published | 2026-07-25 10:46 |
| Title | Старому Jetson Nano — домашнее облако: Nextcloud, Immich, CGNAT и три USB‑сбоя |
| Hub flags | DIY, sys_admin, dwh, hardware, antikvariat · **Из песочницы** · Кейс |
| Read time | 8 min · medium |
| Reach / readers | **13K** |
| Rating | votes 4 (↑3 ↓1), score **+6** |
| Bookmarks | **22** |
| Comments | **9** (link: `/comments/`) |
| GitHub CTA | https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano |

Repo canon already points here: `docs/articles/publication_status.md`, `docs/plans/POST_HABR_FEEDBACK_2026-08.md`, `docs/articles/README.md`, CHANGELOG.

Part 2: still **in preparation** (not published).

---

## 2. Comments: live vs project docs

### Live thread (fetched 2026-09-08)

| # | Author | Date (MSK) | id | Summary |
|---|---|---|---|---|
| 1 | **Lev3250** | 25 Jul 19:42 | 30261680 | Joke on «сервисов» / VPS line |
| 2 | **vvzvlad** | 25 Jul 22:36 | 30262028 | «Claude wrote the article»; why JetPack if GPU unused |
| 3 | Alexey_git | 27 Jul 09:39 | 30266726 | Reply: GPU + orchestrator planned |
| 4 | **tklim** | 26 Jul 06:05 | 30262372 | 4 GB + Docker; Immich RAM mins; USB heat; no open ports / VPN-only |
| 5 | Alexey_git | 27 Jul 09:41 | 30266734 | Reply: used what we had; no overheat; 2 TB HDD next |
| 6 | **dE1l** | 27 Jul 04:51 | 30265652 | Odd to disable Immich ML on board with NPU; else use Pi |
| 7 | Alexey_git | 27 Jul 09:41 | 30266740 | Reply: if buying new → Pi; used on-hand hardware |
| 8 | **falcon4fun** | 29 Jul 22:30 (edited) | 30278360 | Immich without ML = waste; offload ML + hwaccel; N150 box |
| 9 | Alexey_git | 30 Jul 05:52 | 30278802 | Reply: will try Immich ML; no N150 spend; on-hand build |

**Total still 9.** Discussion window **25–30 Jul 2026**. No comments after 30 Jul. No new authors since docs were written (2026-08-01).

### Compare to `POST_HABR_FEEDBACK_2026-08.md`

| Doc claim | Live | Match? |
|---|---|---|
| 9 comments | 9 | Yes |
| 4 readers + author replies | Readers: Lev3250, vvzvlad, tklim, dE1l, falcon4fun (=5) + 4 author replies | **Near-match** — doc says «4 readers»; omits Lev3250 as a content source (joke only) |
| Discussion 25–30 Jul | Same | Yes |
| Analyzed: vvzvlad, tklim, dE1l, falcon4fun | Present live | Yes |
| Lev3250 | Present live, not in action table | **Not new** — already on page; never treated as roadmap input |

### NEW comments not in project docs

**None.** Comment count and set are unchanged since `publication_status.md` / `POST_HABR_FEEDBACK_2026-08.md` (verified 2026-08-01).

Optional doc hygiene (not activity): count readers as 5 if including Lev3250; leave action table as-is (joke has no engineering delta).

### Engagement delta vs early post-pub expectations

| Metric | Pre-pub hope (`ARTICLE_AUDIT_REPORT`) | Live 2026-09-08 |
|---|---|---|
| Views | 2k–5k «good» | **13K reach** (strong) |
| GitHub stars (2 weeks) | 20–50 | **0** |
| Comments | — | 9, stopped end of July |

Reach is solid; conversion to stars/forks did not materialize.

---

## 3. GitHub — AlexeyBorovskoy/NAS_Jetson_Nano

Queried: `gh api repos/...`, stargazers, issues, pulls, releases, traffic/views, traffic/clones, popular referrers/paths, commits, GraphQL discussions.

### Core counters

| Metric | Value |
|---|---|
| Visibility | public |
| Created | 2026-05-31 |
| Last push | **2026-09-07T14:53:51Z** |
| Last repo update | 2026-09-07T14:55:06Z |
| Stars | **0** |
| Forks | **0** |
| Watchers / subscribers | **0** |
| Open issues (API `open_issues_count`) | **6** (includes open issues only; PR count separate) |
| Language / license | Shell · MIT |
| Size | ~12 MB |

Stargazers list: empty.

### Issues (state=all)

| # | State | Title | Author | Created | Updated | Notes |
|---|---|---|---|---|---|---|
| 9 | **open** | Доработки по отзывам с Хабра (на текущем железе, без покупок) | AlexeyBorovskoy | 2026-08-01 | 2026-08-22 | 2 comments; Habr follow-up tracker |
| 8 | closed | Update README with quick start and requirements | **Disha28r** | 2026-07-08 | 2026-07-09 | **PR** merged |
| 6 | closed | feat: Netdata Telegram alerts | AlexeyBorovskoy | 2026-06-21 | 2026-08-22 | closed 2026-08-22 |
| 5 | **open** | feat: Raspberry Pi 4/5 bootstrap guide | AlexeyBorovskoy | 2026-06-21 | 2026-06-21 | 0 comments |
| 4 | **open** | feat: Add HTTPS via Let's Encrypt for VPS nginx | AlexeyBorovskoy | 2026-06-21 | 2026-06-21 | 0 comments |
| 3 | **open** | Good first tasks for contributors | AlexeyBorovskoy | 2026-06-20 | 2026-07-08 | 2 comments |
| 2 | **open** | Security/privacy review wanted | AlexeyBorovskoy | 2026-06-20 | 2026-06-20 | 0 comments |
| 1 | **open** | RFC: Architecture review wanted | AlexeyBorovskoy | 2026-06-20 | 2026-06-20 | 1 comment |

**External contributor signal:** one merged PR (#8, Disha28r, Jul). No new issues/PRs from others since then. No issue activity after **2026-08-22**.

### Pull requests

- Only PR: **#8** merged 2026-07-09 (README quick start). No open PRs.

### Discussions

- totalCount **1**: «👋 Welcome — расскажите о вашем железе» (AlexeyBorovskoy, 2026-06-21). No new discussions.

### Releases

| Tag | Title | Date |
|---|---|---|
| **v1.5.0** | Семейный ИИ-помощник + честность вместо обещаний | 2026-08-11 |
| v1.4.0 | JMS583 USB SSD + Nextcloud Talk + NASA API v0.6.0 | 2026-06-29 |
| v1.3.8 … v1.3.0 | earlier stage tags | 2026-06 |

Latest published release still **v1.5.0** (no tag after Aug 11 despite Sep commits).

### Traffic (last ~14 days, owner API)

**Views:** count **6**, uniques **5** (sparse; max 2/day on 2026-09-05).

**Clones:** count **185**, uniques **48** — dominated by automation/local tooling spikes:

| Day | Clones | Uniques |
|---|---|---|
| 2026-08-25 | 17 | 9 |
| 2026-08-30 | 56 | 5 |
| 2026-08-31 | 12 | 5 |
| **2026-09-07** | **80** | **18** |
| other days | 0–4 | 0–4 |

**Popular referrers:** `github.com` only (2). **Paths:** Overview 4, discussions 1, issues 1.

Interpretation: clone volume ≠ public audience; views near-zero. Habr→GitHub referral not visible in 14-day referrer window (article traffic peaked earlier).

### Recent commits (since ~Aug 2026)

| When | Theme |
|---|---|
| **2026-09-07** (6 commits) | Sber stack: GigaChat/Cloud.ru FM, GitVerse SSH mirror, ADR-0007/8/9, offline deploy pack — device cutover still pending |
| **2026-08-30** (cluster) | Full technical audit (`docs/audit/`), RU+EN bilingual pass (~50 docs), git↔device sync (HDD-2TB/Samba/OOM limits), `check_no_secrets.sh` false-positive fix, second VPS IP note |
| **2026-08-25** | AmneziaVPN desktop client workaround docs; peer expansion notes |
| **2026-08-24** | Off-site backup checkpoint, Talk-bot timeout fix docs |
| **2026-08-11** | Release **v1.5.0** |

**Last push detectable after Aug 2026:** yes — continuous owner activity through **2026-09-07**, concentrated on docs/Sber integration and audit, not on public community growth.

---

## 4. Cross-channel summary

| Channel | Status 2026-09-08 | vs docs / Aug |
|---|---|---|
| Habr Part 1 | Live, 13K reach, +6, 22 bookmarks, 9 comments | Metrics improved on reach vs early hopes; **comments frozen** |
| Habr Part 2 | Not published | Unchanged |
| NEW Habr comments | **0** | Fully reflected in `POST_HABR_FEEDBACK_2026-08.md` |
| GitHub social | 0★ 0 forks 0 watchers | Unchanged; Habr did not convert to stars |
| GitHub issues/PRs | 6 open issues; 1 historical external PR | Last issue touch 2026-08-22 |
| GitHub code/docs | Active push 2026-09-07 | Strong owner activity post-Aug |
| Traffic | Low human views; high clone spikes | Tooling/CI-like pattern |

---

## 5. Risks / notes

- Public interest on Habr did not translate to GitHub stars; promotion loop (article → repo → community issues) is weak.
- Issue #9 still open as the Habr-feedback umbrella; many phases closed in docs but issue not bulk-closed.
- Clone spikes on 08-30 / 09-07 likely agent/local mirrors — do not read as external adoption.
- No secrets in this report; no live device commands run.

---

## 6. Next safe step (suggestion only)

1. Optionally close or checklist-update GitHub **#9** against `POST_HABR_FEEDBACK` phase table (docs already ahead of the issue).
2. When Part 2 is ready, publish and re-run this snapshot (comment/star delta).
3. No Habr doc update required for comments — set is stable.

---

## Sources

- https://habr.com/ru/articles/1062914/
- https://habr.com/ru/articles/1062914/comments/
- `docs/plans/POST_HABR_FEEDBACK_2026-08.md`
- `docs/articles/publication_status.md`
- `gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano` (+ issues, pulls, stargazers, traffic, commits, releases, GraphQL discussions)
