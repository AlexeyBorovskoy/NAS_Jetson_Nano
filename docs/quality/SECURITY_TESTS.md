# Тесты безопасности / Security Tests: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Область охвата по безопасности / Security Scope

🇷🇺 Это аудит безопасности домашнего облака. Охват:
- Усиление shell-скриптов
- Управление секретами (нет учётных данных в git)
- Конфигурация безопасности docker compose
- Аудит сетевой открытости
- Сканирование уязвимостей зависимостей (Trivy)

Вне охвата:
- Пентест
- Аудит безопасности Wi-Fi
- Конфигурация роутера/файрвола
- Клиенты Amnezia VPN (не трогать по правилам проекта)

🇬🇧 This is a home cloud security audit. Scope:
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

## Статические проверки безопасности (CI) / Static Security Checks (CI)

### 1. Сканирование секретов / Secrets Scan

```bash
# Run locally
./scripts/security/check_no_secrets.sh

# In CI: .github/workflows/quality-checks.yml (gitleaks job)
```

🇷🇺 Проверяет наличие в отслеживаемых git файлах: API-ключей, паролей, токенов, приватных ключей.
Исключения: .env.example (плейсхолдер-значения), .gitignore, сам check_no_secrets.sh.

🇬🇧 Checks for: API keys, passwords, tokens, private keys in git-tracked files.
Excludes: .env.example (placeholder values), .gitignore, check_no_secrets.sh itself.

### 2. ShellCheck

```bash
find scripts/ -name "*.sh" | xargs shellcheck --severity=warning --shell=bash
```

🇷🇺 Ключевые проверки:
- SC2086: незакавыченные переменные (расщепление слов)
- SC2046: незакавыченная подстановка команд
- SC2034: неиспользуемые переменные
- SC2155: объявление и присвоение раздельно

🇬🇧 Key checks:
- SC2086: Unquoted variables (word splitting)
- SC2046: Unquoted command substitution
- SC2034: Unused variables
- SC2155: Declare and assign separately

### 3. Сканирование файловой системы Trivy / Trivy Filesystem Scan

```bash
# Scan entire repository
trivy fs . --severity HIGH,CRITICAL

# Docker images
trivy image nextcloud:apache
trivy image tensorchord/pgvecto-rs:pg16-v0.3.0
```

---

## Чеклист безопасности shell-скриптов / Shell Script Security Checklist

🇷🇺 Для каждого скрипта в scripts/:

🇬🇧 For each script in scripts/:

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

## Чеклист безопасности Docker Compose / Docker Compose Security Checklist

- [ ] All secrets via `${VAR}` from .env (no hardcoded values)
- [ ] All services have `restart:` policy
- [ ] Heavy services have `mem_limit:`
- [ ] Services with healthchecks have `healthcheck:`
- [ ] No containers running as root unnecessarily
- [ ] docker.sock mounted read-only where possible
- [ ] No privileged mode except where required (Netdata needs SYS_PTRACE)

---

## Сетевая безопасность / Network Security

- [ ] Services not directly exposed to internet (only via VPS proxy)
- [ ] VPS nginx does not forward admin/setup endpoints
- [ ] Self-signed HTTPS for external access (8443, 2443, 9443)
- [ ] SSH key-based auth only (no password auth from internet)
- [ ] Amnezia VPN not exposed (do not touch)

---

## Журнал находок / Findings Log

🇷🇺 Здесь документируются все находки.

🇬🇧 Document all findings here:

| Дата / Date | Файл / File | Строка / Line | Серьёзность / Severity | Проблема / Issue | Исправлено? / Fixed? |
|---|---|---|---|---|---|
| 2026-06-27 | usb_recovery_watchdog.sh | 11 | MEDIUM | Missing `-e` in `set -uo pipefail` | YES |
| 2026-06-27 | nas_jetson_nano-daily-report.sh | 3 | MEDIUM | Only `set -u`, missing `-eo` | KNOWN LIMITATION (complex heredoc) |
| 2026-06-27 | install_usb_watchdog.sh | 65 | LOW | REMOTE_ENV uses predictable /tmp path | LOW RISK (local only) |
| 2026-06-27 | nas_jetson_nano-daily-report.sh | 106-107 | LOW | Unsafe /tmp file in Beszel SSH section | LOW RISK (non-sensitive data) |
| 2026-06-27 | immich compose | 74 | LOW | immich-microservices has no mem_limit | FIXED |

---

## Не входит в задачи (явно вне охвата) / Non-Goals (Explicitly Out of Scope)

🇷🇺

1. Никакого nmap или агрессивного сканирования портов
2. Никакого перебора (brute-force) учётных данных
3. Никакой эксплуатации найденных уязвимостей
4. Никакого извлечения данных с Android-устройств через ADB
5. Никакого вмешательства в Amnezia VPN (отключило бы ~25 VPN-клиентов)

🇬🇧

1. No nmap or aggressive port scanning
2. No brute-force testing of any credentials
3. No exploitation of found vulnerabilities
4. No ADB data extraction from Android devices
5. No interference with Amnezia VPN (would disconnect ~25 VPN clients)
