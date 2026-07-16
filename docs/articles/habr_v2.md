# USB убивал систему трижды. Домашнее облако на Jetson Nano и Claude Code

> **Хабы:** Системное администрирование · Open Source · Искусственный интеллект · Self-hosted  
> **Теги:** `selfhosted` `nextcloud` `immich` `jetson-nano` `docker` `homelab` `claude-code` `usb-storage`  
> **Репозиторий:** [github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)

---

В два часа ночи пришёл алерт в Telegram: SSD исчез с USB-шины, Docker упал, семейные фотографии недоступны. Это был второй раз за неделю. Я не писал watchdog-сервис, который в итоге решил проблему — его написал Claude Code. Я только объяснял что происходит.

<cut>

## Железо

NVIDIA Jetson Nano Developer Kit — лежал с 2021 года после ML-экспериментов. 4 GB LPDDR4, ARM64, GPU Maxwell, Docker 20.10.7 (обновить нетривиально из-за JetPack зависимостей). Системный диск — microSD 64 GB. Хранилище — внешний USB SSD 232 GB. VPS в Вене — уже был для семейного VPN Amnezia (~25 клиентов, не трогать).

Ключевое ограничение: **нет swap**. Это отсекает тяжёлые решения — Zabbix (нужна 3-я PostgreSQL, 500+ MB RAM), OpenMediaVault (захватывает систему целиком). Остаётся собирать гибрид.

Цель: заменить Google Photos (→ Immich), Google Drive (→ Nextcloud), добавить семейный чат и мониторинг. Всё на одном Jetson, доступно из интернета через CGNAT.

---

## Как мы строили это с Claude Code

Я не давал длинных технических заданий. Описывал намерение — агент строил реализацию.

**Промпт 1:**
```
Приведи проект в порядок. Создай полный проект из данного,
напиши все необходимые подпапки и т.п.
Ориентируйся на использование субагентов
```

Claude Code запустил 4 параллельных субагента: скрипты диагностики и бэкапа, Docker Compose файлы (8 сервисов), GitHub-инфраструктура (`.github/`, CI/CD), ADR-документы. Я отвечал на уточняющие вопросы.

**Промпт 2:**
```
У меня есть внешний VPS 193.8.215.130, его можно использовать.
Ты можешь подключиться и проверить данный сервер.
```

Агент подключился по SSH, обнаружил Amnezia VPN (4 контейнера, ~25 клиентов семейного VPN) — **не тронул их**, установил Docker Compose, настроил UFW, создал nginx reverse-tunnel конфигурацию. Всё задокументировал.

Тут я допустил ошибку. Сам, в другой сессии, полез менять WireGuard-конфиг VPS руками. Уронил VPN у всей семьи на 40 минут. Теперь в `AGENTS.md` жёсткое правило:

```
Никогда не трогать Amnezia-сервер через SSH или wg set.
Только через десктоп-приложение Amnezia.
```

`AGENTS.md` — это не документ. Это **память агента между сессиями**. Он читается при старте каждой сессии. Агент не повторяет прошлые ошибки — потому что они записаны. Если строите что-то с AI — начинайте с этого файла.

---

## Три USB-инцидента

Это главное в статье. Не архитектура — реальные поломки.

### Инцидент 1 — error -71

`2026-06-23, 02:14 MSK.` SSD исчез с шины. В `dmesg`:

```
usb 2-1.3: USB disconnect, device number 3
sd 0:0:0:0: [sda] tag#0 FAILED Result: hostbyte=DID_ERROR
Buffer I/O error on dev sda1, logical block 0
```

Docker упал. 13 контейнеров вниз. Данные недоступны. Физически переткнул кабель — всё поднялось.

Причина: Linux переводит USB-устройства в autosuspend через 2 секунды простоя. RTL9210B-CG (чип внутри DEXP-бокса) не умел из него выходить без физического переподключения.

Решение от агента:
```bash
# udev-правило — отключить autosuspend для этого устройства
SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="5411", \
    ATTR{power/control}="on"

# extlinux.conf — глобально
APPEND ... usbcore.autosuspend=-1
```

Добавили SCSI timeout 120s. Установили Beszel Hub на VPS для мониторинга.

### Инцидент 2 — порт 4 сломан

`2026-06-26.` Снова `error -71`. После диагностики выяснилось: проблема не только в autosuspend. Порт 4 на USB-хабе физически не обеспечивает достаточно тока при нагрузке. Аппаратный дефект.

Решение: переткнуть кабель в порт 2. Watchdog обновили: `PORT=2`.

### Инцидент 3 — CRLF в bash shebang

`2026-06-26, тот же день.` Watchdog-скрипт написан на Windows и закоммичен через git. При клоне на Jetson произошло:

