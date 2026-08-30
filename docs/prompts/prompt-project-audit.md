# Промт: полный аудит проекта Home Cloud и сбор фактуры
# Prompt: full audit of the Home Cloud project and fact-gathering

> Вставить в Claude Code (VS Code), находясь в корне репозитория проекта.
> Paste into Claude Code (VS Code) while in the project repository root.

---

Ты работаешь как инженер-разработчик, DevOps-инженер и технический писатель проекта домашнего облака на Jetson Nano.
You are working as a software engineer, DevOps engineer, and technical writer for the Jetson Nano home-cloud project.

**Цель этой сессии:** собрать единую, проверенную фактуру по проекту — из кода, из конфигураций и из живой системы — чтобы на её основе можно было подготовить англоязычные публикации и привести репозиторий в состояние, пригодное для внешней аудитории. Ты ничего не переписываешь и не публикуешь на этом этапе. Ты собираешь и проверяешь.
**Goal of this session:** gather a single, verified fact base about the project — from the code, from configurations, and from the live system — so it can later be used to prepare English-language publications and bring the repository into a state fit for an external audience. You are not rewriting or publishing anything at this stage. You are gathering and verifying.

## Обязательные правила / Mandatory rules

1. **Read-only по умолчанию.** Любая команда, которая изменяет состояние системы, требует отдельного явного подтверждения от меня. Инспекция — без подтверждения.
1. **Read-only by default.** Any command that changes system state requires separate explicit confirmation from me. Inspection requires no confirmation.
2. Не запускай, не останавливай и не пересоздавай контейнеры, не трогай volumes, не меняй конфигурации сервисов, не делай `docker compose up/down`, не перезапускай systemd-юниты.
2. Do not start, stop, or recreate containers; do not touch volumes; do not change service configurations; do not run `docker compose up/down`; do not restart systemd units.
3. **Никаких секретов в артефактах.** Пароли, токены, ключи, реальные IP, домены, e-mail, имена членов семьи, ID Telegram-чатов, серийные номера — заменяй плейсхолдерами вида `<VPS_IP>`, `<TG_BOT_TOKEN>`. Если секрет попал в вывод команды — маскируй его до записи в файл.
3. **No secrets in artifacts.** Passwords, tokens, keys, real IPs, domains, e-mails, family member names, Telegram chat IDs, serial numbers — replace with placeholders such as `<VPS_IP>`, `<TG_BOT_TOKEN>`. If a secret appears in command output, mask it before writing it to a file.
4. Если факт можно проверить командой — проверь, а не предполагай. Каждое число в отчёте должно сопровождаться командой, которой оно получено, и датой замера.
4. If a fact can be checked with a command — check it, don't assume. Every number in the report must be accompanied by the command that produced it and the measurement date.
5. Если проверить факт невозможно (нет доступа, нужен ваттметр, нужно время) — не выдумывай, пиши `TODO: не измерено` и указывай, как именно это измерить.
5. If a fact cannot be verified (no access, a wattmeter is needed, time is needed) — do not invent it; write `TODO: not measured` and state exactly how to measure it.
6. Работай этапами. После каждого этапа — краткий отчёт и пауза, я подтверждаю переход к следующему.
6. Work in stages. After each stage — a brief report and a pause; I confirm moving on to the next one.

## Контекст проекта / Project context

