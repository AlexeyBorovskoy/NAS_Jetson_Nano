# NAS_Jetson_Nano — план проверки надёжности, устойчивости и качества

**Проект:** `NAS_Jetson_Nano` / `NAS_Jetson_Nano`
**Дата подготовки плана:** 2026-06-27  
**Назначение:** документ для размещения в репозитории и последующего выполнения Codex-агентом.

---

## 1. Зачем нужен этот план

Проект готовится к публичным публикациям: Hackaday.io, Хабр, DEV.to и другие площадки.  
Перед публикацией нужно не просто описать архитектуру, а показать, что решения проверены:

- сетево;
- по Docker Compose;
- по скриптам и коду;
- по безопасности;
- по хранилищу;
- по backup/restore;
- по Android-клиенту;
- по мониторингу;
- по воспроизводимости.

Цель проверки:

```text
Получить инженерное подтверждение, что проект можно честно публиковать как воспроизводимое решение,
а не как набор непроверенных экспериментов.
```

---

## 2. Исходный контекст

По предыдущему аудиту проект уже имеет хорошую базу:

- общая оценка проекта: около `7.9/10`;
- документация объёмная;
- Docker Compose уже валидируется;
- CI содержит secrets-check и validate-compose;
- слабые места: нет CI ShellCheck, не хватает Trivy/image scanning, есть вопросы к networking/VPN-документу, нужны non-root контейнеры, PR template и GitHub Topics.

Этот план добавляет отдельный контур проверки качества и устойчивости.

---

## 3. Уровни проверки

| № | Уровень | Что проверяем | Результат |
|---:|---|---|---|
| 1 | Репозиторий | структура, README, docs, CI, templates | repo audit report |
| 2 | Статический анализ | bash, yaml, docker, markdown, secrets | static checks report |
| 3 | Docker Compose | config, healthchecks, restart policy, dependencies | docker services report |
| 4 | Сеть | ping, DNS, HTTP/HTTPS, TCP ports, LAN speed | network report |
| 5 | Хранилище | SMART, mount, UUID, filesystem, speed | storage report |
| 6 | Backup/restore | dry-run, restore, diff | backup restore report |
| 7 | Android | ADB read-only, apps, sync checklist | android report |
| 8 | Нагрузка | light smoke load test | load test report |
| 9 | Мониторинг | Uptime Kuma / Prometheus readiness | monitoring report |
| 10 | Статья | доказательства, таблицы, честные ограничения | article-ready summary |

---

## 4. Главные правила безопасности

### 4.1. Запрещённые действия без отдельного подтверждения

Codex/агент не должен автоматически выполнять:

```bash
mkfs
fdisk
parted
dd
wipefs
rm -rf
adb install
adb shell pm uninstall
adb shell pm clear
adb reboot
adb reboot bootloader
fastboot
factory reset
```

Также запрещено:

- форматировать диски;
- менять таблицу разделов;
- удалять данные;
- выгружать личные файлы с Android;
- публиковать токены, пароли, ключи, IMEI, serial, аккаунты, Wi-Fi данные;
- выполнять агрессивное сканирование чужих сетей.

### 4.2. Принцип read-only по умолчанию

Все проверки по умолчанию должны быть read-only.

Если проверка может изменить систему, перед ней должен быть блок:

```text
DANGER: эта операция может изменить систему или повлиять на данные.
Выполнять только вручную после backup и явного подтверждения.
```

---

## 5. Рекомендуемая структура файлов в проекте

Codex должен создать или обновить такую структуру:

