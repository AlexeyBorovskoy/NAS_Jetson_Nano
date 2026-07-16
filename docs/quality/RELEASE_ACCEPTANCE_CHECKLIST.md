# Чеклист приёмки релиза / Release Acceptance Checklist: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27  
**Use:** Complete before tagging a release or declaring system operational.

---

## Pre-Release: Code Quality

- [ ] `git status` shows no uncommitted changes
- [ ] `./scripts/security/check_no_secrets.sh` passes (0 findings)
- [ ] GitHub Actions CI passes: shellcheck, compose-validate, secrets-check, quality-checks
- [ ] ShellCheck reports 0 errors on all scripts/
- [ ] All shell scripts have `#!/usr/bin/env bash` and `set -euo pipefail`
- [ ] CHANGELOG.md updated with new version entry

---

## Pre-Release: Infrastructure

- [ ] SSH to Jetson succeeds: `ssh admin@192.168.0.50 hostname`
- [ ] `git pull --ff-only` on Jetson: no conflicts
- [ ] `storage_preflight.sh` passes: 0 errors, /mnt/storage mounted
- [ ] `/dev/sda` is a block device (not mmcblk)
- [ ] `df -h /mnt/storage` shows < 85% used

---

## Pre-Release: Docker Services

- [ ] All 13 containers are in running state
- [ ] No containers in unhealthy state (`docker ps --filter health=unhealthy`)
- [ ] No containers with restart count > 5 in last 24h
- [ ] `docker compose config --quiet` passes for all compose files

---

## Pre-Release: Service Endpoints

- [ ] Nextcloud: `curl -sf http://192.168.0.50:8080/status.php` returns HTTP 200 with `{"installed":true}`
- [ ] Immich: `curl -sf http://192.168.0.50:2283/api/server/ping` returns HTTP 200
- [ ] LLM Gateway: `curl -sf http://192.168.0.50:8090/health` returns HTTP 200
- [ ] VPS Nextcloud proxy: `curl -sf http://193.8.215.130:8080/status.php` returns HTTP 200
- [ ] VPS Immich proxy: `curl -sf http://193.8.215.130:2283/api/server/ping` returns HTTP 200

---

## Pre-Release: Systemd Services

- [ ] `systemctl is-active nas_jetson_nano-usb-watchdog.timer` = active
- [ ] `systemctl is-active nas_jetson_nano-usb-monitor.service` = active
- [ ] `systemctl is-active nas_jetson_nano-tunnel.service` = active
- [ ] `systemctl is-active docker` = active
- [ ] `systemctl is-active beszel-agent` = active

---

## Pre-Release: Backup

- [ ] At least one Nextcloud DB dump exists in /mnt/storage/backups/database-dumps/ (< 7 days old)
- [ ] At least one Immich DB dump exists (< 7 days old)
- [ ] DB dump files are > 0 bytes

---

## Pre-Release: Security

- [ ] `config/.env` is in .gitignore and NOT tracked by git
- [ ] `config/secrets.json` is NOT tracked by git
- [ ] No `CHANGE_ME` or default passwords in deployed config (check Nextcloud admin panel)
- [ ] SSH key auth works (password auth disabled or tested separately)
- [ ] Telegram notifications working (send test via usb_error_monitor)

---

## Go / No-Go Decision

| Area | Status | Blocker? |
|---|---|---|
| CI passes | / | YES |
| Storage mounted | / | YES |
| All containers up | / | YES |
| Nextcloud reachable | / | YES |
| Immich reachable | / | YES |
| USB watchdog active | / | YES |
| DB backup current | / | NO (warn only) |
| VPS proxy working | / | NO (warn only) |

**Decision:** GO / NO-GO  
**Signed off by:** _________________  
**Date:** _________________

---

## Post-Release

- [ ] Git tag created: `git tag -a vX.Y.Z -m "description"`
- [ ] Tag pushed: `git push origin vX.Y.Z`
- [ ] GitHub release created: `gh release create vX.Y.Z`
- [ ] CLAUDE.md operational status table updated
- [ ] Memory checkpoint file created in memory/
