# CLAUDE.md — NAS_Jetson_Nano

> Этот файл читается Claude Code автоматически при открытии проекта.
> Содержит контекст, команды и правила для работы в этом репозитории.

## Проект

**NAS_Jetson_Nano** — приватный семейный облачный сервер на NVIDIA Jetson Nano 4 GB + USB HDD.
Заменяет Google Photos (→ Immich), Google Drive (→ Nextcloud), облачный NAS (→ Samba).

- GitHub: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano
- Owner: AlexeyBorovskoy (a.e.borovskoy@gmail.com)
- Текущий релиз: v1.4.0 — JMS583 USB SSD enclosure, UAS quirk, goss 40/40
- Основная ветка: `main`

## Операционное состояние

**Состояние на 2026-08-01 (live-аудит через VPS-jump): v1.4.0 — JMS583 ✅ подключён (USB 3.0, 5 Gbps). Docker ✅ все 13 контейнеров up (healthy). UAS quirk активен в ядре. Talk-бот (Phase A) ✅ running.**

> ⚠️ **Расхождение git ↔ устройство.** Живой Jetson работает на СТАРОМ, до-переименовочном деплое. Rename `NASA → NAS_Jetson_Nano` сделан только в git — **на устройство не выкатан**. Фактически на устройстве:
> - Репо: **`~/nasa`**, remote `github.com/AlexeyBorovskoy/Nasa_home.git` (HEAD `0f9fd0f`, ветка `main`)
> - Контейнеры: префикс **`homecloud_*`** (не `nas_jetson_nano_*`), API-контейнер `homecloud_nasa_api`
> - systemd-юниты: префикс **`nasa-*`** (не `nas_jetson_nano-*`)
> - Логи мониторинга: **`/var/log/nasa-monitor/`**
> - LAN `192.168.0.50:22` НЕ доступен с Windows-машины — только через VPS-jump (см. «Железо и доступ»).
> Полная миграция устройства на переименованный layout — отдельная неначатая задача (backup + окно обслуживания).

| Компонент | Статус | Детали |
|---|---|---|
| Jetson Nano | ✅ up | 192.168.0.50 |
| Keenetic Omni KN-1410 | 📋 planned extender | Physical device inventoried; not connected/configured; see `docs/25_KEENETIC_OMNI_KN1410.md` |
| SSD `/dev/sda1` → `/mnt/storage` | ✅ **mounted** | 229G, 5% use (9.6G) |
| USB SSD энклоужер | ✅ **JMS583** (152d:a583) | USB 3.0 SuperSpeed, порт 2-1.3, 5000 Mbps |
| USB SSD порт | ✅ **порт 2** | preboot service делает power cycle при boot |
| SCSI timeout | ✅ **120s** | udev правило активно |
| `usbcore.autosuspend=-1` | ✅ **kernel** | `/proc/cmdline` |
| `usb-storage.quirks=...,152d:a583:u` | ✅ **active** | UAS отключён, usb-storage BOT. Write **250 MB/s**, Read 172 MB/s. Нет USB ошибок. |
| USB watchdog timer | ✅ **active (waiting)** | `nasa-usb-watchdog.timer` включён |
| USB pre-boot service | ✅ active | `nasa-usb-preboot.service` — power cycle до монтирования |
| USB error monitor | ✅ active | `nasa-usb-monitor.service` — Telegram при USB ошибках (error -71 + JMS583 stream errors) |
| JMS583 health timer | ✅ **enabled** | `nasa-jms583-health.timer` (service disabled, запускается таймером) |
| SSD hotplug auto-recovery | ✅ active | `nasa-ssd-recovery.service` — udev(`sda1`) → mount → preflight → Docker → контейнеры |
| VPS reverse tunnel | ✅ **enabled** | `nasa-tunnel.service` — API :8099 наружу через VPS |
| Docker daemon | ✅ **active** | 13 контейнеров `homecloud_*` up, healthy |
| Talk-бот (Phase A) | ✅ **running** | `homecloud_nasa_api`, room `37pcobmf`, триггер `нас`. Хирургический backport на `~/nasa` (см. память). |
| immich-microservices | ✅ **mem_limit 512m** | Применён и перезапущен 2026-06-28 |
| Beszel Hub (VPS:8091) | ✅ up | admin@nas_jetson_nano.local / пароль в config/secrets.json |
| Beszel Agent Jetson (45876) | ✅ up | status=up |
| Beszel Agent VPS (45877) | ✅ up | v0.18.7 |
| VPS nginx HTTP | ✅ live | :8080 Nextcloud · :2283 Immich · :8090 LLM |
| VPS nginx HTTPS | ✅ live | :8443 Nextcloud · :2443 Immich · :9443 LLM (self-signed 10y) |
| Nextcloud контейнер | ✅ **up, healthy** | |
| Android apps | ✅ установлены | Immich + Nextcloud из Play Store, DAVx⁵ APK v4.5.14 |
| Immich Android | ✅ **настроен** | Логин: admin@nas_jetson_nano.local, сервер: http://193.8.215.130:2283 |
| Immich backup | ✅ **активирован** | 31 альбом, 6710 фото/видео в очереди |

**🔑 Ротация паролей (2026-06-28):** Все пароли изменены на новые. Git history очищен (filter-repo). Актуальные — в `config/secrets.json`.

**🔧 Если SSD упал — восстановление АВТОМАТИЧЕСКОЕ:**
> Просто физически переткни кабель SSD. Система сделает остальное сама:
> udev(`sda1`) → `nasa-ssd-recovery.service` → mount → preflight → Docker → все 13 контейнеров
> Лог: `journalctl -u nasa-ssd-recovery` или `/var/log/nasa-monitor/ssd-recovery.log`
>
> Если авто-recovery не сработал (маловероятно):
> 1. (через VPS-jump) `sudo -S systemctl start nasa-ssd-recovery.service`
>    PASS — из `config/secrets.json`

