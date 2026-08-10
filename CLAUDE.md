# CLAUDE.md — NAS_Jetson_Nano

> Этот файл читается Claude Code автоматически при открытии проекта.
> Содержит контекст, команды и правила для работы в этом репозитории.

## Проект

**NAS_Jetson_Nano** — приватный семейный облачный сервер на NVIDIA Jetson Nano 4 GB + USB SSD 250 ГБ + USB HDD 2 ТБ.
Заменяет Google Photos (→ Immich), Google Drive (→ Nextcloud), облачный NAS (→ Samba).

- GitHub: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano
- Owner: AlexeyBorovskoy (a.e.borovskoy@gmail.com)
- Текущий релиз: v1.4.0 — JMS583 USB SSD enclosure, UAS quirk, goss 40/40
- Основная ветка: `main`

## Операционное состояние

**Состояние на 2026-08-10 (live-аудит через VPS-jump): все 13 контейнеров up (healthy), 0 рестартов, 0 OOM. Оба диска смонтированы, 0 USB-ошибок. Бэкапы идут по расписанию, restore проверен. Реверс-туннель жив. Сервисы уведены за VPN. Открытых 🔴 нет.**
Полный отчёт: `docs/plans/SYSTEM_AUDIT_2026-08-10.md`.

> ⚠️ **Расхождение git ↔ устройство.** Живой Jetson работает на СТАРОМ, до-переименовочном деплое. Rename `NASA → NAS_Jetson_Nano` сделан только в git — **на устройство не выкатан**. Фактически на устройстве:
> - Репо: **`~/nasa`**, remote `github.com/AlexeyBorovskoy/Nasa_home.git` (HEAD `0f9fd0f`, ветка `main`)
> - Контейнеры: префикс **`homecloud_*`** (не `nas_jetson_nano_*`), API-контейнер `homecloud_nasa_api`
> - systemd-юниты: префикс **`nasa-*`** (не `nas_jetson_nano-*`)
> - Логи мониторинга: **`/var/log/nasa-monitor/`**
> - Сетевой профиль NetworkManager: **`nasa-lan`** (правило №3 ниже называет его по будущему имени)
> - На устройстве **8 файлов изменены вручную** и не в git (Talk-бот, HDD 2 ТБ, Samba, скрипты отчётов) — рядом лежат бэкапы `*.bak.*`. Любой `git pull` на устройстве их затрёт.
> Полная миграция устройства на переименованный layout — отдельная неначатая задача (backup + окно обслуживания).

> ✅ **Закрыто с прошлого аудита (2026-08-01 → 2026-08-10):**
> 1. **Сервисы больше не открыты в интернет.** ufw на VPS пускает 8080/8443/2283/2443/8090/9443/8099/8091/8765/8766 только с `172.29.172.0/24` и `10.8.1.0/24`. Наружу открыты лишь 22, 443 (XRay) и 40568/udp (AmneziaWG). Правило №4 соблюдено.
> 2. **Бэкапы починены.** Причина простоя 24.07 → 09.08 — незакавыченное `TALK_BOT_DISPLAY_NAME=NAS Bot` в `config/.env`: `source` под `set -euo pipefail` падал с кодом 127. Роняло разом бэкапы, `storage_preflight.sh`, `nasa-ssd-recovery` и `jetson-nas-health`. Исправлено 2026-08-09; **restore впервые проверен** накатом дампов во временную БД.
> 3. **Сменился IP VPS.** `193.8.215.130` заблокирован российскими ISP (per-IP stateful-блок, с 2026-08-06). Рабочий адрес — **`95.163.176.103`**. `VPS_HOST` живёт в root-owned `/opt/nasa/config/.env` (это НЕ `~/nasa/config/.env`).

