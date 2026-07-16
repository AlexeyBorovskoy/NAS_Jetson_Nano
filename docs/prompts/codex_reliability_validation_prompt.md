# Промт для Codex — проведение проверки надёжности NAS_Jetson_Nano

**Проект:** `NAS_Jetson_Nano` / `NAS_Jetson_Nano`
**Дата подготовки промта:** 2026-06-27  
**Назначение:** промт для Codex-агента в VS Code / Cursor.

---

## 1. Как использовать

1. Положи этот файл в проект, например:

```text
docs/quality/CODEX_RELIABILITY_VALIDATION_PROMPT.md
```

2. Открой проект в VS Code / Cursor.
3. Открой чат Codex-агента.
4. Вставь текст из раздела **“Готовый промт”**.
5. Дай Codex выполнить работу поэтапно.
6. После завершения проверь `git diff`.

---

## 2. Готовый промт

```text
Ты работаешь как reliability engineer, DevOps-аудитор, security reviewer и technical writer проекта NAS_Jetson_Nano.

Проект:
NAS_Jetson_Nano / NAS_Jetson_Nano

Идея проекта:
Old Hardware Must Live — домашняя облачная платформа на Jetson Nano первого поколения / Jetson Nano 4GB, старом HDD/SSD, Docker Compose, Nextcloud и Android-клиенте.

Контекст:
Проект готовится к публикации на Hackaday.io, Хабре и других технических площадках. Нужно проверить, насколько решения устойчивы и хорошо обоснованы:
- на уровне сетевой связанности;
- на уровне Docker Compose;
- на уровне кода и скриптов;
- на уровне безопасности;
- на уровне хранилища;
- на уровне backup/restore;
- на уровне Android-клиента;
- на уровне мониторинга.

Главное правило:
Не ломать систему. Не выполнять опасные команды без явного подтверждения. Не форматировать диски. Не удалять данные. Не публиковать секреты и персональные данные.

Работай строго по этапам.

---

# Этап 0. Режим безопасности

Перед любыми действиями зафиксируй ограничения.

Запрещено выполнять без отдельного подтверждения пользователя:

- mkfs
- fdisk
- parted
- dd
- wipefs
- rm -rf
- adb install
- adb shell pm uninstall
- adb shell pm clear
- adb reboot
- adb reboot bootloader
- fastboot
- factory reset
- любые команды, которые изменяют разделы диска
- любые команды, которые удаляют данные
- любые команды, которые выгружают личные данные с Android

Если нужна потенциально опасная операция — не выполняй её, а предложи ручной шаг с предупреждением DANGER.

---

# Этап 1. Read-only аудит текущей структуры

Сначала ничего не меняй.

Выполни read-only анализ:

1. Покажи дерево проекта.
2. Найди:
   - README.md;
   - docs/;
   - scripts/;
   - config/;
   - tests/;
   - docker-compose файлы;
   - Dockerfile;
   - .github/workflows;
   - SECURITY.md;
   - CONTRIBUTING.md;
   - LICENSE;
   - CLAUDE.md;
   - AGENTS.md;
   - Android-related docs/scripts.
3. Определи, какие проверки уже есть.
4. Определи, каких проверок не хватает.
5. Сформируй краткий audit summary.

---

# Этап 2. Создать структуру quality-документации

Создай, если отсутствует:

```text
docs/quality/
docs/quality/results/
tests/
tests/network/
tests/service/
tests/storage/
tests/backup/
tests/android/
tests/load/
```

Создай или обнови файлы:

```text
docs/quality/TEST_PLAN.md
docs/quality/TEST_MATRIX.md
docs/quality/RELEASE_ACCEPTANCE_CHECKLIST.md
docs/quality/RELIABILITY_REPORT_TEMPLATE.md
docs/quality/NETWORK_TESTS.md
docs/quality/STORAGE_TESTS.md
docs/quality/BACKUP_RESTORE_TESTS.md
docs/quality/ANDROID_TESTS.md
docs/quality/LOAD_TESTS.md
docs/quality/SECURITY_TESTS.md
```

Требования:
- документация на английском;
- инженерный стиль;
- без обещания production-grade надёжности;
- с честным описанием ограничений Jetson Nano и старого HDD/SSD;
- все опасные операции должны иметь предупреждение DANGER.

---

# Этап 3. Создать безопасные тестовые скрипты

Создай скрипты, если их нет:

```text
tests/network/connectivity_check.sh
tests/network/port_check.sh
tests/service/docker_healthcheck.sh
tests/service/nextcloud_smoke.sh
tests/service/immich_smoke.sh
tests/storage/smart_check.sh
tests/storage/mount_check.sh
tests/storage/fio_quick_test.sh
tests/backup/restore_test.sh
tests/android/adb_readonly_check.sh
```

Все shell-скрипты должны иметь:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

Все скрипты должны:
- иметь `--help`;
- выводить понятные сообщения;
- проверять зависимости;
- не удалять данные;
- не форматировать диски;
- не менять системные конфиги без подтверждения;
- завершаться понятным кодом ошибки.

---

# Этап 3.1. tests/network/connectivity_check.sh

Назначение:
- ping до Jetson;
- curl до Nextcloud URL;
- DNS check, если задан;
- сохранение результата в Markdown.

Аргументы:
- `--host`
- `--url`
- `--dns-name`, опционально
- `--output`, опционально

Нельзя:
- сканировать чужие сети;
- использовать агрессивное сканирование;
- использовать nmap по внешним адресам.

---

# Этап 3.2. tests/network/port_check.sh

Назначение:
- проверка только явно заданных портов через `nc -vz`.

Аргументы:
- `--host`
- `--ports "80,443,8080"`
- `--output`, опционально

Нельзя:
- сканировать диапазоны портов без явного указания;
- проверять чужие IP.

---

# Этап 3.3. tests/service/docker_healthcheck.sh

Назначение:
- `docker compose ps`;
- `docker compose config`;
- health status контейнеров;
- `docker stats --no-stream`, если Docker доступен.

Не перезапускать контейнеры автоматически.

---

# Этап 3.4. tests/service/nextcloud_smoke.sh

Назначение:
- проверить `/status.php`;
- проверить HTTP-код;
- измерить время ответа через curl.

Аргументы:
- `--url`
- `--output`, опционально

---

# Этап 3.5. tests/service/immich_smoke.sh

Назначение:
- проверить доступность Immich URL, если сервис есть в проекте.

Аргументы:
- `--url`
- `--output`, опционально

Если Immich не используется — скрипт должен корректно сообщить `not applicable`.

---

# Этап 3.6. tests/storage/smart_check.sh

Назначение:
- read-only SMART-проверка диска.

Аргументы:
- `--device /dev/sdX`
- `--output`, опционально

Разрешено:
- `smartctl -a`;
- `smartctl -l selftest`;
- чтение температуры.

Запрещено:
- форматирование;
- изменение разделов;
- запуск destructive-тестов.

---

# Этап 3.7. tests/storage/mount_check.sh

Назначение:
- `lsblk`;
- `blkid`;
- `df -h`;
- проверка mount point.

Аргументы:
- `--mount-point`, опционально
- `--output`, опционально

---

# Этап 3.8. tests/storage/fio_quick_test.sh

Назначение:
- безопасный короткий тест fio только в указанной тестовой папке.

Аргументы:
- `--directory /mnt/nas/test_fio`
- `--size 1G`, опционально
- `--output`, опционально

Требования:
- требовать подтверждение перед запуском;
- проверять, что directory не `/`, не `/home`, не `/etc`, не пустой путь;
- создавать только тестовый файл;
- удалять только свои тестовые файлы;
- не трогать пользовательские данные.

---

# Этап 3.9. tests/backup/restore_test.sh

Назначение:
- создать тестовый файл;
- выполнить rsync dry-run;
- выполнить restore в безопасную временную папку;
- проверить через diff.

Аргументы:
- `--source /mnt/nas/test-data`
- `--restore-dir /tmp/nas_jetson_nano_restore_test`
- `--output`, опционально

Не трогать реальные пользовательские данные.

---

# Этап 3.10. tests/android/adb_readonly_check.sh

Назначение:
- проверить `adb devices`;
- вывести модель телефона;
- версию Android;
- наличие релевантных пакетов.

Разрешены только read-only команды:

```bash
adb devices
adb shell getprop ro.product.manufacturer
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell pm list packages
```

Запрещены:
- adb install;
- adb uninstall;
- adb pull личных данных;
- adb shell content query;
- adb shell pm clear;
- adb reboot.

Отчёт не должен содержать:
- IMEI;
- serial полностью;
- аккаунты;
- номера телефонов;
- Wi-Fi данные;
- личные файлы.

---

# Этап 4. Создать k6 smoke test

Создай файл:

```text
tests/load/nextcloud-smoke.js
```

Требования:
- использовать переменную окружения `NEXTCLOUD_URL`;
- проверять `/status.php`;
- профиль: 5 VU / 2 минуты;
- проверять HTTP status 200;
- проверять response time;
- не запускать автоматически.

Пример логики:
- если `NEXTCLOUD_URL` не задан, использовать placeholder и вывести понятную ошибку.

---

# Этап 5. Обновить GitHub Actions

Проверь существующие workflow.

Добавь отдельный workflow, если его нет:

```text
.github/workflows/quality-checks.yml
```

Он должен выполнять:

1. checkout;
2. bash syntax check;
3. ShellCheck;
4. Docker Compose config validation, если есть compose-файл;
5. Gitleaks или подготовку к Gitleaks;
6. Trivy fs scan или отдельный security workflow;
7. actionlint, если возможно.

Если CI получается тяжёлым, раздели:

```text
.github/workflows/quality-checks.yml
.github/workflows/security-scan.yml
```

Не ломай существующие workflow.

---

# Этап 6. Выполнить безопасные локальные проверки

Выполни только безопасные проверки:

```bash
find . -name "*.sh" -print0 | xargs -0 -r bash -n
```

Если доступен ShellCheck:

```bash
find . -name "*.sh" -print0 | xargs -0 -r shellcheck
```

Если доступен Docker и есть compose-файл:

```bash
docker compose config
```

Если доступен Git:

```bash
git status --short
```

Не запускай:
- fio без подтверждения;
- k6 без подтверждения;
- ADB без подключённого устройства и разрешения;
- любые destructive-тесты.

---

# Этап 7. Сформировать отчёты

Создай итоговый baseline report:

```text
docs/quality/results/YYYY-MM-DD_baseline_quality_report.md
```

Структура:

```markdown
# Baseline Quality Report: NAS_Jetson_Nano