**🔜 Ближайшие задачи:**
- Nextcloud Android: `https://193.8.215.130:8443`, admin / пароль из secrets.json
- DAVx⁵: `https://193.8.215.130:8443/remote.php/dav`
- Immich локальный URL: `http://192.168.0.50:2283` в Настройки → Сеть (WiFi: TP-Link_828C)
- Restic off-site backup: после подключения 2 ТБ HDD

**✅ Hardware**: JMS583 (152d:a583, USB 3.0, 5 Gbps) — подключён и работает. Write **250 MB/s**, Read 172 MB/s. UAS quirk активен (usb-storage BOT). Нет USB ошибок. SMART: smartmontools 6.6 слишком старый (SAT passthrough — базовые данные есть). RTL9210B-CG — заменён.

## Железо и доступ

| Компонент | Адрес / Путь | Примечание |
|---|---|---|
| Jetson Nano | `192.168.0.50` | LAN, статический IP |
| SSH на Jetson | `ssh admin@192.168.0.50` | key-based, из Git Bash |
| SSH через VPS | `ssh root@193.8.215.130` → `ssh -p 10022 admin@127.0.0.1` | текущий рабочий путь из внешней сети |
| sudo на Jetson | `sudo -S <cmd>` | пароль брать только из приватного runtime/local secret storage; не коммитить |
| VPS (Vienna) | `193.8.215.130` | `ssh -i ~/.ssh/borovskoy_new_ed25519 root@193.8.215.130` |
| Keenetic Omni KN-1410 | IP pending | Planned Wi-Fi extender; label secrets stay local; factory reset only after explicit confirmation |
| Vostro 15 ML-узел | `192.168.0.60` (план) | 🔧 onboarding: Dell Vostro 15 (2018, tag `H7YB9L2`) → always-on Immich ML-узел. См. `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md` |
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
git commit -m "тип: описание\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push
```

### SSH-команда на Jetson
```bash
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no admin@192.168.0.50 "команда"
```

### Git pull на Jetson
```bash
ssh admin@192.168.0.50 "cd ~/nasa && git pull --ff-only"
```

### Docker Compose на Jetson
```bash
ssh admin@192.168.0.50 "cd ~/nasa && docker compose -f docker/compose/docker-compose.monitoring.yml --env-file config/.env up -d"
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
docs/             — документация (00–24 + подпапки)
docs/prompts/     — агентные промпты (CODEX_*, Claude, ChatGPT)
docs/quality/     — test plan, matrix, baseline reports
docs/references/  — внешние ссылки (external_docs/ — gitignored)
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
| Nextcloud | 8080 | http://192.168.0.50:8080 · live after controlled start |
| Immich | 2283 | http://192.168.0.50:2283 |
| LLM Gateway | 8090 | http://192.168.0.50:8090 |
| API (`homecloud_nasa_api`) + Swagger | 8099 | http://192.168.0.50:8099/docs |
| Netdata | 19999 | http://192.168.0.50:19999 |
| Uptime Kuma | 3001 | http://192.168.0.50:3001 |
| Portainer | 9000 | http://192.168.0.50:9000 |
| Beszel Agent | 45876 | внутренний (→ Hub через tunnel) |

VPS (193.8.215.130): Nextcloud :8080, Immich :2283, LLM Gateway :8090
**Beszel Hub: http://193.8.215.130:8091** (login: admin@nas_jetson_nano.local / `$BESZEL_ADMIN_PASSWORD` — см. config/secrets.json)
Jetson уже добавлен: `jetson-nano` → `127.0.0.1:45876`, status=up

## Жёсткие правила

1. **НЕ коммитить** реальные `.env`, пароли, токены, ключи, персональные данные.
2. **НЕ трогать** Amnezia VPN контейнеры на VPS — уронит ~25 VPN клиентов.
3. **НЕ удалять** сетевой профиль `nas_jetson_nano-lan` на Jetson (eth0, 192.168.0.50/24).
4. **НЕ открывать** сервисы напрямую в интернет без отдельного решения.
5. **Destructive команды** (rm -rf, форматирование, DROP DATABASE) — только с явного подтверждения.
6. Перед push: `./scripts/security/check_no_secrets.sh`
7. Keenetic Omni KN-1410 сначала подключать изолированно к workstation: не вводить в production LAN с активным DHCP и не делать factory reset без явного подтверждения.

## Workflow (стандартная процедура)

1. Изменения в файлах проекта (Windows)
2. `git add` + `git commit` (с Co-Authored-By)
3. `git push`
4. `ssh admin@192.168.0.50 "cd ~/nasa && git pull --ff-only"` или через VPS `ssh root@193.8.215.130 "ssh -p 10022 admin@127.0.0.1 'cd ~/nasa && git pull --ff-only'"` (если нужно применить на Jetson)
5. Перед запуском Nextcloud/Immich/backup: `sudo bash scripts/storage/storage_preflight.sh`
6. Перезапуск затронутых контейнеров (если compose-файлы изменились и preflight прошёл)
7. После крупных изменений: `git tag` + `gh release create`
8. Обновить README и CHANGELOG

## Память

Память о проекте (cross-session): `C:\Users\Alexey\.claude\projects\e--Linux-mint-virtual-VM-shared-NAS_Jetson_Nano\memory\`
Индекс: `MEMORY.md` в той же папке.
