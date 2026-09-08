# Project Audit

> **Mode:** AUDIT ONLY (GLOBAL_CODE_QUALITY.md §44). No production code changed in this pass.  
> **Date:** 2026-09-08  
> **Canon overrides:** `AGENTS.md`, ADRs 0003/0005/0007/0008/0009 (stricter than generic prompt).  
> **RU / EN:** findings in bilingual tables below.

## Executive Summary

🇬🇧 NAS_Jetson_Nano is a **family home cloud** on Jetson Nano 4 GB: Nextcloud + Immich + Samba + Talk bot + LLM Gateway. Sber-era cutover (2026-09-08) is **live**: GigaChat-2 default, Immich→HDD L1, giga-balance timer. Architecture is sound (single outbound LLM door, LAN/VPN-only).

🇷🇺 Семейное облако на Nano 4 ГБ. Sber-cutover **в бою**. Архитектура шлюза здравая.

**Overall grade:** runtime **B+** · code maintainability **C+** · tests **D+** · security (LAN-perimeter) **B-** · bilingual docs **D+**.

Do **not** big-bang rewrite. Protect tests first, then P0/P1 (empty dumps, CORS, pin deps).

## Project Inventory

| Area | Stack |
|---|---|
| Purpose | Family SoR: photos/files/calendar at home |
| Languages | Python 3.12 (containers), Bash, some host Python 3.6 |
| Frameworks | FastAPI, Pydantic, httpx, openai SDK, python-jose |
| DB | PostgreSQL (Nextcloud + Immich), Redis |
| External APIs | GigaChat PERS, DeepSeek, Cloud.ru FM, Nextcloud OCS/Talk |
| Docker | 13 containers, split compose, mem_limit on most |
| CI | GitHub Actions: compose validate, shellcheck, secrets-check, quality-checks |
| Systemd | backup, USB watchdog, Immich HDD copy, giga-balance |
| Hardware | Jetson Nano 4 GB, USB SSD, HDD 2 TB NTFS, VPS reverse SSH |
| GPU/CUDA | Unused in prod (CUDA 10.2 vs Immich ML 11/12) |
| Tests | `tests/llm_gateway/test_sber_routing.py`, `tests/unit/test_talk_alert_selftest.py`, shell tests |

**God module:** `services/llm-gateway/app/main.py` (~1019 lines) — redaction + budget + OAuth + 4 providers + images.

## Architecture

```text
Family phones (VPN)
        ↓
VPS nginx + Amnezia  (ports 22/443/40568 only)
        ↓ reverse SSH
Jetson
  Nextcloud / Immich / Samba     ← SoR (SSD)
  nasa-api :8099 JWT             ← local orchestration
  llm-gateway :8090              ← ONLY outbound LLM door
        ↓
  GigaChat PERS | DeepSeek | Cloud.ru FM
```

| Component | In | Out | Failure | Criticality |
|---|---|---|---|---|
| Immich+PG | phones | SSD library | disk/USB | **P0 data** |
| Nextcloud | DAV | SSD | disk | P0 |
| LLM Gateway | Talk/API | cloud LLM | API 402/429 | P1 UX |
| nasa-api | JWT | docker/scripts | auth/CORS | P1 |
| Vostro restic | dumps pull | /srv | tunnel race | P2 emergency |
| Cloud.ru S3 | planned | — | tenant_id | P2 |

**Coupling:** Talk bot → gateway HTTP; actions router → docker CLI. Acceptable for 4 GB host.

## Baseline

See [`BASELINE.md`](BASELINE.md). Device 2026-09-08: 13 containers, RAM ~2.2/3.9 GB (older 22.08), Immich 13G SSD=HDD, gateway chat 200 gigachat.

## Critical Findings

See FINDINGS **F-01** (backup empty gzip on boot), **F-02** (single SSD was P0 — **mitigated L1** 2026-09-08).

## High / Medium / Low

See [`FINDINGS.md`](FINDINGS.md).

## Resource Leaks

| Type | Assessment |
|---|---|
| Memory | Usage JSON file bounded; Talk poll loop except-continue — watch |
| FD | httpx per-call (no shared client) — extra sockets, not unbounded |
| DB | dumps via docker exec; no app connection pool in gateway |
| Disk | dump rotation keep-last-7; jms583 logrotate still TD-06 |
| GPU | N/A prod |
| Queue | Giga serialized by lock (good); no unbounded queue |

## Security

- Secrets gitignored (`gigachat/`, `.env`); scanner + push protection on GitHub.
- CORS `allow_origins=["*"]` on :8099 (LAN + VPN only — still HIGH if JWT stolen).
- JWT secret historically in example — rotate separately.
- Redaction is word-list not NER (documented).
- No Amnezia changes recommended.

## Dependencies

| Dep | Note | Class |
|---|---|---|
| nasa-api unpinned `>=` | TD-04 | REQUIRES TESTING to pin |
| openai 1.82 / fastapi 0.115 gateway | pinned | SAFE minor |
| Host Ubuntu 18.04 / Py 3.6 | EOL JetPack ceiling | DO NOT UPDATE YET (board) |
| Immich/NC images floating tags | TD-05 | REQUIRES TESTING |

## Tests

Insufficient vs GLOBAL_CODE_QUALITY §12. Critical paths without tests: `backup_databases.sh` empty-dump, JWT auth, actions whitelist, PII redaction golden tests (partial in docs), Talk poll.

## Performance

Not profiled this pass. Bottleneck is RAM 4 GB + USB SSD, not CPU of gateway.

## Reliability

Healthchecks on compose; USB watchdog; dump timer **false SUCCESS** on cold postgres. Giga failover to DeepSeek exists.

## Observability

Beszel, Kuma, Netdata, Talk alerts, daily Telegram. Gateway: `/health`, `/v1/usage`, `/v1/provider/gigachat/balance`. No traces. No structured request-id on gateway.

## Technical Debt

Prior register `TECHNICAL_DEBT.md` (2026-08-30): TD-02 photos **partially closed** (L1 HDD). TD-01 rename Part B still open. TD-08 CORS still open. TD-14 tests still open.

## Recommended Roadmap

See [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md). **No code in this audit pass.**