## 1. Executive summary
## 2. Environment
## 3. Repository audit
## 4. Static checks
## 5. Docker Compose validation
## 6. Network checks
## 7. Storage checks
## 8. Backup/restore checks
## 9. Android checks
## 10. Load test readiness
## 11. Monitoring readiness
## 12. Security findings
## 13. Risks
## 14. Recommended fixes
## 15. Article-ready summary
```

Также создай/обнови:

```text
docs/quality/RELIABILITY_REPORT_TEMPLATE.md
docs/quality/RELEASE_ACCEPTANCE_CHECKLIST.md
docs/quality/TEST_MATRIX.md
```

---

# Этап 8. Article-ready summary

В baseline report добавь раздел:

```markdown
## Article-ready summary
```

В нём коротко сформулируй:

- какие проверки добавлены;
- какие проверки прошли;
- какие проверки требуют ручного запуска;
- какие ограничения честно указать;
- почему проект теперь выглядит инженерно проверенным.

Нельзя писать, что решение production-grade, если это не доказано.

---

# Этап 9. Финальный вывод Codex

В конце работы выведи:

1. Что было найдено.
2. Какие файлы созданы.
3. Какие файлы обновлены.
4. Какие проверки выполнены.
5. Какие проверки не запускались и почему.
6. Какие риски остаются.
7. Что нужно сделать вручную.
8. Команды для commit:

```bash
git status
git add docs/quality tests .github/workflows
git commit -m "Add reliability and quality validation framework"
git push
```

---

# Стиль

Документацию пиши на английском языке, если файл предназначен для публичного репозитория.

Тон:
- инженерный;
- честный;
- без хайпа;
- без обещания production-grade надёжности;
- с явным указанием ограничений Jetson Nano и старых HDD/SSD.

Начинай с read-only аудита текущего репозитория.
```

---

## 3. Что ожидать после выполнения

После выполнения Codex должен подготовить:

```text
docs/quality/
tests/
.github/workflows/quality-checks.yml
docs/quality/results/YYYY-MM-DD_baseline_quality_report.md
```

И вывести список ручных действий, которые нельзя запускать автоматически.

---

## 4. Команды для фиксации

После проверки результата вручную:

```bash
git status
git diff
git add docs/quality tests .github/workflows
git commit -m "Add reliability and quality validation framework"
git push
```
