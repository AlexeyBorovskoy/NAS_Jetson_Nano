# План тестирования / Test Plan: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27  
**Author:** AlexeyBorovskoy  
**Scope:** Jetson Nano 4GB home cloud — Nextcloud, Immich, Samba, LLM Gateway, USB SSD reliability

---

## 1. Objectives

1. Validate that all services are reachable and functional after deploy or hardware event.
2. Detect shell script vulnerabilities (missing error handling, unsafe temp files, hardcoded secrets).
3. Measure baseline I/O performance of the USB SSD (RTL9210B-CG).
4. Confirm backup and restore procedures work without data loss.
5. Verify Android client connectivity to Nextcloud and Immich.
6. Confirm USB watchdog and pre-boot cycle behave correctly on failure injection.

---

## 2. Scope

| Area | In Scope | Out of Scope |
|---|---|---|
| Docker services | Yes — all 13 containers | Docker internals, image builds |
| USB SSD reliability | Yes — watchdog, SMART, mount | Physical hardware replacement |
| Network | LAN + VPS reverse proxy | ISP routing, Amnezia VPN clients |
| Backup/restore | DB dumps, rsync dry-run | Full disaster recovery |
| Android | Immich, Nextcloud, DAVx5 | MIUI system internals |
| Security | Secret scan, ShellCheck, Trivy | Penetration testing |
| Load | Light smoke test (k6, 5 VU/2min) | Stress / soak testing |

---

## 3. Test Environments

### 3.1 Primary: Jetson Nano (192.168.0.50)
- OS: Ubuntu 18.04 LTS (L4T r32.7.6)
- Docker: 24.x
- Storage: USB SSD /dev/sda1 -> /mnt/storage (229G, ext4)
- RAM: 4GB LPDDR4 (shared CPU/GPU)

### 3.2 VPS (193.8.215.130)
- Location: Vienna
- Role: Reverse proxy + autossh tunnel endpoint
- Services: nginx -> :8080 (Nextcloud), :2283 (Immich), :8090 (LLM Gateway)

### 3.3 CI Environment
- GitHub Actions: ubuntu-latest
- Tools: shellcheck, docker compose validate, gitleaks, trivy, actionlint

---

## 4. Test Categories

### T1: Static Analysis (CI)
- ShellCheck on all scripts/
- docker compose config --quiet on all compose files
- Gitleaks secrets scan
- Trivy filesystem scan (vuln + secret + misconfig)
- actionlint on .github/workflows/

### T2: Network Connectivity
- Ping Jetson from LAN
- Port check: 22, 8080, 2283, 8090, 8099, 19999, 3001
- VPS reverse proxy HTTP check: 8080, 2283, 8090
- DNS resolution of Jetson hostname

### T3: Service Smoke Tests
- Nextcloud: /status.php -> HTTP 200
- Immich: /api/server/ping -> HTTP 200
- LLM Gateway: /health -> HTTP 200
- Beszel Agent: systemctl is-active
- nas_jetson_nano-usb-watchdog.timer: active

### T4: Storage
- mountpoint -q /mnt/storage
- lsblk shows /dev/sda
- df -h shows < 90% usage
- SMART: smartctl -H /dev/sda returns PASSED
- Write/read performance > 50 MB/s (USB 3.0 SSD expected ~300 MB/s)

### T5: Backup / Restore
- DB dump created for nextcloud and immich
- Dump file size > 0
- rsync dry-run to backup target succeeds
- Restore to temp dir + diff check

### T6: Android Client
- Immich app can login (manual)
- Nextcloud app can login via HTTPS (manual)
- DAVx5 contacts sync configured (manual)
- Backup queue progress visible in Immich

### T7: Load Test
- k6 smoke: 5 VU / 2 min on /status.php
- Acceptance: p95 < 2s, error rate < 1%
- Resource check: RAM not exhausted during test

### T8: Security
- No secrets in git-tracked files
- All scripts have set -euo pipefail
- No hardcoded IPs/passwords in scripts (config from env only)
- Trivy no CRITICAL CVEs in compose images (informational)

---

## 5. Acceptance Criteria

| Category | Pass Condition |
|---|---|
| Static (CI) | ShellCheck 0 errors; compose valid; no secrets in git |
| Network | All local ports reachable, VPS proxy returns 200 |
| Services | All 13 containers running, no unhealthy |
| Storage | Mounted, < 90% used, SMART PASSED |
| Backup | Both DB dumps exist and non-empty |
| Android | Immich + Nextcloud login successful |
| Load | p95 < 2s, errors < 1% at 5 VU/2min |

---

## 6. Known Limitations

- Jetson Nano L4T 4.9 kernel: limited SMART passthrough via RTL9210B-CG USB bridge.
- USB SSD (RTL9210B-CG) is unreliable hardware; watchdog mitigates but does not eliminate risk.
- RAM is shared CPU/GPU; heavy photo ML would OOM (ML disabled).
- No off-site backup configured yet (restic to VPS is planned).
- Load test is a smoke test only; not a capacity or stress test.
- Android tests require manual execution (no ADB automation per policy).

---

## 7. Test Execution Schedule

| Phase | When | Who |
|---|---|---|
| Static (CI) | Every push/PR | GitHub Actions |
| Network + Service | After each deploy | Admin (manual or script) |
| Storage + SMART | Weekly | systemd timer or manual |
| Backup/Restore | Weekly | nas_jetson_nano-backup.timer |
| Android | After app updates | Admin (manual) |
| Load test | After major changes | Admin (manual, k6) |

---

## 8. References

- `tests/network/connectivity_check.sh` -- network connectivity
- `tests/service/docker_healthcheck.sh` -- container health
- `tests/storage/smart_check.sh` -- SMART read-only check
- `tests/backup/restore_test.sh` -- backup validation
- `tests/android/adb_readonly_check.sh` -- Android readonly check
- `tests/load/nextcloud-smoke.js` -- k6 load script
- `docs/quality/RELEASE_ACCEPTANCE_CHECKLIST.md` -- go/no-go checklist
- `docs/12_BACKUP_RESTORE.md` -- backup runbook
