# Старому «железу» новую жизнь: домашнее облако на Jetson Nano и Claude Code

> **Хабы:** Системное администрирование · Open Source · Искусственный интеллект · Self-hosted  
> **Теги:** `selfhosted` `nextcloud` `immich` `jetson-nano` `docker` `homelab` `claude-code` `ai-assisted-dev`  
> **Репозиторий:** [github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)

---

В связи с переездом перебирал дома старые коробки и нашёл NVIDIA Jetson Nano Developer Kit — сын всерьёз занимался робототехникой. Зная, сколько это стоило в своё время, решил поискать, куда его можно применить с учётом современных возможностей AI. В моём случае — это Claude Code, агентная CLI от Anthropic, которую я активно использую в работе.

Принимая во внимание, что у меня постоянно идёт переполнение аккаунта Google, возникла идея сделать локальное решение на базе Jetson. Провёл глубокий поиск подобных проектов и понял, что это реализуемо. Вторым пунктом, который позволил это достаточно просто сделать, стало наличие VPS-сервера — через него был организован доступ к домашнему ресурсу из интернета.

А теперь по порядку: что использовал из железа, какие задачи ставил, как решал.

<cut>

---

## Железо и требования

### Что было в наличии

| Компонент | Характеристики |
|---|---|
| NVIDIA Jetson Nano Dev Kit | 4 GB LPDDR4, ARM64, GPU Maxwell |
| Системный диск | microSD 64 GB |
| Хранилище данных | USB SSD 232 GB → 229 GB (ext4) |
| VPS | Ubuntu 24.04, 2 GB RAM, Вена |
| Роутер | Статический DHCP → Jetson 192.168.0.50 |

**Ключевые ограничения Jetson Nano:**
- Нет swap-раздела — ограничивает выбор тяжёлых сервисов
- Docker 20.10.7 (старый, обновить нетривиально из-за JetPack)
- ARM64 — не все Docker-образы имеют нативные сборки

**Требования к внешнему хранилищу:**
USB SSD — единственный вариант для большого объёма. Требования к энклоужеру:
- Работа в **USB 3.0 BOT-режиме** (не UAS — несовместим с Tegra kernel 4.9)
- Отсутствие перехода в autosuspend при простое
- SCSI timeout не менее 60 секунд
- Стабильный чип без деградации скорости

Итоговый выбор — энклоужер с чипом **JMS583** (152d:a583, 5 Gbps). Write 250 MB/s, Read 172 MB/s после применения quirk:

```bash
# /boot/extlinux/extlinux.conf — добавить к строке APPEND:
usb-storage.quirks=152d:a583:u usbcore.autosuspend=-1
```

Флаг `u` переключает JMS583 в BOT mode — обязательно для Jetson kernel 4.9.

---

## Постановка задачи с Claude Code

Я не писал техническое задание. Я описывал **жизненную ситуацию**, а агент предлагал реализацию, объяснял компромиссы и задавал уточняющие вопросы.

### Задача 1 — структура проекта

```
Приведи проект в порядок. Создай полный проект из данного,
напиши все необходимые подпапки и т.п.
Ориентируйся на использование субагентов
```

Claude Code запустил 4 параллельных субагента:
- Агент A — скрипты диагностики, бэкапа, мониторинга
- Агент B — Docker Compose файлы для всех сервисов
- Агент C — GitHub-инфраструктура: `.github/`, CI/CD, issue templates
- Агент D — архитектурные решения (ADR-документы)

Результат: структурированный репозиторий за один сеанс. Вручную я бы расставлял папки несколько часов.

### Задача 2 — выбор инструментов мониторинга

```
Я хочу попробовать специальные инструменты по контролю типа Zabbix
или иных подобных решений. Проанализируй какие можно использовать.
```

Агент проанализировал 9 инструментов и объяснил почему Zabbix не подходит: требует отдельной PostgreSQL, 500+ MB RAM — при нашем ограничении «нет swap» это риск OOM. Предложил лёгкую связку:

| Инструмент | Назначение | RAM |
|---|---|---|
| Netdata | Real-time метрики | ~80 MB |
| Uptime Kuma | HTTP/TCP мониторы | ~50 MB |
| Portainer | Управление Docker | ~50 MB |
| Beszel | CPU/RAM/Disk история + агенты | ~30 MB |

Суммарно ~210 MB против 500+ MB у Zabbix. Это именно то решение, которое нужно было — без объяснения ограничений Jetson агент мог бы предложить стандартный enterprise-стек.