| Компонент | Статус | Детали |
|---|---|---|
| Jetson Nano | ✅ up | 192.168.0.50, eth0 1000 Мбит/с Full, аптайм с 2026-08-09 15:41 UTC |
| Температуры | ✅ норма | CPU/AO 45 °C, GPU 41.5 °C, PMIC 50 °C |
| RAM | 🟠 плотно | 2.0 / 3.9 ГБ занято + zram-swap 312 МБ из 1.9 ГБ |
| SSD `/dev/sda1` → `/mnt/storage` | ✅ mounted | 229G, **5 %** (9.7G), ext4 noatime |
| HDD 2 ТБ `/dev/sdb1` → `/mnt/hdd2tb` | ✅ mounted | WD20EADS, **NTFS** через ntfs-3g, метка `Borovskoy_Hard`, 1.9T, **76 %** (1.4T архива, 462G свободно) |
| USB SSD энклоужер | ✅ **JMS583** (152d:a583) | USB 3.0 SuperSpeed 5000 Mbps, драйвер `usb-storage` |
| USB HDD мост | ✅ **RTL9201** (0bda:9201) | USB 3.0, драйвер `usb-storage` |
| `usbcore.autosuspend=-1` | ✅ kernel | `/proc/cmdline` |
| `usb-storage.quirks=0bda:9210:rw,152d:a583:u,0bda:9201:u` | ✅ active | UAS отключён для **обоих** дисков. SSD write 250 / read 172 МБ/с; HDD read 106 / write 92 МБ/с |
| USB-ошибки | ✅ **0** | dmesg с момента загрузки — ни одной (`error -71`, `uas_eh`, `I/O error`) |
| SCSI timeout | ✅ 120s | udev правило активно |
| USB watchdog / pre-boot / error monitor | ✅ active | `nasa-usb-watchdog.timer`, `nasa-usb-preboot.service`, `nasa-usb-monitor.service` |
| JMS583 health timer | ✅ active (waiting) | `nasa-jms583-health.timer` ежечасно; последний прогон `errors=0 warnings=0` |
| SSD hotplug auto-recovery | ✅ active | `nasa-ssd-recovery.service` — udev(`sda1`) → mount → preflight → Docker → контейнеры |
| smartd | ⛔ **disabled by design** | UAS-quirk → usb-storage BOT → SMART passthrough невозможен в принципе. Здоровье закрывают JMS583-таймер и USB-монитор. См. `docs/13_MONITORING_RUNBOOK.md` |
| Бэкапы БД | ✅ работают | `nasa-backup.timer`, последний дамп **2026-08-10 03:02** (immich 19 МБ + nextcloud 2.7 МБ), каталог 150 МБ |
| Restore | ✅ **проверен 2026-08-09** | Накат во временную БД: NC 153 таблицы (users 5 = live, filecache 403 = live); Immich 61 таблица (asset 7098 = live, album 23 = live) |
| VPS reverse tunnel | ✅ active | `nasa-tunnel.service`, ESTAB `192.168.0.50 → 95.163.176.103:22`; на VPS подняты 18080/12283/18090/18099/10022/45876 |
| Docker daemon | ✅ active | **13 контейнеров** `homecloud_*` up (healthy), **restarts=0**, **OOMKilled=false** у всех |
| Talk-бот (Phase A) | ✅ running | `homecloud_nasa_api`, room `37pcobmf`, триггер `нас`, `last_error: null`. Хирургический backport на `~/nasa` |
| Immich | ✅ v2.7.5 | **7098 ассетов** (6686 фото + 412 видео), 23 альбома, upload 5.8 ГБ (весь каталог 8.9 ГБ) |
| Nextcloud | ✅ v33.0.4 | `maintenance:false`, 5 пользователей, 403 файла в кэше |
| Nextcloud external storage | ✅ `/HDD-2TB` | mount id 1, Local → `/mnt/hdd2tb`, applicable All, sharing on, `files_external` 1.25.1 |
| Samba | ✅ up | шары `public` и **`hdd2tb`** (`\\192.168.0.50\hdd2tb`, пользователь `nas`, guest запрещён) |
| LLM Gateway | ✅ healthy | `/health` → `{"status":"ok","provider":"deepseek","redaction":"true"}` |
| Beszel Agent Jetson (45876) | ✅ active | **systemd-юнит** `beszel-agent.service` (не контейнер), enabled |
| Beszel Hub (VPS:8091) | ✅ up | доступен только через VPN |
| VPS nginx | ✅ live | `nasa_nginx` up 5 недель; проксирует 8080/2283/8090/8099/8091 на порты туннеля |
| Telegram daily report | ✅ доставляется | `nasa-daily-report-telegram.timer` активен, последняя доставка 2026-08-09 16:33 MSK |
| Android apps | ✅ установлены | Immich + Nextcloud из Play Store, DAVx⁵ APK v4.5.14 |
| Immich Android | ✅ настроен | Логин: admin@nas_jetson_nano.local; снаружи — только через VPN |
| Keenetic Omni KN-1410 | ⛔ **план закрыт 2026-08-10** | Заменён Deco E4; остаётся холодным резервом, в сеть не вводится |
| TP-Link Deco E4 (2 шт.) | 📋 закуплен, не введён | **Решение 2026-08-10: Deco заменяет роутер целиком** (режим Router, LAN IP → `192.168.0.1`). Регламент — `docs/27_HOME_NETWORK_MESH.md`. 🔴 Цена решения: Jetson 1000 → **100 Мбит/с** |
| EC220-G5 | 📋 к выводу | После перехода на Deco убирается в коробку как холодный резерв. **Не сбрасывать** — это путь отката |

