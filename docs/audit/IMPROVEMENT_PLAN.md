# Improvement plan / План работ

> GLOBAL_CODE_QUALITY.md §41 · 2026-09-08  
> 🇬🇧 Small atomic diffs. No mix of bugfix+refactor+optimize. AGENTS.md safety wins.  
> 🇷🇺 Малые атомарные diff. Safety AGENTS.md важнее «красивого» рефакторинга.

## P0 — blocking / critical

| ID | Work | Tests first | Risk |
|---|---|---|---|
| F-01/F-03 | Fail-closed dumps: `pg_isready` wait, min size, `gzip -t`, systemd After/Pre | shell fixture empty gzip | LOW — **git done 2026-09-08**; install unit on Jetson still pending |
| F-02 L2 | Cloud.ru S3 when owner gives tenant_id — dumps only first | dry-run restic | MEDIUM |

## P1 — high

| ID | Work |
|---|---|
| F-04 | CORS origins from env (not `*`) |
| F-05 | Rotate JWT if ever in git; rotate `.env.bak` on device (owner) |
| F-07 | Device Part B rename — **maintenance window only** |
| F-06 | Explicit EOL accept note in README (already implied) — no OS upgrade on Nano |

## P2 — medium

| ID | Work |
|---|---|
| F-11 | Tests: dump script, redaction golden, JWT login mock, actions whitelist |
| F-12 | Pin nasa-api `requirements.txt` `==` |
| F-08 | Split gateway: `redact.py`, `providers/*.py`, keep `main.py` thin — **after** tests |
| F-10 | Log Talk poll exceptions at ERROR with command id |
| F-14 | `X-Request-ID` on gateway |

## P3 — optimization / debt

| ID | Work |
|---|---|
| F-09 | Shared `httpx.Client` in gateway (measure first) |
| F-15 | Pin image digests |
| F-16 | logrotate jms583 |
| F-17 | Bilingual 1–3 files per PR |
| F-18 | GitHub `main` protection + close stale issues |
| F-19 | Quarantine or delete `stage1.yml` after grep |

## Explicitly NOT doing

- Rewrite gateway from scratch  
- Major dependency bumps  
- Immich ML on Nano CUDA 10.2  
- Amnezia / VPS firewall experiments  
- Mass delete “unused” scripts  
- Load/soak until P0 dump fix exists (otherwise metrics lie)

## Sequence (next implementation sprint)

```text
1. Tests for empty dump + min size
2. Patch backup_databases.sh + timer
3. pytest llm-gateway (already 5)
4. CORS env allowlist
5. Pin nasa-api deps
6. Then optional gateway split
```

Each step: tests → lint/preflight → commit → no mix.
