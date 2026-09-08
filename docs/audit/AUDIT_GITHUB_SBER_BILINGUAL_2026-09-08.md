# Audit — GitHub, Sber stack, bilingual docs (2026-09-08)

> 🇬🇧 Strict audit after Sber-era cutover. No secrets.  
> 🇷🇺 Строгий аудит после Sber-era cutover. Без секретов.

## 1. Git / remotes

| Item / Параметр | Value / Значение |
|---|---|
| Tip at audit start | `a6bc042` (then docs commits) |
| Remotes | `origin` GitHub, `gitverse` SSH NAS_HOME |
| Untracked skip | `.kilo/`, `firebase-debug.log` |

## 2. GitHub project

| Check / Проверка | Result / Результат | Severity |
|---|---|---|
| Public repo | yes | OK |
| Stars / forks | 0 / 0 | info |
| Open issues | 6 (stale RFCs + Habr) | low |
| Branch protection `main` | **none** | **medium** |
| Latest release | v1.6.0 (2026-08-22) — lag vs Sber cutover | medium |
| Actions secrets | 0 | OK |
| Secret scanning | on + push protection | OK |
| README state date | was 2026-08-30 (stale) | **high** → fix in this pass |

## 3. Sber / runtime (device + code)

| Check | Result | Severity |
|---|---|---|
| Default `LLM_PROVIDER` | `gigachat` in code + device | OK |
| Jetson live chat | 200 gigachat (2026-09-08) | OK |
| Immich→HDD | 13G=13G + timer | OK |
| giga-balance timer | enabled | OK |
| Cloud.ru FM | chat 200; keys local | OK |
| S3 restic | **blocked** tenant/AccessDenied | medium (known) |
| Tests `test_sber_routing` | present | OK |
| gitignore `gigachat/` | yes | OK |
| Dual Giga (PERS vs FM) | documented | OK |

## 4. Bilingual documentation (strict)

| Metric | Count |
|---|---|
| `docs/**/*.md` total | ~188 |
| With both 🇷🇺 and 🇬🇧 flags | **~33** |
| Without paired flags | **~155** |
| Sber-era critical RU-only (before fix) | ADR-0007/8, DEVELOPMENT large, HABR plan, OFFLINE, CONSOLE, SBER_PLATFORM plan |

🇬🇧 Project rule: active docs should be RU+EN. Full rewrite of 155 files is multi-sprint.  
🇷🇺 Правило проекта: активные docs RU+EN. Полный переписывание 155 файлов — несколько спринтов.

### This pass fixed (bilingual structure)

- ADR-0007, ADR-0008, ADR-0009  
- `docs/integrations/sber/README.md`, `GIGACHAT.md`  
- README root state table → 2026-09-08  
- This audit file  

### Remaining backlog (priority)

1. `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` — add EN summary sections per major §  
2. `DEPLOY_FULL_SBER_CUTOVER.md` — RU/EN step headers  
3. `OFFLINE_SBER_READY_PACK.md`, `SBER_PLATFORM_IMPLEMENTATION_PLAN.md`  
4. `HABR_PART2_ARTICLE_PLAN` — EN abstract  
5. Historical `docs/0x_*.md` — existing bilingual campaign (partial)

## 5. Refactoring (this pass)

| Change | Why |
|---|---|
| README state refresh | Truth vs 2026-08-30 debt text |
| ADR bilingual normalize | Canon decisions must be dual-lang |
| Sber index status table | Single entry point |
| Audit artifact | Traceable strict check |
| `.gitignore` firebase-debug if missing | Hygiene |

🇬🇧 No big-bang code split of `main.py` this pass (risk on live Jetson). Gateway already modular enough for providers.  
🇷🇺 Крупный split `main.py` не делаем в этом проходе (риск live Jetson).

## 6. Recommendations / Рекомендации

1. 🇬🇧 Enable GitHub branch protection on `main` (PR or signed commits).  
   🇷🇺 Включить branch protection на `main`.
2. 🇬🇧 Tag release `v1.7.0-sber-era` after README update.  
   🇷🇺 Тег `v1.7.0-sber-era` после README.
3. 🇬🇧 Owner: Cloud.ru Object Storage tenant_id → S3 L2.  
   🇷🇺 Владелец: tenant_id → S3 L2.
4. 🇬🇧 Continue bilingual backlog in small PRs (1–3 files).  
   🇷🇺 Двуязычность — малыми PR по 1–3 файла.
5. 🇬🇧 Close or refresh stale GitHub issues #1–#5.  
   🇷🇺 Закрыть/обновить stale issues.

## 7. Verdict / Вердикт

| Area | Grade |
|---|---|
| Sber runtime cutover | **A** (live) |
| Sber code/tests | **A-** |
| Git remotes | **A** |
| GitHub hygiene | **B-** (no protection, stale README/issues) |
| Docs bilingual project-wide | **D+** (legacy debt) |
| Docs bilingual Sber canon (after this pass) | **B** (ADRs + index fixed; large plans remain) |

🇬🇧 **Overall:** production Sber path is real; documentation bilingualism is the main remaining quality debt.  
🇷🇺 **Итог:** боевой Sber-путь реален; главный долг качества — двуязычность документации.