**🔑 Ротация паролей (2026-06-28):** Все пароли изменены на новые. Git history очищен (filter-repo). В git секретов нет; источник истины на устройстве — `~/nasa/config/.env`.

**🔧 Если SSD упал — восстановление АВТОМАТИЧЕСКОЕ:**
> Просто физически переткни кабель SSD. Система сделает остальное сама:
> udev(`sda1`) → `nasa-ssd-recovery.service` → mount → preflight → Docker → все 13 контейнеров
> Лог: `journalctl -u nasa-ssd-recovery` или `/var/log/nasa-monitor/ssd-recovery.log`
>
> Если авто-recovery не сработал (маловероятно):
> `sudo -S systemctl start nasa-ssd-recovery.service`

**⚠️ Грабли, проверенные на практике:**
- В `config/.env` **любое значение с пробелом обязано быть в кавычках** — иначе `source` под `set -e` молча роняет бэкапы, preflight, ssd-recovery и health-чек, а systemd при этом рапортует `success`. Проверять свежестью файлов в `/mnt/storage/backups/database-dumps/`, а не статусом юнита.
- `echo "$P" | sudo -S <cmd>` **нельзя** сочетать с heredoc/stdin — `sudo -S` забирает stdin, и в файл уходит пароль. Писать файл в `/tmp` от `admin`, затем `sudo cp`.
- После правки `/etc/fstab` обязателен `systemctl daemon-reload`, иначе systemd примонтирует по старому сгенерированному юниту.
- FUSE + Docker: если хостовый mount `/mnt/hdd2tb` пересоздан, контейнеры держат мёртвую ссылку → нужен `docker compose up -d --force-recreate`.
- После временных замеров (`python3 -m http.server`) **гасить процесс** — иначе остаётся открытый порт на всю LAN (найден и закрыт при аудите 2026-08-10).

**🔜 Ближайшие задачи:**
- **Перестройка домашней сети на Deco E4** — решение принято 2026-08-10, регламент готов (`docs/27_HOME_NETWORK_MESH.md`), работы не начаты. Первый шаг — снять параметры WAN с EC220-G5.
- **Vostro как удалённый ML-узел** — решение принято 2026-08-10 (остаётся в корпоративной сети). Первый шаг L0 — проверить исходящий TCP/22 из `192.168.75.0/24` на VPS.
- Миграция устройства на переименованный layout (`~/nasa` → `NAS_Jetson_Nano`).
- Restic off-site backup (HDD 2 ТБ подключён — блокер снят).
- Память: `uptime_kuma` 92 %, `immich_microservices` 88 %, `netdata` 85 % от своих лимитов — пересмотреть.

## Железо и доступ