### Задача 3 — доступ из интернета через VPS

```
У меня есть внешний VPS 193.*.***.*, его можно использовать.
Ты можешь подключиться и проверить данный сервер.
```

Агент подключился по SSH, обнаружил Amnezia VPN (4 контейнера, ~25 клиентов семейного VPN) — не тронул их, установил Docker Compose, настроил UFW, создал nginx конфигурацию для reverse-tunnel. Задокументировал всё найденное.

Этот момент важен: **агент самостоятельно определил, что трогать нельзя**, и зафиксировал ограничение в `AGENTS.md`. Без этого я бы мог случайно уронить VPN у всей семьи.

### AGENTS.md — память агента между сессиями

Это один из главных инсайтов. `AGENTS.md` читается при каждом запуске новой сессии. Там зафиксировано:
- Жёсткие запреты (не трогать Amnezia, не удалять сетевой профиль eth0)
- Аппаратные ограничения (нет swap, ARM64, kernel 4.9)
- Архитектурные решения с обоснованиями
- Рабочий процесс (preflight перед запуском сервисов)

Агент не повторяет ошибки — потому что они записаны. Если строите что-то с AI — начинайте именно с этого файла.

---

## Архитектура решения

### Как устроен доступ из интернета

Jetson Nano находится за домашним роутером в CGNAT — прямого входящего соединения нет. Решение: **reverse SSH tunnel через VPS**.

```
[Телефон/браузер в интернете]
         |
         | HTTPS / HTTP
         v
[VPS 193.*.***.* — Vienna]
    nginx (Docker)
    :8080/:8443  ──┐
    :2283/:2443  ──┤  reverse SSH tunnel (autossh)
    :8090/:9443  ──┤
    :8099        ──┤
    :8091        Beszel Hub (direct)
         |
         | SSH tunnel (исходящий от Jetson)
         v
[Jetson Nano 192.168.0.50 — домашняя сеть]
    Nextcloud    :8080
    Immich       :2283
    LLM Gateway  :8090
    NAS_Jetson_Nano API     :8099
    Samba NAS    :445  (только LAN)
    Netdata      :19999
    Uptime Kuma  :3001
    Portainer    :9000
         |
         | USB 3.0 (5 Gbps)
         v
[JMS583 SSD 229 GB — /mnt/storage]
    nextcloud/data
    immich/library
    db/ (PostgreSQL × 2)
    backups/
```

**Почему autossh, а не WireGuard или Tailscale:**
- WireGuard требует DKMS — несовместим с Tegra kernel 4.9
- Tailscale конфликтует с Amnezia VPN на Android
- autossh: работает через CGNAT, нет внешних зависимостей, `Restart=always`

**HTTPS без домена:**
Let's Encrypt недоступен (нет домена, порт 443 занят Amnezia). Решение: self-signed TLS на alt-портах (:8443/:2443/:9443), срок 10 лет. Браузер предупреждает один раз — принять и забыть.

### Стек Docker-контейнеров

13 контейнеров на одном Jetson Nano 4 GB. Ключевые ограничения при дизайне — mem_limit для каждого контейнера и `restart: always`:

| Контейнер | Образ | Порт | mem_limit |
|---|---|---|---|
| nextcloud | nextcloud:apache | 8080 | 512m |
| nextcloud_db | postgres:16-alpine | — | 512m |
| nextcloud_redis | redis:7-alpine | — | 64m |
| immich_server | immich-server:release | 2283 | 1024m |
| immich_db | pgvecto-rs:pg16 | — | 384m |
| immich_redis | redis:7-alpine | — | 64m |
| immich_microservices | immich-server:release | — | 512m |
| llm_gateway | custom FastAPI | 8090 | 256m |
| nas_jetson_nano_api | custom FastAPI | 8099 | 128m |
| samba | crazymax/samba | 445 | — |
| netdata | netdata:latest | 19999 | 256m |
| uptime_kuma | louislam/uptime-kuma | 3001 | 128m |
| portainer | portainer-ce | 9000 | 128m |

`IMMICH_DISABLE_MACHINE_LEARNING=true` — обязательно. Immich с ML не влезает в 4 GB без swap.

---

## Как доводил проект: шаг за шагом

### Шаг 1 — Docker Compose и базовые сервисы

Начал с Nextcloud + Immich + PostgreSQL. Промпт агенту:

```
Подними Nextcloud и Immich на Jetson Nano.
PostgreSQL для обоих. Данные на /mnt/storage.
Учти: нет swap, 4 GB RAM.
```

