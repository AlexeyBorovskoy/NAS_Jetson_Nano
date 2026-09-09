# Findings registry / Реестр проблем

> Audit 2026-09-08 · GLOBAL_CODE_QUALITY.md · AUDIT ONLY  
> Status: `OPEN` / `MITIGATED` / `ACCEPTED`

| ID | Severity | Category | Location | Problem | Risk | Status |
| -- | -------- | -------- | -------- | ------- | ---- | ------ |
| F-01 | CRITICAL | Data integrity | `scripts/backup/backup_databases.sh` `dump_postgres` + `nasa-backup.timer` | Dump can write ~20-byte gzip when Postgres not ready; timer still success. Evidence: 2026-09-08 04:04 empty dumps; good dumps after manual run 09:13. No min-size/`gzip -t` fail-closed. | False sense of backup; restore of empty file | **CLOSED 2026-09-09** (git + **device**: `nasa-backup.service` ExecStartPre; live dump immich ~20M + nextcloud ~2.7M; `test_dump_validate` PASS) |
| F-02 | CRITICAL | Backup | Immich library single copy | Was P0 TD-02. **L1 HDD copy 13G=13G + timer 2026-09-08**. L2 S3 still blocked. House fire still single-site. | Photo loss if house lost | MITIGATED (L1) / OPEN (L2) |
| F-03 | HIGH | Reliability | `nasa-backup.timer` vs Docker start | Boot race: timer at ~03:00 / Persistent=true fires before PG listen | Empty dumps F-01 | **CLOSED 2026-09-09** with F-01 device install |
| F-04 | HIGH | Security | `services/nas_jetson_nano-api/app/main.py` CORS `*` | Any origin if API reachable (VPN/LAN). JWT still required on mutating routes. | CSRF/token use from random origin | OPEN (TD-08) |
| F-05 | HIGH | Security | JWT secret / `.env.bak.*` on device | TD-12 backups of env; historical example secret shape | Disk compromise | OPEN |
| F-06 | HIGH | Platform | Host Ubuntu 18.04 + Py 3.6 EOL | TD-11 JetPack ceiling | Unpatched host CVEs | ACCEPTED until board replace |
| F-07 | HIGH | Deploy | Device layout `~/nasa` vs git names | TD-01 Part B not done | Naive pull/rename break | OPEN |
| F-08 | MEDIUM | Code smell | `llm-gateway/app/main.py` ~1019 lines | God module: OAuth, 4 providers, images, budget | Hard to test/review | OPEN (refactor later) |
| F-09 | MEDIUM | Resources | httpx client per call | Extra TLS handshakes; not a leak | Latency/RAM on 4 GB | OPEN P3 |
| F-10 | MEDIUM | Error handling | Talk bot `except Exception` swallow in poll loop | Loop survives; errors may hide | Silent command fail | OPEN |
| F-11 | MEDIUM | Tests | Only 2 Python test modules | No dump-size test, weak API coverage | Regressions return | OPEN (TD-14) |
| F-12 | MEDIUM | Security | nasa-api deps unpinned | TD-04 | Supply-chain drift | OPEN |
| F-13 | MEDIUM | Backup | S3 L2 AccessDenied / no tenant_id | Off-site canon blocked | No true off-site photos | OPEN |
| F-14 | MEDIUM | Observability | Gateway no request-id / structured logs | Hard to correlate Talk→Giga | Ops | OPEN |
| F-15 | LOW | Docker | Floating image tags, dangling images | TD-05 | Surprise upgrades | OPEN |
| F-16 | LOW | Logging | jms583 log no rotate | TD-06 | Disk growth | OPEN |
| F-17 | LOW | Docs | ~155 docs without 🇷🇺/🇬🇧 pair | Project bilingual rule | Onboarding | OPEN |
| F-18 | LOW | GitHub | No branch protection; 6 stale issues | Accidental force-push | Process | OPEN |
| F-19 | LOW | Dead code | `docker-compose.stage1.yml` unused? | TD-13 | Accidental start | OPEN |
| F-20 | INFO | LLM | Redaction ≠ NER; diminutives must be listed | Documented in gateway | PII leak nicknames | ACCEPTED |
| F-21 | INFO | LLM | 1 PERS stream — lock present | Good | Latency under burst | OK |
| F-22 | INFO | GPU | Nano CUDA unused | Commenters Part1 | Not a defect vs ADR-0007 | ACCEPTED |

## Detail cards (CRITICAL / HIGH)

### F-01 Empty dumps

- **Evidence:** 20-byte `*_20260908_040406.sql.gz`; journal pg connection refused; unit exit 0.  
- **Reproduce:** reboot Jetson so Persistent timer fires before `immich_db` ready.  
- **Fix (git 2026-09-08):** `wait_pg_ready`; dump to `.partial`; `gzip -t`; `MIN_DUMP_BYTES=1024`; fail-closed; `tests/backup/test_dump_validate.sh`.  
- **Device 2026-09-09:** `nasa-backup.service` + live dump `*_20260909_133026` (~20M / ~2.7M).  
- **Fix risk:** LOW.

### F-03 Timer race

- Same incident. **Mitigation:** `wait_pg_ready` in script + `ExecStartPre` DB containers running (15×4s). Timer calendar unchanged.

### F-04 CORS *

- **Fix:** `allow_origins` from env list (Nextcloud origin only). **Fix risk:** Talk/web clients if any other origin.

### F-07 Layout drift

- **Fix:** Part B maintenance window only (existing runbook). Not in this audit implement pass.