| Компонент | Адрес / Путь | Примечание |
|---|---|---|
| Jetson Nano | `192.168.0.50` | LAN, статический IP |
| SSH на Jetson (из дома) | `ssh admin@192.168.0.50` | key-based; работает **только из домашней сети** `192.168.0.0/24` |
| SSH через VPS (извне) | `ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103` → `ssh -p 10022 admin@127.0.0.1` | рабочий путь из внешней сети |
| SSH одной командой (ProxyJump) | `ssh -o "ProxyCommand=ssh -i ~/.ssh/borovskoy_new_ed25519 -W %h:%p root@95.163.176.103" -p 10022 admin@127.0.0.1` | позволяет `bash -s < script.sh` напрямую |
| sudo на Jetson | `sudo -S <cmd>` | пароль = `NEXTCLOUD_ADMIN_PASSWORD` из `~/nasa/config/.env` **на устройстве**; не коммитить |
| VPS (AEZA, Frankfurt DE) | `95.163.176.103` | старый `193.8.215.130` заблокирован из РФ; IPv6 `2a12:5940:665a::2/48` |
| VPS через VPN-туннель | `172.29.172.1` | запасной путь, если публичный IP снова заблокируют |
| Сервисы VPS | только через VPN | ufw пускает сервисные порты лишь с `172.29.172.0/24` и `10.8.1.0/24` |
| Keenetic Omni KN-1410 | — | ⛔ План закрыт; холодный резерв |
| TP-Link Deco E4 ×2 | `192.168.0.1` / `.3` (план) | Заменяет роутер, **режим Router**; см. `docs/27_HOME_NETWORK_MESH.md` |
| Vostro 15 ML-узел | **`192.168.75.177`** (корпоративная сеть) | Dell Vostro 15 (2018, tag `H7YB9L2`), Ubuntu 24.04, user `alexey`. **Остаётся на месте** → удалённый ML-узел через VPS-туннель. См. `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`. Сетевые параметры — источник `E:\Belgorod_platform\infra\network.md` |
| Репо на Jetson | `~/nasa` | `/home/admin/nasa` (remote `Nasa_home.git`; rename не выкатан) |

## GitHub CLI (gh)

**Установлен:** `C:\tools\gh\bin\gh.exe` (также в PATH → работает как `gh` из Git Bash и PowerShell)  
**Авторизован:** keyring (Windows), токен с полными правами `repo` + `admin`

```bash
# Из Git Bash (рекомендуется):
gh repo view                          # инфо о репозитории
gh issue list                        # список issues
gh issue create --title "..." --body "..."
gh pr list                           # список PR
gh pr create --title "..." --body "..."
gh release list                      # список релизов
gh release create v1.x.x --notes "..."
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano/topics  # topics

# Из PowerShell (полный путь или просто gh если PATH обновлён):
& "C:\tools\gh\bin\gh.exe" issue list
```

**Если `gh` разлогинился:**
```bash
# Получить токен из git credential manager:
printf 'protocol=https\nhost=github.com\n' | git credential fill | grep password
# Авторизовать:
echo "ghp_TOKEN" | gh auth login --with-token
```

## Частые операции

### Коммит и пуш (из Windows, рабочая директория репо)
```bash
cd "e:/Linux mint/virtual_VM/shared/NAS_Jetson_Nano"
git add <files>
git commit -m "тип: описание"
git push
```

### SSH-команда на Jetson
```bash
# из домашней сети:
ssh -o ConnectTimeout=10 admin@192.168.0.50 "команда"

# из внешней сети (через VPS):
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 \
    "ssh -p 10022 admin@127.0.0.1 'команда'"
```

### Прогнать скрипт на Jetson извне (ProxyJump)
```bash
ssh -o "ProxyCommand=ssh -i ~/.ssh/borovskoy_new_ed25519 -W %h:%p root@95.163.176.103" \
    -p 10022 admin@127.0.0.1 "bash -s" < local_script.sh
```

### Git pull на Jetson
```bash
ssh admin@192.168.0.50 "cd ~/nasa && git pull --ff-only"
```
> ⚠️ На устройстве есть незакоммиченные ручные правки (см. «Расхождение git ↔ устройство») — `git pull` их затрёт.

### Docker Compose на Jetson
```bash
ssh admin@192.168.0.50 "cd ~/nasa && docker compose -f docker/compose/docker-compose.monitoring.yml --env-file config/.env up -d"
```

### Проверить, что бэкапы живы (не верить статусу юнита!)
```bash
ssh admin@192.168.0.50 "ls -lt /mnt/storage/backups/database-dumps/ | head -5"
```

### Создать GitHub issue
```bash
gh issue create \
  --title "Заголовок" \
  --body "Описание" \
  --label "enhancement"
```

### Создать release
```bash
git tag -a v1.x.x -m "описание"
git push origin v1.x.x
gh release create v1.x.x --title "v1.x.x — название" --notes "описание"
```

## Структура проекта

```
docker/compose/   — Docker Compose файлы для всех сервисов
config/           — конфиги (шаблоны); .env — НЕ в git
scripts/          — bash/python скрипты (backup, monitoring, setup, storage)
systemd/          — systemd units (таймеры, сервисы)
docs/             — документация (00–26 + подпапки)
docs/prompts/     — агентные промпты (CODEX_*, Claude, ChatGPT)
docs/quality/     — test plan, matrix, baseline reports
docs/references/  — внешние ссылки (external_docs/ — gitignored)
docs/local/       — локальные runbook'и вне git (.git/info/exclude)
tests/            — автоматические тесты (network, service, storage, backup)
assets/           — фото, схемы, скриншоты
artifacts/        — отчёты аудитов, JSON exports
archive/legacy/   — устаревшие файлы (не удалять, хранить)
.github/          — CI/CD workflows, issue templates
```