- Jetson Nano Dev Kit, 4 ГБ, ARM64, GPU Maxwell. JetPack 4.6.x, L4T 32.x, Ubuntu 18.04 — платформа EOL, обновление невозможно.
- Jetson Nano Dev Kit, 4 GB, ARM64, Maxwell GPU. JetPack 4.6.x, L4T 32.x, Ubuntu 18.04 — an EOL platform, no upgrade path.
- Системный диск microSD 64 ГБ, хранилище — внешний USB SSD (JMS583) на `/mnt/storage`, ext4.
- System disk: 64 GB microSD; storage: an external USB SSD (JMS583) at `/mnt/storage`, ext4.
- Jetson за CGNAT. Внешний доступ — reverse SSH tunnel (autossh) до VPS Ubuntu 24.04 / 2 ГБ, на VPS nginx в Docker.
- The Jetson is behind CGNAT. External access is via a reverse SSH tunnel (autossh) to a VPS (Ubuntu 24.04 / 2 GB), with nginx in Docker on the VPS.
- Сервисы на Jetson: Nextcloud, Immich, PostgreSQL, собственный REST API на FastAPI, Samba, Netdata, Uptime Kuma, Portainer. Мониторинг: Beszel Hub на VPS, Telegram-бот для отчётов.
- Services on the Jetson: Nextcloud, Immich, PostgreSQL, a custom FastAPI REST API, Samba, Netdata, Uptime Kuma, Portainer. Monitoring: Beszel Hub on the VPS, a Telegram bot for reports.
- Клиенты: Android (Xiaomi, MIUI/HyperOS), DAVx⁵ для CalDAV/CardDAV.
- Clients: Android (Xiaomi, MIUI/HyperOS), DAVx⁵ for CalDAV/CardDAV.

Уточни у меня всё, что расходится с реальностью, прежде чем фиксировать это в отчёте.
Ask me about anything that diverges from reality before recording it in the report.

---

## Этап 1. Инвентаризация репозитория / Stage 1. Repository inventory

Пройди по репозиторию и собери:
Walk through the repository and gather:

- дерево проекта, назначение каждой значимой директории и файла;
- the project tree, and the purpose of each significant directory and file;
- все `docker-compose*.yml`: сервисы, образы с точными тегами, порты, volumes, `mem_limit`, healthcheck, restart policy, сети;
- every `docker-compose*.yml`: services, images with exact tags, ports, volumes, `mem_limit`, healthcheck, restart policy, networks;
- все `.env`, `.env.example`, конфиги nginx, systemd-юниты, скрипты бэкапа, cron/timer'ы;
- every `.env`, `.env.example`, nginx configs, systemd units, backup scripts, cron/timers;
- полный список эндпоинтов FastAPI: метод, путь, назначение, модель ответа, требуется ли авторизация. Сверь фактическое количество с заявленными 20;
- the full list of FastAPI endpoints: method, path, purpose, response model, whether auth is required. Cross-check the actual count against the claimed 20;
- зависимости и их версии (`requirements.txt`, `pyproject.toml`, `package.json`);
- dependencies and their versions (`requirements.txt`, `pyproject.toml`, `package.json`);
- состояние документации: что есть, что устарело, что противоречит коду.
- documentation state: what exists, what's outdated, what contradicts the code.

Отдельно проверь и вынеси в отчёт:
Separately check and record in the report:

- есть ли файл лицензии;
- whether a license file exists;
- есть ли секреты в рабочем дереве **и в истории git** (проверь `git log -p` по чувствительным паттернам, либо предложи мне запустить gitleaks/trufflehog);
- whether there are secrets in the working tree **and in git history** (check `git log -p` for sensitive patterns, or suggest that I run gitleaks/trufflehog);
- сколько файлов содержит русскоязычные комментарии, строки, имена переменных или документацию — с перечнем;
- how many files contain Russian-language comments, strings, variable names, or documentation — with a list;
- захардкоженные IP, пути, имена хостов.
- hardcoded IPs, paths, hostnames.

## Этап 2. Инвентаризация живой системы / Stage 2. Live system inventory

Сначала определи, есть ли у тебя доступ к Jetson и VPS из этой сессии (проверь `~/.ssh/config`, спроси меня).
First determine whether you have access to the Jetson and VPS from this session (check `~/.ssh/config`, ask me).

**Если доступа нет** — не пытайся его получить. Вместо этого сгенерируй скрипт `scripts/collect_facts.sh`: строго read-only, без sudo там, где можно обойтись, с маскированием секретов на выходе, пишущий результат в один текстовый файл. Я запущу его сам и верну тебе вывод.
**If there is no access** — do not try to obtain it. Instead, generate a `scripts/collect_facts.sh` script: strictly read-only, avoiding sudo where possible, masking secrets in its output, writing the result to a single text file. I will run it myself and return the output to you.