```text
docs/
└── quality/
    ├── TEST_PLAN.md
    ├── TEST_MATRIX.md
    ├── RELEASE_ACCEPTANCE_CHECKLIST.md
    ├── RELIABILITY_REPORT_TEMPLATE.md
    ├── NETWORK_TESTS.md
    ├── STORAGE_TESTS.md
    ├── BACKUP_RESTORE_TESTS.md
    ├── ANDROID_TESTS.md
    ├── LOAD_TESTS.md
    ├── SECURITY_TESTS.md
    └── results/
        └── YYYY-MM-DD_baseline_quality_report.md

tests/
├── network/
│   ├── connectivity_check.sh
│   ├── port_check.sh
│   └── iperf_lan_test.md
├── service/
│   ├── docker_healthcheck.sh
│   ├── nextcloud_smoke.sh
│   └── immich_smoke.sh
├── storage/
│   ├── smart_check.sh
│   ├── mount_check.sh
│   └── fio_quick_test.sh
├── backup/
│   └── restore_test.sh
├── android/
│   ├── adb_readonly_check.sh
│   └── android_sync_checklist.md
├── load/
│   └── nextcloud-smoke.js
└── README.md
```

---

## 6. Инструменты проверки

| Область | Инструмент | Зачем нужен | Приоритет |
|---|---|---|---|
| Bash | `bash -n` | синтаксис shell-скриптов | Critical |
| Bash | ShellCheck | качество и ошибки shell | Critical |
| Bash | shfmt | форматирование shell | Medium |
| Docker Compose | `docker compose config` | валидность compose | Critical |
| Dockerfile | Hadolint | проверка Dockerfile | High |
| Secrets | Gitleaks | поиск секретов | Critical |
| Security | Trivy | уязвимости, misconfig, secrets | High |
| YAML | yamllint | проверка YAML | Medium |
| Markdown | markdownlint | качество документации | Medium |
| GitHub Actions | actionlint | проверка workflows | High |
| Network | ping, mtr, curl, nc, dig | связанность и доступность | Critical |
| LAN speed | iperf3 | пропускная способность | High |
| Storage | smartctl, lsblk, blkid, df | состояние дисков | Critical |
| Storage speed | fio | осторожный тест скорости | Medium |
| Backup | rsync, diff | проверка восстановления | Critical |
| Android | adb | read-only проверка телефона | High |
| Load | k6 | лёгкая нагрузка | Medium |
| Monitoring | Uptime Kuma / Blackbox Exporter | постоянный контроль | High |

---

## 7. Этап 1 — аудит репозитория

### 7.1. Проверить наличие

- `README.md`;
- `docs/`;
- `scripts/`;
- `tests/`;
- `config/`;
- `docker-compose*.yml`;
- `compose*.yml`;
- `Dockerfile*`;
- `.github/workflows/`;
- `LICENSE`;
- `SECURITY.md`;
- `CONTRIBUTING.md`;
- PR template;
- issue templates;
- Android-документация;
- release notes.

### 7.2. Результат

Создать отчёт:

```text
docs/quality/results/YYYY-MM-DD_repo_audit.md
```

Таблица:

| Элемент | Есть/нет | Качество | Что улучшить |
|---|---|---|---|

---

## 8. Этап 2 — статические проверки

### 8.1. Bash syntax

```bash
find . -name "*.sh" -print0 | xargs -0 -r bash -n
```

### 8.2. ShellCheck

```bash
find . -name "*.sh" -print0 | xargs -0 -r shellcheck
```

### 8.3. shfmt

```bash
find . -name "*.sh" -print0 | xargs -0 -r shfmt -d
```

### 8.4. Docker Compose

```bash
docker compose config
```

Если несколько compose-файлов:

```bash
find . \( -name "docker-compose*.yml" -o -name "compose*.yml" \) -print
```

### 8.5. Secrets

```bash
gitleaks detect --source . --no-git --redact
```

### 8.6. Trivy

```bash
trivy fs --scanners vuln,secret,misconfig .
```

### 8.7. Hadolint

```bash
find . -name "Dockerfile*" -print0 | xargs -0 -r hadolint
```

### 8.8. Результат

Создать:

```text
docs/quality/results/YYYY-MM-DD_static_checks.md
```