> **Полная карта структуры:** `docs/REPOSITORY_STRUCTURE.md`

## Сервисы и порты (Jetson 192.168.0.50)

| Сервис | Порт | URL |
|---|---|---|
| Nextcloud | 8080 | http://192.168.0.50:8080 |
| Immich | 2283 | http://192.168.0.50:2283 |
| LLM Gateway | 8090 | http://192.168.0.50:8090/health |
| API (`homecloud_nasa_api`) + Swagger | 8099 | http://192.168.0.50:8099/docs |
| Netdata | 19999 | http://192.168.0.50:19999 |
| Uptime Kuma | 3001 | http://192.168.0.50:3001 |
| Portainer | 9000 / 9443 | http://192.168.0.50:9000 (9443 — HTTPS) |
| Samba | 445 | `\\192.168.0.50\public`, `\\192.168.0.50\hdd2tb` |
| Beszel Agent | 45876 | внутренний (→ Hub через туннель) |

**Снаружи (VPS `95.163.176.103`) — только через VPN:** Nextcloud :8080/:8443, Immich :2283/:2443,
LLM Gateway :8090/:9443, API :8099, Beszel Hub :8091.
При активном VPN тот же набор доступен по `http://172.29.172.1:<порт>`.

> ⚠️ Внутри домашней LAN все сервисы открыты **любому, кто знает пароль Wi-Fi** — сегментации нет.

## Жёсткие правила

1. **НЕ коммитить** реальные `.env`, пароли, токены, ключи, персональные данные.
2. **НЕ трогать** Amnezia VPN контейнеры на VPS — уронит ~25 VPN клиентов.
3. **НЕ удалять** сетевой профиль LAN на Jetson (на устройстве он называется `nasa-lan`, eth0, 192.168.0.50/24).
4. **НЕ открывать** сервисы напрямую в интернет без отдельного решения. Наружу на VPS допустимы только 22, 443 и 40568/udp.
5. **Destructive команды** (rm -rf, форматирование, DROP DATABASE) — только с явного подтверждения.
6. Перед push: `./scripts/security/check_no_secrets.sh`
7. **НЕ форматировать** `/mnt/hdd2tb` — на нём 1.4 ТБ семейного архива, NTFS оставлен намеренно.
8. Любое значение с пробелом в `config/.env` — **обязательно в кавычках** (см. «Грабли»).
9. Любое сетевое оборудование сначала подключать изолированно к workstation: не вводить в production LAN с активным DHCP и не делать factory reset без явного подтверждения.
10. Deco E4 вводится **в режиме Router** и обязан быть переведён на `192.168.0.1/24` (`More → Advanced → LAN IP`) **до** подключения Jetson. Подсеть `192.168.0.0/24` и адрес `.50` не менять никогда (правило №3).
11. **Не выводить EC220-G5 и не сбрасывать его** до успешной приёмки новой сети — это единственный путь отката.
12. Перед заменой роутера **записать тип WAN-подключения и WAN MAC** со старого роутера. Без них новую сеть не поднять, а старого роутера под рукой уже не будет.

## Workflow (стандартная процедура)

1. Изменения в файлах проекта (Windows)
2. `git add` + `git commit`
3. `git push`
4. При необходимости применить на Jetson: `ssh admin@192.168.0.50 "cd ~/nasa && git pull --ff-only"` (из дома) или через VPS-jump (см. «Частые операции») — **сначала проверить, не затрёт ли ручные правки на устройстве**
5. Перед запуском Nextcloud/Immich/backup: `sudo bash scripts/storage/storage_preflight.sh`
6. Перезапуск затронутых контейнеров (если compose-файлы изменились и preflight прошёл)
7. После крупных изменений: `git tag` + `gh release create`
8. Обновить README и CHANGELOG

## Память

Память о проекте (cross-session): `C:\Users\Alexey\.claude\projects\e--Linux-mint-virtual-VM-shared-NAS-Jetson-Nano\memory\`
Индекс: `MEMORY.md` в той же папке.