Что нужно собрать (на Jetson, если не указано иное):
What needs to be collected (on the Jetson, unless stated otherwise):

**Платформа / Platform**
- `cat /etc/nv_tegra_release`, `head -n1 /etc/nv_boot_control.conf`, `uname -a`, `lsb_release -a`
- `docker version`, `docker compose version`, `docker info | grep -i -E 'storage|cgroup'`
- `free -h`, `swapon --show`, `zramctl` — фактически проверь, есть ли zram по умолчанию и настроен ли swap
- `free -h`, `swapon --show`, `zramctl` — actually verify whether zram is present by default and whether swap is configured
- `nvcc --version` или `cat /usr/local/cuda/version.txt`, доступность CUDA
- `nvcc --version` or `cat /usr/local/cuda/version.txt`, CUDA availability

**Хранилище / Storage**
- `lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL`, `df -h`, `findmnt /mnt/storage`
- работает ли SSD через UAS или через usb-storage: `lsusb -t`, `dmesg | grep -i -E 'uas|usb-storage'`
- whether the SSD runs via UAS or via usb-storage: `lsusb -t`, `dmesg | grep -i -E 'uas|usb-storage'`
- SMART: `smartctl -a` (может быть недоступен через JMS583 без `-d sat`)
- SMART: `smartctl -a` (may be unavailable through the JMS583 without `-d sat`)
- фактическая занятость: размеры каталогов Nextcloud, Immich, PostgreSQL, бэкапов
- actual usage: directory sizes for Nextcloud, Immich, PostgreSQL, backups

**Сервисы / Services**
- `docker ps -a --format` с образами, статусами, uptime, health
- `docker ps -a --format` with images, statuses, uptime, health
- `docker stats --no-stream` — реальное потребление RAM/CPU по контейнерам
- `docker stats --no-stream` — actual RAM/CPU consumption per container
- версии Nextcloud и Immich (через `occ status` в контейнере и `/api/server/version`)
- Nextcloud and Immich versions (via `occ status` inside the container and `/api/server/version`)
- Nextcloud: количество пользователей, файлов, объём. Immich: количество фото, видео, объём, включено ли ML и на CPU оно или на GPU
- Nextcloud: number of users, files, volume. Immich: number of photos, videos, volume, whether ML is enabled and whether it runs on CPU or GPU
- контакты/календари DAVx⁵: количество записей
- DAVx⁵ contacts/calendars: number of records
- `systemctl status autossh*`, конфигурация юнита, число рестартов за последние 30 дней из `journalctl`
- `systemctl status autossh*`, the unit configuration, restart count over the last 30 days from `journalctl`

**Сеть / Network**
- прослушиваемые порты: `ss -tulpn` (на Jetson и на VPS)
- listening ports: `ss -tulpn` (on the Jetson and on the VPS)
- схема проброса: какие порты VPS на какие порты Jetson, из конфигурации nginx и autossh
- the forwarding map: which VPS ports map to which Jetson ports, from the nginx and autossh configuration
- сроки действия и параметры self-signed сертификатов
- validity periods and parameters of the self-signed certificates
- проверь, не торчит ли что-нибудь наружу помимо туннеля
- check whether anything is exposed externally besides the tunnel

## Этап 3. Измеримые показатели / Stage 3. Measurable metrics

Это то, чего в проекте сейчас нет и что нужно для внешней публикации. Составь план замеров и сгенерируй `scripts/benchmark.sh`. Каждый замер — с методикой, длительностью и условиями.
This is what the project currently lacks and what's needed for external publication. Draft a measurement plan and generate `scripts/benchmark.sh`. Each measurement should include a methodology, duration, and conditions.