Агент написал docker-compose файлы с mem_limit, healthcheck-ами и fail-closed логикой бэкапа (не пишет в microSD если /mnt/storage не смонтирован). Я проверил конфиги — поправил пути, согласовал пароли.

**Проверка работоспособности:**
```bash
docker compose ps          # все контейнеры up
curl -s http://localhost:8080/status.php | python3 -m json.tool
curl -s http://localhost:2283/api/server/ping
```

### Шаг 2 — Мониторинг и алертинг

Хотел понимать: что происходит с системой ночью. Промпт:

```
Настрой Telegram-бот для ежедневного отчёта о состоянии системы.
Что хочу видеть: температуры, RAM, диск, все контейнеры, HTTP статусы.
```

Агент написал bash-скрипт + systemd timer. Каждое утро в 09:00 приходит сообщение:

```
NAS_JETSON_NANO — Daily Report
2026-06-29 09:00 MSK

SYSTEM — nas_jetson_nano-jetson
Uptime: 18h | RAM: 2.3/3.9G | Disk /mnt/storage: 7G/229G (3%)

CONTAINERS
✅ nextcloud: running (restarts: 0)
✅ immich_server: running (restarts: 0)
... (все 13)

LOCAL HTTP
✅ Nextcloud: HTTP 302
✅ Immich: HTTP 200

EXTERNAL ACCESS
✅ Nextcloud via VPS: HTTP 302
✅ Immich via VPS: HTTP 200
```

Дополнительно настроил **Beszel Hub** на VPS — исторические графики CPU/RAM/Disk для обоих серверов:

![Beszel Hub — обзор систем: Jetson Nano + VPS Vienna](../../assets/screenshots/article/beszel_systems_overview.png)

![Beszel Hub — метрики Jetson: CPU ~15%, RAM 2.3 GB, Docker containers](../../assets/screenshots/article/beszel_jetson_metrics.png)

### Шаг 3 — Инфраструктурные тесты (goss)

Чтобы после каждого изменения быть уверен что всё работает:

```bash
# Установка goss ARM64
curl -fsSL https://goss.rocks/install | GOSS_VER=v0.4.9 sh

# Запуск тестов
goss validate --gossfile tests/goss/goss.yaml
```

40 тестов покрывают: порты открыты, systemd-сервисы активны, файлы и директории существуют, HTTP эндпоинты отвечают. Итог: **40/40**.

```
Count: 40, Failed: 0, Skipped: 0
Duration: 4.32s
```

### Шаг 4 — HTTPS и внешний доступ

Android-приложения требуют HTTPS для некоторых функций. Без домена — self-signed:

```bash
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /opt/nas_jetson_nano/nginx/ssl/nas_jetson_nano.key \
  -out /opt/nas_jetson_nano/nginx/ssl/nas_jetson_nano.crt \
  -subj "/CN=nas-jetson-nano" \
  -addext "subjectAltName=IP:193.*.***.*, IP:192.168.0.50"
```

nginx на VPS проксирует через tunnel на alt-портах: `:8443` → Nextcloud, `:2443` → Immich, `:9443` → LLM Gateway. Браузер/приложение предупреждает один раз, дальше — без проблем.

### Шаг 5 — Android клиенты

```
Помоги настроить Immich и Nextcloud на Android.
Сервер доступен по HTTPS с self-signed сертификатом.
Телефон Xiaomi MIUI/HyperOS.
```

Агент написал пошаговую инструкцию учитывая специфику MIUI:
- Battery whitelist для Immich и Nextcloud (иначе убивает фоновый процесс)
- Автозапуск в настройках безопасности
- «Заблокировать в RAM» для стабильного бэкапа

**Immich:** 6 697 фотографий и видео загружено. Автобэкап настроен.

![Immich Android — прогресс бэкапа: 6697/6719 объектов](../../assets/screenshots/article/android_immich_backup_stats.jpg)

**DAVx⁵:** 2 151 контакт синхронизируется через CardDAV. Календарь через CalDAV.

![DAVx⁵ — CalDAV/CardDAV синхронизация настроена](../../assets/screenshots/article/android_davx5_caldav.jpg)

### Шаг 6 — Семейный чат и пользователи

Nextcloud Talk — встроенный мессенджер. Группа «Семья» на 5 человек. История переписки хранится на нашем SSD, не на серверах сторонних сервисов.

Каждому члену семьи — персональная памятка на одну страницу: URL, логин, шаги настройки Android. Никаких технических деталей — только что нажать.

