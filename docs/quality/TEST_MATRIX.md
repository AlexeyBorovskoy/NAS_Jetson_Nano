# Матрица тестов / Test Matrix: NAS_Jetson_Nano

**Version:** 1.0  
**Date:** 2026-06-27

---

## Справочник ID тестов / Test ID Reference

🇷🇺 Идентификатор, категория, название теста, скрипт/инструмент, автоматизация и приоритет — по каждому тесту.

🇬🇧 Identifier, category, test name, script/tool, automation, and priority — per test.

| ID | Категория / Category | Название теста / Test Name | Скрипт / Инструмент / Script / Tool | Автоматизация / Automated | Приоритет / Priority |
|---|---|---|---|---|---|
| T1.1 | Static | ShellCheck scripts/ | shellcheck | CI | HIGH |
| T1.2 | Static | Compose validate all | docker compose config | CI | HIGH |
| T1.3 | Static | Secrets scan | gitleaks / check_no_secrets.sh | CI | CRITICAL |
| T1.4 | Static | Trivy FS scan | trivy fs | CI | HIGH |
| T1.5 | Static | actionlint workflows | actionlint | CI | MEDIUM |
| T2.1 | Network | Ping Jetson LAN | connectivity_check.sh | Manual | HIGH |
| T2.2 | Network | Port check Jetson | port_check.sh | Manual | HIGH |
| T2.3 | Network | VPS proxy check | connectivity_check.sh | Manual | HIGH |
| T2.4 | Network | DNS resolution | connectivity_check.sh | Manual | LOW |
| T3.1 | Service | Docker containers up | docker_healthcheck.sh | Manual | CRITICAL |
| T3.2 | Service | Nextcloud status.php | nextcloud_smoke.sh | Manual | HIGH |
| T3.3 | Service | Immich ping | immich_smoke.sh | Manual | HIGH |
| T3.4 | Service | USB watchdog timer | systemctl is-active | Manual | HIGH |
| T3.5 | Service | Beszel agent | systemctl is-active | Manual | MEDIUM |
| T4.1 | Storage | Mount check | mount_check.sh | Manual | CRITICAL |
| T4.2 | Storage | SMART health | smart_check.sh | Manual | HIGH |
| T4.3 | Storage | Disk usage < 90% | mount_check.sh | Manual | HIGH |
| T4.4 | Storage | I/O performance | fio_quick_test.sh | Manual | MEDIUM |
| T5.1 | Backup | DB dump exists | restore_test.sh / scripts | Manual | HIGH |
| T5.2 | Backup | Dump non-empty | restore_test.sh | Manual | HIGH |
| T5.3 | Backup | rsync dry-run | restore_test.sh | Manual | MEDIUM |
| T5.4 | Backup | Restore + diff | restore_test.sh | Manual | HIGH |
| T6.1 | Android | Immich login | Manual | Manual | HIGH |
| T6.2 | Android | Nextcloud HTTPS login | Manual | Manual | HIGH |
| T6.3 | Android | DAVx5 sync | Manual | Manual | MEDIUM |
| T6.4 | Android | Immich backup queue | Manual | Manual | MEDIUM |
| T6.5 | Android | ADB device check | adb_readonly_check.sh | Manual | LOW |
| T7.1 | Load | k6 smoke 5VU/2min | nextcloud-smoke.js | Manual | MEDIUM |
| T7.2 | Load | RAM during load | docker stats | Manual | MEDIUM |
| T8.1 | Security | No secrets in git | check_no_secrets.sh | CI | CRITICAL |
| T8.2 | Security | set -euo pipefail | grep audit | Manual | HIGH |
| T8.3 | Security | No hardcoded creds | grep audit | Manual | HIGH |
| T8.4 | Security | Trivy CRITICAL CVEs | trivy | CI | HIGH |

---

## Покрытие по компонентам / Coverage by Component

🇷🇺 Какие тесты покрывают каждый компонент, по категориям («--» значит покрытия в этой категории нет).

🇬🇧 Which tests cover each component, by category (“--” means no coverage in that category).

| Компонент / Component | Static | Network | Service | Storage | Backup | Android | Load | Security |
|---|---|---|---|---|---|---|---|---|
| Nextcloud | T1.2 | T2.2 | T3.2 | T4.1 | T5.1 | T6.2 | T7.1 | T1.3 |
| Immich | T1.2 | T2.2 | T3.3 | T4.1 | T5.1 | T6.1 | -- | T1.3 |
| USB SSD | -- | -- | T3.4 | T4.1-4.4 | -- | -- | -- | -- |
| Docker | T1.2 | -- | T3.1 | -- | -- | -- | -- | T1.4 |
| VPS proxy | -- | T2.3 | -- | -- | -- | -- | -- | -- |
| Shell scripts | T1.1 | -- | -- | -- | -- | -- | -- | T8.2-3 |
| Backup | -- | -- | -- | -- | T5.1-4 | -- | -- | -- |
| Android apps | -- | -- | -- | -- | -- | T6.1-5 | -- | -- |

---

## Матрица рисков / Risk Matrix

🇷🇺 Риск, вероятность, влияние и способ снижения — по каждой строке.

🇬🇧 Risk, likelihood, impact, and mitigation — per row.

| Риск / Risk | Вероятность / Likelihood | Влияние / Impact | Снижение риска / Mitigation |
|---|---|---|---|
| USB SSD error -71 | HIGH | CRITICAL | watchdog + preboot cycle |
| microSD wear (OS disk) | MEDIUM | HIGH | monitoring, backup |
| RAM OOM on Jetson | MEDIUM | HIGH | mem_limit in compose, ML disabled |
| Jetson thermal throttle | LOW | MEDIUM | Netdata thermal alerts |
| VPS tunnel down | MEDIUM | HIGH | autossh auto-reconnect |
| DB corruption on power loss | LOW | CRITICAL | DB healthchecks, regular dumps |
| Docker image security vuln | MEDIUM | MEDIUM | Trivy in CI |

---

## Требуемые тестовые окружения / Test Environments Required

🇷🇺 Какое окружение нужно для группы тестов — Jetson, VPS, Android-устройство.

🇬🇧 Which environment is required for each test group — Jetson, VPS, Android device.

| ID теста / Test ID | Нужен Jetson / Requires Jetson | Нужен VPS / Requires VPS | Нужен Android / Requires Android |
|---|---|---|---|
| T1.x | No (CI) | No | No |
| T2.x | Yes | Yes (T2.3) | No |
| T3.x | Yes | No | No |
| T4.x | Yes | No | No |
| T5.x | Yes | No | No |
| T6.x | No | No | Yes |
| T7.x | Yes | No | No |
| T8.x | No (CI) | No | No |
