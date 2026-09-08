# Baseline metrics / Базовые метрики

> 2026-09-08. Mix of live SSH (Jetson via VPS) and git-tree static counts.  
> Not a lab load test (GLOBAL_CODE_QUALITY §20–21 not run).

| Metric | Before (this audit) | After | Change |
| ------ | -----: | ----: | -----: |
| Containers up | 13 | — | — |
| LLM `/health` provider | gigachat | — | cutover done pre-audit |
| LLM chat HTTP (gigachat ping) | 200 | — | — |
| `prefer_local` | false | — | — |
| Immich SSD | 13G | — | — |
| Immich HDD L1 | 13G | — | — |
| SSD free `/mnt/storage` | ~204G | — | — |
| HDD free `/mnt/hdd2tb` | ~462G | — | — |
| Last good T0 dump | 2026-09-08 09:13 ~20M+2.6M | — | — |
| Empty dump incident | 2026-09-08 04:04 20 B | — | — |
| Vostro restic snapshot | `3922949b` | — | — |
| RAM host (22.08 snapshot) | 2.2 / 3.9 GB | — | not re-sampled |
| Gateway file LOC | ~1019 | — | — |
| Python test modules | 2 | — | — |
| `pytest` sber routing | 5 passed (workstation) | — | — |
| docs `*.md` bilingual flags | ~33 / ~188 | — | — |
| GitHub stars | 0 | — | — |
| Open GitHub issues | 6 | — | — |
| Branch protection | none | — | — |
| CI workflows | 4 | — | — |

🇬🇧 Startup/P95/FD/coverage: **not measured** this pass (no soak, no profiler).  
🇷🇺 Старт/P95/FD/coverage: **не мерили** (нет soak/профайлера).