![Nextcloud Talk — чат «Семья»](../../assets/screenshots/article/nextcloud_talk.png)

![Nextcloud — дашборд пользователя](../../assets/screenshots/article/nextcloud_dashboard.png)

### Шаг 7 — NAS_Jetson_Nano API

Последний шаг — REST API поверх всего стека. Зачем? Чтобы управлять системой без SSH и смотреть статистику программно.

```
Создай FastAPI сервис. Пусть он умеет:
- авторизоваться через Nextcloud (JWT)
- читать состояние Docker-контейнеров
- отправлять сообщения в Talk
- показывать статистику Immich
- перезапускать контейнеры по whitelist
Swagger UI обязателен.
```

Агент написал 9 роутеров, Pydantic-модели, JWT middleware, OpenAPI-документацию. Итог — 20 эндпоинтов, доступных через Swagger UI:

![NAS_Jetson_Nano API v0.6.0 — Swagger UI с группами эндпоинтов](../../assets/screenshots/article/nas_jetson_nano_api_swagger.png)

| Группа | Примеры эндпоинтов |
|---|---|
| Система | RAM, CPU, температура, список контейнеров |
| Talk | Список чатов, участники, отправка сообщений |
| Пользователи | Семейные аккаунты, личные сообщения через Talk |
| Фото | Статистика Immich: 6 484 фото, 210 видео, 4.24 GB |
| Действия | Restart контейнера, бэкап по запросу |

---

## Что получилось: итоговая картина

![Immich — фотоархив семьи (6.1 GiB, 228 GB свободно)](../../assets/screenshots/article/immich_web.png)

**Цифры по итогу:**
- 13 Docker-контейнеров, все `up/healthy`
- 6 697 фотографий и видео загружено с телефона
- 2 151 контакт синхронизируется
- 5 членов семьи в чате
- goss 40/40 — инфраструктурные тесты
- Write 250 MB/s, Read 172 MB/s на SSD

**Что заменили:**
- Google Photos → Immich (автобэкап, поиск, альбомы)
- Google Drive / Яндекс.Диск → Nextcloud (файлы, синхронизация)
- Google Contacts → DAVx⁵ + Nextcloud (CardDAV)
- WhatsApp/Telegram-группы → Nextcloud Talk (история на своём SSD)

---

## Честная оценка AI-assisted подхода

**Что получилось хорошо:**

*Скорость.* systemd-юниты, udev-правила, nginx-конфиги, Docker Compose — агент пишет это параллельно, не забывая про детали (mem_limit, restart policy, healthcheck). То, что заняло бы недели освоения — делается за часы объяснений.

*Документация.* ADR (Architecture Decision Records), CHANGELOG, двуязычные инструкции — создаются вместе с реализацией. Решения зафиксированы с обоснованием, а не теряются в голове.

*Системность.* CI/CD в GitHub Actions, secrets-check перед каждым push, shellcheck для bash-скриптов, goss-тесты — агент знает open-source конвенции и применяет их автоматически.

**Что требует контроля человека:**

Агент не знает ваше железо. Нужно объяснять детали: какой чип в USB-мосте, реальное RAM, версию kernel, что на VPS нельзя трогать. Без этого контекста рекомендации будут общими.

Firewall, fstab, пароли — проверять самому. Агент напишет конфиг, но финальная ответственность за безопасность — ваша.

Контекст сессии конечен. Решается `AGENTS.md` и `CLAUDE.md` — файлы, которые агент читает при старте. Там зафиксировано актуальное состояние системы, жёсткие запреты и архитектурные решения.

**Открытые вопросы (честно):**

- Docker 20.10.7 устарел — обновить нетривиально на JetPack
- off-site backup не настроен — restic скрипты готовы, backup на VPS не запущен
- ML в Immich отключён — Jetson 4 GB без swap не тянет распознавание лиц
- SMART у JMS583 базовый — smartmontools 6.6 не поддерживает полный SAT passthrough

---

## Вывод

Jetson Nano из коробки превратился в работающий семейный сервер за несколько вечеров. Семья использует — не тестирует. 6 697 фотографий больше не лежат в Google.

Главное, что я вынес из этого проекта: AI-агент — не волшебная кнопка. Это инструмент, который резко снижает стоимость реализации, если ты умеешь формулировать требования из реальной ситуации. Чем точнее описываешь контекст — тем лучше результат.

Промпты агентов, ADR, Docker Compose, скрипты, памятки пользователей — всё открыто:

**[github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)**