---

## 9. Этап 3 — Docker Compose и сервисы

### 9.1. Проверки

```bash
docker compose ps
docker compose config
docker compose logs --tail=100
docker stats --no-stream
```

### 9.2. Проверить

| Проверка | Ожидаемый результат |
|---|---|
| Compose валиден | `docker compose config` без ошибок |
| Сервисы подняты | `docker compose ps` без постоянных restart-loop |
| Healthcheck есть | для ключевых сервисов |
| Restart policy есть | `restart: unless-stopped` или обоснование |
| Memory limits есть | для тяжёлых сервисов |
| Non-root users | если применимо |
| Secrets не в compose | пароли не захардкожены |

### 9.3. Результат

```text
docs/quality/results/YYYY-MM-DD_docker_services.md
```

---

## 10. Этап 4 — сетевая связанность

### 10.1. Базовые переменные

```bash
JETSON_IP="192.168.1.100"
NEXTCLOUD_URL="http://192.168.1.100"
```

### 10.2. Проверки

```bash
ping -c 20 "$JETSON_IP"
mtr -rwzc 50 "$JETSON_IP"
nc -vz "$JETSON_IP" 80
nc -vz "$JETSON_IP" 443
curl -I "$NEXTCLOUD_URL"
```

### 10.3. DNS

```bash
dig cloud.local
dig nextcloud.local
```

Если локальный DNS не используется — указать `not applicable`.

### 10.4. iperf3

На Jetson:

```bash
iperf3 -s
```

На клиенте:

```bash
iperf3 -c "$JETSON_IP" -t 30
```

### 10.5. Что записать

| Показатель | Значение |
|---|---|
| Ping avg |  |
| Packet loss |  |
| mtr loss |  |
| HTTP status |  |
| HTTPS status |  |
| Open ports |  |
| iperf3 throughput |  |

### 10.6. Результат

```text
docs/quality/results/YYYY-MM-DD_network_tests.md
```

---

## 11. Этап 5 — хранилище

### 11.1. Read-only диагностика

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL
blkid
df -h
mount | grep -E "nas|nextcloud|media|mnt" || true
```

### 11.2. SMART

```bash
sudo smartctl -a /dev/sdX
sudo smartctl -t short /dev/sdX
sudo smartctl -l selftest /dev/sdX
```

### 11.3. FIO quick test

Только в тестовой папке:

```bash
mkdir -p /mnt/nas/test_fio

fio --name=nas_readwrite_test \
  --directory=/mnt/nas/test_fio \
  --size=1G \
  --bs=4M \
  --rw=readwrite \
  --direct=1 \
  --numjobs=1 \
  --runtime=60 \
  --time_based \
  --group_reporting
```

Удалять только собственные тестовые файлы.

### 11.4. Результат

```text
docs/quality/results/YYYY-MM-DD_storage_tests.md
```

---

## 12. Этап 6 — backup/restore

### 12.1. Главный принцип

```text
Backup без restore-теста не считается backup.
```

### 12.2. Тест

```bash
mkdir -p /mnt/nas/test-data
echo "NAS_Jetson_Nano backup test $(date)" > /mnt/nas/test-data/test.txt

