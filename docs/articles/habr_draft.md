# Домашнее облако на Jetson Nano: задумал я, реализовал Claude Code

> **Платформы:** [Habr.com](https://habr.com)  
> **Хабы:** Системное администрирование · Open Source · Искусственный интеллект · Self-hosted  
> **Теги:** `selfhosted` `nextcloud` `immich` `jetson-nano` `docker` `homelab` `claude-code` `ai-assisted-dev` `usb-storage`  
> **Статус проекта (июнь 2026):** v1.4.0 · NAS_Jetson_Nano API v0.6.0 · семья подключена · goss 40/40
> **Репозиторий:** [github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)

---

Когда Google Photos урезал бесплатное место, я нашёл на полке Jetson Nano, который год пылился после ML-экспериментов. Рядом стоял внешний SSD от сына. Идея была простая: поднять своё облако, заменить Google Photos и Google Drive, добавить семейный чат.

Проблема: у меня нет времени разбираться в Immich, Nextcloud, Docker Compose и systemd с нуля. Тогда я попробовал доверить реализацию **Claude Code** — агентной CLI от Anthropic. Это история о том, что получилось. И о трёх USB-инцидентах, которые чуть не всё сломали.

<cut>

## Это не инструкция «как поднять Nextcloud»

Таких на Хабре достаточно. Это рефлексия о том, как **AI-assisted разработка меняет подход к домашним проектам**: ты описываешь что хочешь, ИИ строит, ты решаешь ключевые вещи и проверяешь результат.

Спойлер: я потратил больше времени на формулировку требований, чем на написание кода.

---

## Железо и исходная точка

- **NVIDIA Jetson Nano Developer Kit** — лежал с 2021 года, 4 GB LPDDR4, ARM64, GPU Maxwell
- **microSD 64 GB** — системный диск
- **USB SSD 232 GB** — всё пользовательское хранилище (спойлер: первый был проблемным)
- **VPS в Вене** — уже был для семейного VPN Amnezia (~25 клиентов, не трогать!)
- **Роутер** — Jetson получил статический IP `192.168.0.50`

Ключевые ограничения Jetson Nano: **нет swap, 4 GB RAM, Docker 20.10.7** (старый, обновить нетривиально из-за JetPack зависимостей). Это навязывает жёсткий выбор компонентов — тяжёлые решения типа Zabbix или OpenMediaVault не подходят.

---

## Как выглядел процесс с Claude Code

Я не давал длинные технические задания. Я описывал **намерение**, а агент строил реализацию.

**Промпт 1 — структура проекта:**

```
Приведи проект в порядок. Создай полный проект из данного,
напиши все необходимые подпапки и т.п.
Ориентируйся на использование субагентов
```

Claude Code запустил 4 параллельных субагента:
- Агент A — скрипты диагностики и бэкапа
- Агент B — Docker Compose файлы (8 сервисов)
- Агент C — GitHub-инфраструктура (`.github/`, CI/CD)
- Агент D — ADR-документы (Architecture Decision Records)

Я только отвечал на уточняющие вопросы.

**Промпт 2 — мониторинг:**

```
Я хочу попробовать специальные инструменты по контролю типа zabbix
или иных подобных решений. Проанализируй какие можно использовать.
```

Агент проанализировал 9 инструментов и объяснил, почему **Zabbix не подходит** (нужна 3-я PostgreSQL, 500+ MB RAM → OOM на Jetson без swap). Предложил Netdata + Uptime Kuma + Portainer (~220 MB суммарно). Аргументы были технически корректны.

**Промпт 3 — VPS:**

```
У меня есть внешний VPS 193.8.215.130 его можно использовать.
Ты можешь подключиться и проверить данный сервер.
```

Агент подключился через SSH, обнаружил Amnezia VPN (4 контейнера — семейный VPN ~25 клиентов), **не тронул их**, установил Docker Compose, настроил UFW, создал nginx reverse-tunnel конфигурацию и задокументировал всё.

### Момент, когда всё чуть не сломалось

Я сначала хотел изменить WireGuard-конфиг VPS через SSH. Агент предупредил — я не послушал и в другой раз уронил VPN у всей семьи на 40 минут.

Теперь это жёсткое правило в `AGENTS.md`:

```
Никогда не трогать Amnezia-сервер через SSH или wg set.
Только через десктоп-приложение Amnezia.
```

Агент теперь это знает. И напоминает при каждой попытке.

### AGENTS.md — это не документ, это память агента

`AGENTS.md` читается агентом при старте каждой сессии. Там зафиксированы ограничения железа, жёсткие правила и архитектурные решения. Агент не повторяет прошлые ошибки — потому что они записаны.

Если вы строите что-то с AI-агентом — начинайте именно с этого файла.

---

## Архитектура

```
Android / Windows / macOS (LAN)
    ├─ Nextcloud App → :8080
    ├─ Immich App → :2283
    ├─ SMB \\jetson-nas\public → :445
    └─ SSH / SFTP

             Jetson Nano 192.168.0.50
         ┌─────────────────────────────────┐
         │ homecloud_nextcloud       :8080  │
         │   + Talk «Семья» (5 чел)        │
         │ homecloud_immich          :2283  │
         │ homecloud_llm_gateway     :8090  │
         │ homecloud_nas_jetson_nano_api        :8099  │  ← v0.6.0
         │ homecloud_samba            :445  │
         │ Netdata + Uptime Kuma + Portainer│
         └─────────────┬───────────────────┘
                       │ USB 3.0 SuperSpeed (5 Gbps)
               /mnt/storage (JMS583 SSD, 229 GB, 250 MB/s)

Внешний доступ (CGNAT → reverse SSH tunnel):
  Jetson → autossh → VPS nginx → интернет
  :8080/:8443  Nextcloud
  :2283/:2443  Immich
  :8090/:9443  LLM Gateway
  :8099        NAS_Jetson_Nano API Swagger
  :8091        Beszel Hub (мониторинг)
```

**Почему не WireGuard и не Tailscale?** WireGuard требует DKMS — несовместим с Tegra kernel 4.9. Tailscale конфликтует с Amnezia на Android. Решение — autossh reverse SSH tunnel: надёжно, без зависимостей, работает через CGNAT. (ADR-0003, ADR-0004, ADR-0005)

**HTTPS без домена:** Let's Encrypt недоступен (нет домена, порт 443 занят Amnezia). Решение — self-signed TLS на alt-портах (:8443/:2443/:9443), срок 10 лет. Браузер показывает предупреждение один раз — принять и забыть. (ADR-0006)

---

## Три USB-инцидента

Это центральный сюжет. Не архитектура — а реальные поломки.

### Инцидент 1 — error -71 (2026-06-23)

Ночью пришёл алерт в Telegram. SSD исчез с USB-шины, Docker упал, данные недоступны. В `dmesg`:

```
usb 2-1.3: USB disconnect, device number 3
sd 0:0:0:0: [sda] tag#0 FAILED Result: hostbyte=DID_ERROR
```

Причина: Linux по умолчанию переводит USB-устройства в autosuspend через 2 секунды простоя. RTL9210B-CG (чип внутри DEXP-бокса) не умел из него выходить без физического переподключения.

Решение: `usbcore.autosuspend=-1` в `extlinux.conf`, SCSI timeout 120s через udev-правило.

### Инцидент 2 — порт 4 сломан аппаратно (2026-06-26)

После очередного `error -71` выяснилось: проблема не только в autosuspend. Порт 4 USB-хаба физически не обеспечивает достаточно тока. Решение простое — переткнуть кабель в порт 2.

### Инцидент 3 — CRLF в bash shebang

Watchdog-скрипт написан на Windows и закоммичен через git. При клоне на Jetson `#!/bin/bash` превратился в `#!/bin/bash\r` — невалидный shebang. Скрипт молчал. Системный watchdog не работал 4+ часов.

Решение: `.gitattributes` с `*.sh text eol=lf`.

### Итог: RTL9210B-CG заменён на JMS583

RTL9210B-CG деградировал USB 3.0 до USB 2.0 (~40 MB/s), блокировал SMART-данные. Заказал JMS583 — другой класс чипа.

После замены: Write **250 MB/s**, Read **172 MB/s**. Нет ни одного `error -71`.

Но JMS583 с UAS-режимом не дружит с Jetson kernel 4.9:

```bash
# /boot/extlinux/extlinux.conf — добавить к APPEND:
usb-storage.quirks=152d:a583:u usbcore.autosuspend=-1
```

После quirk `u` (BOT mode) скорость записи выросла с 8 MB/s до 250 MB/s.

**Итоговая инфраструктура надёжности USB:**

- `nas_jetson_nano-usb-preboot.service` — power cycle USB-порта при каждом boot (до монтирования)
- `nas_jetson_nano-usb-monitor.service` — dmesg watcher, Telegram alert при первом `error -71`
- `nas_jetson_nano-ssd-recovery.service` — udev hotplug: подключил кабель → mount → preflight → Docker start автоматически

---

## Android: миграция с Google

**Immich — замена Google Photos:**

6697 фото и видео загружены с телефона. Автобэкап настроен. Приложение не отличается от Google Photos визуально — те же альбомы, карта, поиск по лицам (ML отключён на Jetson, работает только базовый поиск).

![Immich — фотоархив (6.1 GiB, 228 GB свободно)](../../assets/screenshots/article/immich_web.png)

**DAVx⁵ — замена Google Contacts:**

2151 контакт синхронизируется через CalDAV/CardDAV. Установка: APK с официального сайта (не из Play Store — там старая версия), добавить аккаунт `https://193.8.215.130:8443/remote.php/dav`, принять self-signed сертификат.

**Nextcloud — файлы и дашборд:**

Документы, фото через браузер, синхронизация папок. Встроенный календарь подтягивает дни рождения из контактов — видно прямо на дашборде.

![Nextcloud — дашборд](../../assets/screenshots/article/nextcloud_dashboard.png)

**MIUI/HyperOS специфика (для владельцев Xiaomi):**

Immich и Nextcloud нужно добавить в battery whitelist, включить автозапуск и разрешить работу в фоне через MIUI → Безопасность → Разрешения приложений. Без этого бэкап Immich работает только когда телефон в руках. Подробнее: `docs/android/XIAOMI_MIUI_QUIRKS.md`.

---

## Семья подключилась: Talk и NAS_Jetson_Nano API

### Nextcloud Talk «Семья»

Nextcloud Talk — встроенный мессенджер. Создал группу «Семья» (5 человек). История переписки хранится на нашем SSD, не на серверах Telegram или WhatsApp.

![Nextcloud Talk — чат «Семья»](../../assets/screenshots/article/nextcloud_talk.png)

Каждому члену семьи отправил персональную памятку на одну страницу: URL, логин, шаги настройки на Android.

### NAS_Jetson_Nano API v0.6.0 — 20 эндпоинтов

Параллельно попросил Claude Code построить REST API поверх всего стека. Зачем? Чтобы скриптовать действия, смотреть статистику и управлять контейнерами без SSH.

| Группа | Что делает |
|---|---|
| Система | RAM, CPU, диск, температура, контейнеры |
| Хранилище | SSD статус, бэкапы |
| Talk | Список комнат, участники, отправка сообщений |
| Пользователи | Семейные аккаунты, личные DM через Talk |
| Фото | Immich: 6484 фото, 210 видео, 4.24 GB |
| Действия | Restart контейнера, бэкап по запросу |

![NAS_Jetson_Nano API v0.6.0 — Swagger UI](../../assets/screenshots/article/nas_jetson_nano_api_swagger.png)

Промпт, с которого начался API:

```
Создай FastAPI сервис nas_jetson_nano-api. Пусть он умеет авторизоваться
через Nextcloud OCS, читать состояние Docker-контейнеров,
отправлять сообщения в Talk и показывать статистику Immich.
JWT токен — от Nextcloud. Swagger UI обязателен.
```

Агент написал 9 роутеров, pydantic-модели, config через pydantic-settings, JWT middleware и OpenAPI-документацию. Всё в `services/nas_jetson_nano-api/`, деплой через Docker Compose.

---

## Мониторинг и наблюдаемость

**Beszel Hub** — основной инструмент мониторинга. Лёгкий (Go бинарь), показывает CPU/RAM/Disk/Network в реальном времени и historical charts. Hub живёт на VPS, агенты на Jetson и VPS.

![Beszel — обзор систем: Jetson Nano + VPS Vienna](../../assets/screenshots/article/beszel_systems_overview.png)

![Beszel — метрики Jetson: CPU 14–19%, RAM 2.3 GB, Docker containers](../../assets/screenshots/article/beszel_jetson_metrics.png)

Что видно: CPU Jetson ~15% под нагрузкой 13 контейнеров. RAM ~2.3 GB из 3.87 GB. Docker containers стабильны — нет пиков, нет restarts.

**Telegram daily report в 09:00:**

Каждое утро приходит сообщение с состоянием системы: все 13 контейнеров ✅, LOCAL HTTP ✅, EXTERNAL ACCESS ✅, температура, RAM, диск. Реализован как systemd timer + bash скрипт + Telegram Bot API.

**goss 40/40** — инфраструктурные тесты: порты открыты, сервисы активны, файлы существуют, HTTP отвечает. Запускается вручную после изменений.

---

## Честная оценка подхода

**Плюсы:**

- **Скорость** — то, что заняло бы недели, делается за часы. Systemd-юниты, udev-правила, nginx-конфиг, Docker Compose — агент пишет всё это параллельно.
- **Документация** — ADR, CHANGELOG, двуязычные доки, TEST_PLAN — создаются вместе с кодом. Я бы сам так не делал.
- **Ошибки зафиксированы** — VPN-инцидент, CGNAT-сюрприз, CRLF-баг — всё в ADR и постмортемах. Не теряются между сессиями.
- **GitHub-стандарт** — `.github/`, CI/CD, badge-линейка, CODEOWNERS — агент знает конвенции open-source.

**Минусы:**

- Агент **не знает ваше железо** — нужно объяснять детали (USB-SATA мост, реальное RAM, версия kernel).
- **Финальная проверка — ваша** — firewall, fstab, пароли надо читать и проверять самому.
- **Контекст сессии конечен** — решается хорошим `AGENTS.md` и `CLAUDE.md`. Без этих файлов каждая сессия начинается с нуля.

**Открытые вопросы (честно):**

- Docker 20.10.7 устарел — обновление нетривиально на JetPack (зависимости Tegra)
- off-site backup не настроен — restic скрипты есть, backup на VPS не запущен
- SMART у JMS583 базовый — smartmontools 6.6 не поддерживает полный SAT passthrough
- ML в Immich отключён — нет распознавания лиц и объектов (Jetson 4 GB + нет swap)

---

## Как повторить: Quick Start

Требования: любой ARM64/x86 с 4+ GB RAM, Docker Compose v2, VPS (опционально для внешнего доступа).

```bash
git clone https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano
cd NAS_Jetson_Nano
cp config/.env.example config/.env
# Заполнить config/.env — пароли, VPS_HOST, Telegram token
sudo bash scripts/storage/storage_preflight.sh
docker compose -f docker/compose/docker-compose.nextcloud.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.immich.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.monitoring.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d
```

Проверка:

```bash
# Установить goss (ARM64):
curl -fsSL https://goss.rocks/install | GOSS_VER=v0.4.9 sh
goss validate --gossfile tests/goss/goss.yaml
# Ожидаемый результат: 40/40
```

Подробнее: `docs/00_QUICK_START.md` и `docs/android/ANDROID_SETUP.md`.

---

## Итог

Семейное облако работает. 6697 фотографий загружено. 2151 контакт синхронизирован. Чат «Семья» работает на нашем железе. Система пережила три USB-инцидента и теперь восстанавливается автоматически — просто переткни кабель.

**Что дал AI-assisted подход:**
- Скорость: проект от нуля до production за несколько вечеров
- Системность: ADR, CI, двуязычная документация — вещи которые я бы откладывал месяцами
- Честность: агент фиксирует ошибки, а не замалчивает

**Что впереди:**
- Restic off-site backup на VPS
- Ollama local AI на Jetson (Stage 3)
- Let's Encrypt когда появится домен

**GitHub:** [AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano) — промпты, ADR, Docker Compose, скрипты, памятки пользователей — всё открыто.