- **Энергопотребление.** На Jetson Nano Dev Kit есть INA3221, `tegrastats` отдаёт `POM_5V_IN` в мВт. Сними среднее за 10 минут в простое и под нагрузкой. Отдельно зафиксируй, что потребление SSD в эту цифру не входит, и оцени полное потребление сборки.
- **Power consumption.** The Jetson Nano Dev Kit has an INA3221; `tegrastats` reports `POM_5V_IN` in mW. Measure the average over 10 minutes at idle and under load. Separately note that SSD consumption is not included in this figure, and estimate the build's total consumption.
- **Температуры.** `tegrastats` и `/sys/devices/virtual/thermal/thermal_zone*/temp` — простой, загрузка фото в Immich, ночной бэкап. Есть ли троттлинг.
- **Temperatures.** `tegrastats` and `/sys/devices/virtual/thermal/thermal_zone*/temp` — idle, photo upload to Immich, nightly backup. Whether throttling occurs.
- **Режим питания.** `nvpmodel -q`, `jetson_clocks --show` — на 5 Вт или 10 Вт работает плата.
- **Power mode.** `nvpmodel -q`, `jetson_clocks --show` — whether the board runs at 5 W or 10 W.
- **Диск.** Последовательные и случайные чтение/запись на `/mnt/storage` через `fio`, реальная пропускная способность USB 3.0 с JMS583. Замер не должен упасть на сервисы — согласуй со мной время.
- **Disk.** Sequential and random read/write on `/mnt/storage` via `fio`, actual USB 3.0 throughput with the JMS583. The measurement must not impact services — coordinate timing with me.
- **Сеть через туннель.** Задержка и пропускная способность от внешнего клиента до Nextcloud через VPS: время отклика `curl -w`, скорость выгрузки и загрузки файла 100 МБ. Сравни с той же операцией по LAN — разница покажет цену туннеля.
- **Network via the tunnel.** Latency and throughput from an external client to Nextcloud via the VPS: `curl -w` response time, upload/download speed for a 100 MB file. Compare against the same operation over LAN — the difference reveals the tunnel's cost.
- **Immich.** Скорость импорта (объектов в минуту), время генерации превью и эмбеддингов на объект, используется ли CUDA. Если ML идёт на CPU — зафиксируй это как факт и оцени, реализуемо ли GPU-ускорение на CUDA 10.2 и Maxwell.
- **Immich.** Import speed (objects per minute), thumbnail and embedding generation time per object, whether CUDA is used. If ML runs on CPU — record this as fact and assess whether GPU acceleration is feasible on CUDA 10.2 and Maxwell.
- **Nextcloud.** Время отклика `status.php` и дашборда, поведение при параллельной работе двух-трёх клиентов.
- **Nextcloud.** Response time for `status.php` and the dashboard, behavior under two-to-three concurrent clients.
- **Стабильность.** Аптайм системы и контейнеров, число перезапусков, обрывы туннеля, инциденты из логов за всё время наблюдения.
- **Stability.** System and container uptime, restart counts, tunnel disconnects, incidents from the logs over the whole observation period.
- **Бэкапы.** Длительность, размер, дата последнего успешного, проверялось ли восстановление.
- **Backups.** Duration, size, date of the last success, whether restore was tested.

Для каждой позиции, которую нельзя снять прямо сейчас, укажи, что именно требуется (ваттметр, второй хост для iperf3, окно простоя).
For every item that cannot be measured right now, state exactly what's required (a wattmeter, a second host for iperf3, a maintenance window).

## Этап 4. Разрыв между статьёй и реальностью / Stage 4. Gap between the article and reality

В репозитории/документации есть опубликованная статья с числами (6 697 объектов при первичной загрузке, 6 979 активных объектов на 16 июля 2026, 2 151 запись контактов, 229 ГБ, 20 операций API, RAM 2,3 ГБ, CPU ~15 %). Сверь каждое утверждение с текущим состоянием системы и выпиши таблицу: заявлено → фактически → расхождение → причина.
There's a published article in the repository/documentation with figures (6,697 objects on initial upload, 6,979 active objects as of July 16, 2026, 2,151 contact records, 229 GB, 20 API operations, RAM 2.3 GB, CPU ~15%). Cross-check every claim against the current system state and produce a table: claimed → actual → delta → cause.

