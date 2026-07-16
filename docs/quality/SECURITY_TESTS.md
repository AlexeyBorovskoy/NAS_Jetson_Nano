# Тесты безопасности / Security Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Security Scope

This is a home cloud security audit. Scope:
- Shell script hardening
- Secret management (no credentials in git)
- Docker compose security configuration
- Network exposure audit
- Dependency vulnerability scan (Trivy)

Out of scope:
- Penetration testing
- WiFi security audit
- Router/firewall configuration
- Amnezia VPN clients (do not touch per project rules)

---

## Static Security Checks (CI)

### 1. Secrets Scan

```bash
# Run locally
./scripts/security/check_no_secrets.sh

# In CI: .github/workflows/quality-checks.yml (gitleaks job)
```

Checks for: API keys, passwords, tokens, private keys in git-tracked files.
Excludes: .env.example (placeholder values), .gitignore, check_no_secrets.sh itself.

### 2. ShellCheck

```bash
find scripts/ -name "*.sh" | xargs shellcheck --severity=warning --shell=bash
```

Key checks:
- SC2086: Unquoted variables (word splitting)
- SC2046: Unquoted command substitution
- SC2034: Unused variables
- SC2155: Declare and assign separately

### 3. Trivy Filesystem Scan

```bash
# Scan entire repository
trivy fs . --severity HIGH,CRITICAL

# Docker images
trivy image nextcloud:apache
trivy image tensorchord/pgvecto-rs:pg16-v0.3.0
```

---

## Shell Script Security Checklist

For each script in scripts/:

- [ ] `#!/usr/bin/env bash` or `#!/bin/bash`
- [ ] `set -euo pipefail` (or at minimum `set -eu`)
- [ ] No hardcoded passwords or tokens
- [ ] Variables quoted: `"${VAR}"` not `$VAR`
- [ ] Temp files created with `mktemp`, not fixed `/tmp/name`
- [ ] `curl` uses `--max-time`
- [ ] Dependency checks before use (command -v tool)
- [ ] Input validation for script arguments
- [ ] No world-writable files created
- [ ] Sensitive data not logged to stdout

---

## Docker Compose Security Checklist

- [ ] All secrets via `${VAR}` from .env (no hardcoded values)
- [ ] All services have `restart:` policy
- [ ] Heavy services have `mem_limit:`
- [ ] Services with healthchecks have `healthcheck:`
- [ ] No containers running as root unnecessarily
- [ ] docker.sock mounted read-only where possible
- [ ] No privileged mode except where required (Netdata needs SYS_PTRACE)

---

## Network Security

- [ ] Services not directly exposed to internet (only via VPS proxy)
- [ ] VPS nginx does not forward admin/setup endpoints
- [ ] Self-signed HTTPS for external access (8443, 2443, 9443)
- [ ] SSH key-based auth only (no password auth from internet)
- [ ] Amnezia VPN not exposed (do not touch)

---

## Findings Log

Document all findings here:

| Date | File | Line | Severity | Issue | Fixed? |
|---|---|---|---|---|---|
| 2026-06-27 | usb_recovery_watchdog.sh | 11 | MEDIUM | Missing `-e` in `set -uo pipefail` | YES |
| 2026-06-27 | nas_jetson_nano-daily-report.sh | 3 | MEDIUM | Only `set -u`, missing `-eo` | KNOWN LIMITATION (complex heredoc) |
| 2026-06-27 | install_usb_watchdog.sh | 65 | LOW | REMOTE_ENV uses predictable /tmp path | LOW RISK (local only) |
| 2026-06-27 | nas_jetson_nano-daily-report.sh | 106-107 | LOW | Unsafe /tmp file in Beszel SSH section | LOW RISK (non-sensitive data) |
| 2026-06-27 | immich compose | 74 | LOW | immich-microservices has no mem_limit | FIXED |

---

## Non-Goals (Explicitly Out of Scope)

1. No nmap or aggressive port scanning
2. No brute-force testing of any credentials
3. No exploitation of found vulnerabilities
4. No ADB data extraction from Android devices
5. No interference with Amnezia VPN (would disconnect ~25 VPN clients)