mkdir -p /tmp/nas_jetson_nano_restore_test
rsync -avh --dry-run /mnt/nas/test-data/ /tmp/nas_jetson_nano_restore_test/
rsync -avh /mnt/nas/test-data/ /tmp/nas_jetson_nano_restore_test/
diff -r /mnt/nas/test-data/ /tmp/nas_jetson_nano_restore_test/
```

### 12.3. Результат

```text
docs/quality/results/YYYY-MM-DD_backup_restore_tests.md
```

---

## 13. Этап 7 — Android-контур

### 13.1. Только read-only

Разрешённые команды:

```bash
adb devices
adb shell getprop ro.product.manufacturer
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell pm list packages
```

### 13.2. Проверки приложений

```bash
adb shell pm list packages | grep -i nextcloud || true
adb shell pm list packages | grep -i dav || true
adb shell pm list packages | grep -i immich || true
adb shell pm list packages | grep -i syncthing || true
```

### 13.3. Чек-лист

| Проверка | Статус |
|---|---|
| Телефон виден по ADB |  |
| Android version определена |  |
| Nextcloud client установлен |  |
| Immich client установлен |  |
| DAVx5 установлен |  |
| Синхронизация фото работает | manual |
| Синхронизация файлов работает | manual |
| ADB выключен после настройки | manual |
| Личные данные не попали в отчёт |  |

### 13.4. Результат

```text
docs/quality/results/YYYY-MM-DD_android_tests.md
```

---

## 14. Этап 8 — нагрузочное тестирование

### 14.1. k6 smoke test

Файл:

```text
tests/load/nextcloud-smoke.js
```

Сценарий:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '2m',
};

export default function () {
  const baseUrl = __ENV.NEXTCLOUD_URL || 'http://YOUR_NEXTCLOUD_HOST';
  const res = http.get(`${baseUrl}/status.php`);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
```

Запуск:

```bash
NEXTCLOUD_URL="http://192.168.1.100" k6 run tests/load/nextcloud-smoke.js
```

### 14.2. Во время нагрузки смотреть

```bash
docker stats
free -h
uptime
df -h
```

### 14.3. Результат

```text
docs/quality/results/YYYY-MM-DD_load_tests.md
```

---

## 15. Этап 9 — мониторинг

### 15.1. MVP

Uptime Kuma:

| Объект | Тип проверки |
|---|---|
| Jetson Nano | Ping |
| Router | Ping |
| Nextcloud | HTTP/HTTPS |
| Immich | HTTP/HTTPS |
| Docker containers | Docker monitor |
| DNS name | DNS |

### 15.2. Продвинутый вариант

Prometheus + Blackbox Exporter + Grafana.

### 15.3. Результат

```text
docs/quality/results/YYYY-MM-DD_monitoring_setup.md
```

---

## 16. Release acceptance checklist

Перед статьёй и release:

| Критерий | Статус |
|---|---|
| README понятен за 30 секунд |  |
| Quick Start виден вверху README |  |
| GitHub Topics заданы |  |
| PR template есть |  |
| ShellCheck в CI есть |  |
| docker compose config проходит |  |
| Gitleaks не находит секреты |  |
| Trivy выполнен |  |
| Nextcloud доступен в LAN |  |
| Android-клиент проверен |  |
| SMART без критических ошибок |  |
| Backup restore test пройден |  |
| Uptime мониторинг настроен |  |
| Опасные команды не автоматизированы |  |
| Статья содержит честные ограничения |  |

---

## 17. Итоговый reliability report

Итоговый файл:

```text
docs/quality/RELIABILITY_REPORT.md
```

Структура:

```markdown
# Reliability Report: NAS_Jetson_Nano

## 1. Executive summary
## 2. Test environment
## 3. Repository checks
## 4. Static checks
## 5. Docker Compose validation
## 6. Network tests
## 7. Storage tests
## 8. Backup/restore tests
## 9. Android client tests
## 10. Load tests
## 11. Monitoring
## 12. Security findings
## 13. Known limitations
## 14. Final readiness score
## 15. Article-ready summary
```

---

## 18. Минимальный стартовый набор

Для первой итерации достаточно:

1. `bash -n`;
2. ShellCheck;
3. Gitleaks;
4. `docker compose config`;
5. network connectivity check;
6. SMART read-only check;
7. backup restore test;
8. Android read-only ADB check;
9. baseline quality report.

После этого уже можно писать в статье:

```text
Before publishing the project, I added a reliability validation layer:
static checks, Docker Compose validation, network checks, storage health checks,
backup/restore tests and Android client verification.
```