## Этап 5. Что мешает внешней публикации / Stage 5. What blocks external publication

Составь список блокеров и рисков по категориям, каждый с оценкой критичности и объёмом работ:
Compile a list of blockers and risks by category, each with a criticality assessment and effort estimate:

- юридическое и именование: лицензия, имя проекта (текущее имя конфликтует с чужим товарным знаком — предложи 5 вариантов замены, свободных в GitHub и в npm/PyPI);
- legal and naming: license, project name (the current name conflicts with someone else's trademark — propose 5 replacement options, free on GitHub and on npm/PyPI);
- безопасность: секреты в истории, self-signed вместо ACME DNS-01, доступность API снаружи, права на volumes, версии образов с известными CVE;
- security: secrets in history, self-signed certs instead of ACME DNS-01, external API availability, volume permissions, image versions with known CVEs;
- воспроизводимость: сможет ли посторонний человек развернуть это по README с нуля — пройди по инструкции построчно и отметь каждый шаг, который не выполним без знаний, которых в тексте нет;
- reproducibility: could an outsider deploy this from the README from scratch — walk through the instructions line by line and flag every step that's not achievable without knowledge missing from the text;
- локализация: русскоязычные строки в коде и документации;
- localization: Russian-language strings in code and documentation;
- гигиена репозитория: `.gitignore`, `.env.example`, размер репозитория, бинарники в истории.
- repository hygiene: `.gitignore`, `.env.example`, repository size, binaries in history.

## Артефакты на выходе / Output artifacts

Создай в `docs/` (на английском, кроме отдельно оговорённого):
Create in `docs/` (in English, except where noted otherwise):

| Файл / File | Содержание / Content |
|---|---|
| `PROJECT_FACTS.md` | Единый источник правды: каждый факт и число с командой-источником и датой замера / Single source of truth: every fact and number with its source command and measurement date |
| `INVENTORY.md` | Сервисы, образы, версии, порты, volumes, лимиты, схема проброса портов / Services, images, versions, ports, volumes, limits, port-forward map |
| `API.md` | Полный перечень эндпоинтов, сгенерированный из кода / Full endpoint list, generated from the code |
| `MEASUREMENTS.md` | Результаты замеров + методика + список TODO / Measurement results + methodology + TODO list |
| `GAPS.md` | Блокеры публикации, критичность, оценка работ / Publication blockers, criticality, effort estimate |
| `OBJECTIONS.md` | Заготовки честных ответов: почему autossh, а не Tailscale/Cloudflare Tunnel/WireGuard; почему Jetson, а не Raspberry Pi 5 или мини-ПК; почему self-signed; почему EOL-платформа / Honest answer drafts: why autossh instead of Tailscale/Cloudflare Tunnel/WireGuard; why a Jetson instead of a Raspberry Pi 5 or a mini PC; why self-signed; why an EOL platform |
| `architecture.mmd` | Схема в Mermaid: клиенты → VPS → туннель → Jetson → SSD / Mermaid diagram: clients → VPS → tunnel → Jetson → SSD |
| `../scripts/collect_facts.sh` | Read-only сборщик фактов с маскированием секретов / Read-only fact collector with secret masking |
| `../scripts/benchmark.sh` | Скрипт замеров / Measurement script |

## Формат работы / Work format

Начни с Этапа 1 и остановись. В конце каждого этапа дай:
Start with Stage 1 and stop. At the end of each stage, provide:

1. что сделано и какими командами;
1. what was done and with which commands;
2. ключевые находки — списком, без воды;
2. key findings — as a list, no filler;
3. что не удалось проверить и почему;
3. what couldn't be verified and why;
4. риски, если они появились;
4. risks, if any emerged;
5. предложение по следующему безопасному шагу.
5. a proposal for the next safe step.

Не создавай файлы до Этапа 5 — сначала собери и покажи мне данные в чате, я подтвержу или поправлю.
Do not create files before Stage 5 — first gather and show me the data in chat, and I will confirm or correct it.
