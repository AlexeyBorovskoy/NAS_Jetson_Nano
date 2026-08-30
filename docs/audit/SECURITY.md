# Security audit / Аудит безопасности

**Дата / Date:** 2026-08-30. Read-only, без эксплуатации уязвимостей / read-only, no exploitation. Секреты — только `file:line, тип, [REDACTED]`, никогда значение / secrets never printed by value.

## 1. SSH

`/etc/ssh/sshd_config` (прочитан без root):
```
GatewayPorts clientspecified     # намеренно — контейнеры видят обратный туннель
ClientAliveInterval 60
ClientAliveCountMax 3            # добавлено 2026-08-23 (грабли: мёртвый туннель держался ~2ч)
#PermitRootLogin ...              (закомментировано — системный default)
#PasswordAuthentication ...       (закомментировано — системный default)
```

🟠 **Находка**: `PasswordAuthentication`/`PermitRootLogin` не заданы явно — используется дефолт демона, не подтверждённый напрямую. Безопасная проверка `sshd -T | grep -iE 'passwordauthentication|permitrootlogin'` **не выполнена** в этом заходе (не входила в собранный набор команд) — см. `UNKNOWNS.md`.

## 2. Docker: privileged / host networking / docker.sock

| Файл:строка | Настройка | Оценка |
|---|---|---|
| `docker-compose.coturn.yml:21` | `network_mode: host` | обоснованно (TURN нужен широкий UDP-диапазон), но контейнер не развёрнут |
| `docker-compose.samba.yml:20` | `network_mode: host` | обоснованно (NetBIOS/mDNS не проходят Docker NAT) |
| `docker-compose.monitoring.yml:57,141` | `docker.sock:ro` (Netdata, Portainer) | принятый риск — `ro` не убирает полностью (read-only доступ к Docker API раскрывает список контейнеров/env) |
| `docker-compose.nas_jetson_nano-api.yml:18` | `docker.sock:ro` | используется для чтения статуса + restart по whitelist |

`privileged: true` — **не найдено** ни в одном compose-файле. Смонтированных `/dev` — ни у одного контейнера.

## 3. API на порту 8099 (`services/nas_jetson_nano-api`)

- **Аутентификация**: JWT, `auth.py` — логин/пароль проверяется **против Nextcloud OCS** (не своя БД пользователей), HS256, TTL по умолчанию 24ч.
- 🟠 **Находка**: `config.py:22` — `jwt_secret: str = secrets.token_hex(32)` генерируется **случайно при каждом старте процесса**, если `NAS_JETSON_NANO_API_JWT_SECRET` не задан в `.env`. Не проверялось, задан ли реально на устройстве (запрет читать `.env`). Если не задан — все выданные токены аннулируются при каждом перезапуске/пересборке контейнера.
- 🟠 **Находка (MEDIUM)**: `main.py:171-176` — `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])`. Полностью открытый CORS. JWT передаётся в заголовке `Authorization`, не в cookie — классический CSRF не эксплуатируется напрямую браузером, но `*`-origin разрешает любому сайту делать fetch к API, если токен доступен JS (не проверялось, как его хранит клиент). Для API, живущего только в LAN без выхода в интернет, эксплуатируемость низкая, но нарушает принцип наименьших привилегий.
- `POST /v1/report/now` — не требует JWT (документировано как осознанное), subprocess без пользовательских аргументов, риск низкий (нет rate-limit — теоретический DoS через спам-вызовы).
- `POST /v1/actions/containers/{name}/restart` — JWT обязателен, whitelist контейнеров проверяется до вызова Docker API — корректный паттерн.

## 4. Command injection / subprocess

`grep -rn "subprocess\|os.system\|shell=True"` по `services/` и `scripts/monitoring/*.py` — **ни одного `shell=True` не найдено**. Везде `asyncio.create_subprocess_exec(...)`/`subprocess.run([...])` со списком аргументов, команды берутся из конфига, не из пользовательского ввода. **Инъекции не выявлено.**

🟠 **Отдельная находка (не security, деплой)**: `config.py:47` — `report_cmd` default указывает на `/usr/local/sbin/nas_jetson_nano-send-report-telegram.sh`, которого на устройстве **нет** (есть `nasa-send-report-telegram.sh`); в `.env` устройства переопределения `REPORT_CMD=`/`BACKUP_CMD=` тоже нет (`grep -c` → 0). Если бы переименованный код был выкачен «как есть» без явного переопределения — `/v1/report/now` и `/v1/actions/backup/now` упали бы `FileNotFoundError`. Прямое следствие известного расхождения git↔устройство, не проявляется сейчас, т.к. контейнер работает на старом коде.

## 5. Secrets-аудит

`bash scripts/security/check_no_secrets.sh` → **чисто** («No obvious secrets found outside allowed files»), после фикса ложного срабатывания от 2026-08-30 (см. `git log`, коммит `7707d0e`).

`config/certs/russian_trusted_bundle.pem` — публичный сертификат (`BEGIN CERTIFICATE`), закоммичен намеренно, известный false-positive для наивных сканеров.

**Права файлов на устройстве** (структура, не содержимое):
```
~/nasa/config/.env            600  admin:admin   3635 байт, изменён 2026-08-24
~/nasa/config/.env.example    664  admin:admin   5162 байта (шаблон, читаем ожидаемо)
~/nasa/config/certs/*.pem     644  (публичный сертификат)
/opt/nasa/config/.env         640  root:root     181 байт
```
Ничего world-readable среди файлов с реальными секретами.

🟠 **Находка**: **10 файлов `.env.bak.*`** в `~/nasa/config/` (от 31 мая до 24 августа), все `600`, без единой политики ротации/удаления старых версий. Каждый — ещё одна копия секретов на диске. Растущая поверхность при компрометации диска.

## 6. Firewall

Вне периметра этой части (уровень VPS, не устройства). По CLAUDE.md: ufw на VPS пускает сервисные порты только с `172.29.172.0/24` и `10.8.1.0/24`; известная незакрытая находка прошлых аудитов — `DOCKER-USER` пуст (правила Docker вставляются в `FORWARD` до ufw).

## 7. HTTP без TLS в LAN

Принятый и задокументированный риск (CLAUDE.md), не переисследовался повторно.

## Сводка находок / Findings summary

| # | Находка | Уровень |
|---|---|---|
| 1 | CORS `*` на API 8099 | MEDIUM |
| 2 | JWT-секрет может генерироваться заново при каждом рестарте | MEDIUM (если действительно не задан — не подтверждено) |
| 3 | 10 незаротированных `.env.bak.*` | LOW-MEDIUM |
| 4 | `report_cmd`/`backup_cmd` default сломается при наивном деплое переименованного кода | LOW (деплой, не security) |
| 5 | `PasswordAuthentication`/`PermitRootLogin` не подтверждены явно | UNKNOWN — требует одной read-only команды |
| 6 | `jms583-health.log` без logrotate (см. `RISKS.md`) | LOW |

Ничего из найденного не относится к CRITICAL — критичные периметры (правило №2/4/13 CLAUDE.md: наружу с VPS только 22/443/40568, с Jetson — ничего напрямую) не нарушены.