```bash
# Было в файле после git checkout на Jetson:
#!/bin/bash\r   ← невалидный shebang, скрипт молча не работал
```

Git на Windows конвертировал LF → CRLF. Watchdog не работал 4+ часов. Мы не знали.

Решение:
```bash
# .gitattributes
*.sh text eol=lf
```

После этого git перестал трогать окончания строк в shell-скриптах.

### Финал: RTL9210B-CG → JMS583

RTL9210B-CG деградировал USB 3.0 до USB 2.0 (~40 MB/s), блокировал SMART-данные. Заказал замену — JMS583 (другой класс чипа, Realtek JMS583).

После замены Write **250 MB/s**, Read **172 MB/s**. Нет ни одного `error -71`.

Но JMS583 с UAS-режимом не дружит с Jetson kernel 4.9 — нужен quirk:

```bash
# extlinux.conf — добавить к строке APPEND:
usb-storage.quirks=152d:a583:u
```

Флаг `u` переключает в BOT mode. Скорость записи: 8 MB/s → 250 MB/s.

**Итоговая инфраструктура надёжности USB — три systemd-сервиса:**

- `nas_jetson_nano-usb-preboot.service` — power cycle USB-порта при каждом boot, до монтирования
- `nas_jetson_nano-usb-monitor.service` — dmesg watcher, Telegram alert при первом `error -71`
- `nas_jetson_nano-ssd-recovery.service` — udev hotplug: подключил кабель → mount → preflight → docker start

Сейчас восстановление автоматическое. Просто переткни кабель.

---

## Что работает сейчас

13 Docker-контейнеров, 4 семейных пользователя, 6 697 фотографий загружено с телефона.

**Immich** заменил Google Photos. Автобэкап с Android. Поиск по датам и альбомам — работает. ML (поиск по лицам) отключён: Jetson 4 GB без swap не тянет.

![Immich — фотоархив семьи (6.1 GiB, 228 GB свободно)](../../assets/screenshots/article/immich_web.png)

**Nextcloud + DAVx⁵** — файлы и 2 151 контакт синхронизируются. Nextcloud Talk «Семья» — групповой чат на 5 человек. История переписки хранится на нашем SSD.

![Nextcloud — дашборд с чатом «Семья» в левой панели](../../assets/screenshots/article/nextcloud_dashboard.png)

**Мониторинг:** Beszel Hub на VPS (Go бинарь, лёгкий) показывает CPU/RAM/Disk обоих серверов. Telegram daily report в 09:00 — все 13 контейнеров, HTTP статусы, температура. goss 40/40 — инфраструктурные тесты.

![Beszel Hub — Jetson Nano: CPU ~15%, RAM 2.3 GB, Docker containers stacked](../../assets/screenshots/article/beszel_jetson_metrics.png)

**NAS_Jetson_Nano API v0.6.0** — FastAPI поверх всего стека. 20 эндпоинтов: состояние системы, Talk, пользователи, статистика Immich, restart контейнеров. JWT через Nextcloud OCS. Swagger UI доступен внешне.

![NAS_Jetson_Nano API v0.6.0 — Swagger UI](../../assets/screenshots/article/nas_jetson_nano_api_swagger.png)

**Внешний доступ:** autossh reverse SSH tunnel через VPS (CGNAT bypass). WireGuard и Tailscale отклонены — первый несовместим с Tegra kernel 4.9, второй конфликтует с Amnezia на Android. HTTPS на alt-портах с self-signed сертификатом 10 лет (нет домена, порт 443 занят Amnezia).

---

## Честная оценка

**Что AI-assisted подход дал реально:**

Скорость. systemd-юниты, udev-правила, nginx-конфиг, Docker Compose — агент пишет это параллельно с кодом. ADR, CHANGELOG, двуязычная документация создаются вместе с реализацией. Ошибки (VPN-инцидент, CRLF-баг) фиксируются в `AGENTS.md` и не повторяются.

**Что требует контроля человека:**

Агент не знает ваше железо — нужно объяснять детали (USB-SATA чип, реальное RAM, версия kernel). Firewall, fstab, пароли — читать и проверять самому. Контекст сессии конечен — решается `AGENTS.md` и `CLAUDE.md` с актуальным состоянием системы.

**Открытые вопросы (честно):**

- Docker 20.10.7 устарел — обновить нетривиально на JetPack
- off-site backup не настроен — restic скрипты готовы, но backup на VPS не запущен
- SMART у JMS583 базовый — smartmontools 6.6 не поддерживает полный SAT passthrough

---

Система работает. Семья использует. USB больше не убивает сервис.

Промпты агентов, ADR, Docker Compose, скрипты, памятки пользователей — всё открыто: **[github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)**
