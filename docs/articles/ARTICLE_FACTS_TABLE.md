# ARTICLE_FACTS_TABLE — Проверка фактов в статье для Хабра / Fact-check of the Habr article
> Generated: 2026-06-29; live verification updated: 2026-07-16
> Article: `docs/articles/publication/habr_final.md`
> Evidence source: read-only checks on VPS and Jetson through the implemented reverse SSH tunnel, article screenshots, project operational documents

---

## Таблица фактов / Facts table

| # | Утверждение в статье / Claim in the article | Значение в тексте / Value in the text | Источник доказательства / Evidence source | Статус / Status | Примечание / Note |
|---|---|---|---|---|---|
| 1 | Фотографий и видео на момент исторического снимка / Photos and videos at the time of the historical snapshot | 6 697 | Исторический скриншот Android / Historical Android screenshot | ✅ SNAPSHOT | Это не дата публикации и не текущее значение. / This is neither a publication date nor a current value. |
| 2 | Активные изображения Immich / Active Immich images | 6 622 | Live SQL count из таблицы `asset`, `deletedAt IS NULL`, status `active` / Live SQL count over the `asset` table, `deletedAt IS NULL`, status `active` | ✅ LIVE | Проверено 2026-07-16. / Verified 2026-07-16. |
| 3 | Активные видео Immich / Active Immich videos | 357 | Live SQL count из таблицы `asset`, `deletedAt IS NULL`, status `active` / Live SQL count over the `asset` table, `deletedAt IS NULL`, status `active` | ✅ LIVE | Проверено 2026-07-16. / Verified 2026-07-16. |
| 4 | Immich итого / Immich total | 6 979 | 6 622 изображения + 357 видео / 6 622 images + 357 videos | ✅ LIVE | Текущий счётчик отделён в статье от исторических скриншотов 6 697 / 6 719. / The current counter is kept separate in the article from the historical screenshots 6 697 / 6 719. |
| 5 | Контактов в DAVx⁵ / Contacts in DAVx⁵ | 2 151 | Статья, Шаг 5 / The article, Step 5 | ✅ OK | Принято как есть; верификация через CardDAV невозможна без SSH. / Accepted as is; CardDAV verification is impossible without SSH. |
| 6 | Docker-контейнеров / Docker containers | 13 | Live `docker ps` | ✅ LIVE | Все 13 запущены; 12 имеют health status `healthy`, у Portainer healthcheck не задан. / All 13 are running; 12 report health status `healthy`, Portainer has no healthcheck defined. |
| 7 | goss 40/40 | 40/40 | CLAUDE.md v1.4.0 state, checkpoint 2026-06-28b | ✅ OK | Последнее подтверждение 2026-06-28; нужна повторная проверка перед публикацией. / Last confirmed 2026-06-28; a re-check is needed before publication. |
| 8 | Скорость записи SSD / SSD write speed | 250 MB/s | Checkpoint 2026-06-28, CLAUDE.md | ✅ OK | Измерено после включения UAS quirk (usb-storage BOT). / Measured after the UAS quirk was enabled (usb-storage BOT). |
| 9 | Скорость чтения SSD / SSD read speed | 172 MB/s | Checkpoint 2026-06-28, CLAUDE.md | ✅ OK | Измерено после включения UAS quirk. / Measured after the UAS quirk was enabled. |
| 10 | SSD объём / SSD capacity | 229 GB | Live `findmnt` / `df` | ✅ LIVE | `/dev/sda1` → `/mnt/storage`, ext4, 228.2 GiB total, около 208.5 GiB свободно. / `/dev/sda1` → `/mnt/storage`, ext4, 228.2 GiB total, about 208.5 GiB free. |
| 11 | RAM Jetson | 4 GB | Спецификация Jetson Nano Dev Kit / Jetson Nano Dev Kit specification | ✅ OK | LPDDR4 4 GB — факт Hardware. / LPDDR4 4 GB — a hardware fact. |
| 12 | RAM использование / RAM usage | ~2.3 GB | Пример Telegram-отчёта в статье / The sample Telegram report in the article | ⚠️ SNAPSHOT | Число из примера отчёта, не текущее измерение. Реальное может отличаться. / A number from a sample report, not a current measurement. The real value may differ. |
| 13 | Пользователей Nextcloud / участников семейного контура — Nextcloud users / members of the family circle | 5 | Live `occ user:list --output=json`, подсчитано без вывода имён / Live `occ user:list --output=json`, counted without printing names | ✅ LIVE | Проверено 2026-07-16. / Verified 2026-07-16. |
| 14 | Чип энклоужера / Enclosure chip | JMS583 | Live `lsusb` | ✅ LIVE | USB ID `152d:a583`. |
| 15 | USB скорость / USB speed | 5 Gbps | CLAUDE.md, checkpoint 2026-06-28b | ✅ OK | USB 3.0 SuperSpeed подтверждено. / USB 3.0 SuperSpeed confirmed. |
| 16 | Docker версия / Docker version | 20.10.7 | Live `docker version --format` | ✅ LIVE | Корректно; это JetPack ограничение. / Correct; this is a JetPack constraint. |
| 17 | Self-signed cert срок / Self-signed cert validity | 10 лет (3650 дней) / 10 years (3650 days) | Статья Шаг 4, openssl команда / The article, Step 4, the openssl command | ✅ OK | -days 3650 в команде. / -days 3650 in the command. |
| 18 | Off-site backup | не настроен / not configured | Статья «Что ещё не сделано» / The article's "What is still undone" | ✅ OK | Честно указано. restic скрипты готовы. / Stated honestly. The restic scripts are ready. |
| 19 | ML в Immich / ML in Immich | отключён / disabled | Live container configuration: `IMMICH_DISABLE_MACHINE_LEARNING=true` | ✅ LIVE | Подтверждено без вывода секретов. / Confirmed without printing any secrets. |
| 20 | Число эндпоинтов NAS_Jetson_Nano API / Number of NAS_Jetson_Nano API endpoints | 20 | Live `/openapi.json` | ✅ LIVE | 20 paths и 20 HTTP operations. / 20 paths and 20 HTTP operations. |
| 21 | Swap | четыре zram-устройства, около 2 GB суммарно / four zram devices, about 2 GB in total | Live `/proc/meminfo` и `swapon --show --bytes` / Live `/proc/meminfo` and `swapon --show --bytes` | ✅ LIVE | Старое утверждение «нет swap» исправлено на «изначально не было дискового swap; позднее добавлен zram». / The old claim "no swap" was corrected to "there was no disk swap initially; zram was added later". |
| 22 | VPS | Ubuntu 24.04.4 LTS, около 2 GB RAM / Ubuntu 24.04.4 LTS, about 2 GB RAM | Live `/etc/os-release`, `/proc/meminfo` | ✅ LIVE | Reverse-порты Jetson слушают только на loopback VPS. / The Jetson's reverse ports listen only on the VPS loopback. |
| 23 | Версии приложений / Application versions | Nextcloud 33.0.4; Immich 2.7.5 | Live `occ status` и `/api/server/version` / Live `occ status` and `/api/server/version` | ✅ LIVE | Сервисы отвечают локально и через публичные VPS endpoints. / The services respond both locally and through the public VPS endpoints. |

---

## Устранённые несоответствия / Resolved inconsistencies

### 1. Число фото/видео / Photo and video counts

🇷🇺 Скриншоты 6 697 / 6 719 явно помечены как исторические. Текущие значения из базы Immich вынесены отдельно: 6 622 изображения + 357 видео = 6 979 активных объектов.

🇬🇧 The screenshots showing 6 697 / 6 719 are explicitly labelled as historical. The current values from the Immich database are listed separately: 6 622 images + 357 videos = 6 979 active assets.

### 2. RAM 2.3 GB — это snapshot из примера Telegram-отчёта / RAM 2.3 GB is a snapshot from the sample Telegram report

🇷🇺 Реальное потребление может отличаться. Не выдавать за точное актуальное значение.

🇬🇧 Actual consumption may differ. Do not present it as an exact current value.

### 3. Swap

🇷🇺 Фраза «нет swap» относилась к начальному состоянию. На 2026-07-16 активны четыре zram-устройства общим объёмом около 2 GB; активные версии статьи исправлены.

🇬🇧 The phrase "no swap" referred to the initial state. As of 2026-07-16 four zram devices are active with a combined size of about 2 GB; the live versions of the article have been corrected.

---

## Операционное замечание вне фактов статьи / Operational note outside the article's facts

🇷🇺 Во время read-only аудита `smartd.service` обнаружен в состоянии `failed`. Статья не утверждает, что все systemd units исправны, поэтому это не меняет её факты. Исправление сервиса требует отдельного безопасного шага и в этот аудит не входило.

🇬🇧 During the read-only audit, `smartd.service` was found in the `failed` state. The article does not claim that all systemd units are healthy, so this does not change any of its facts. Fixing the service requires a separate, safe step and was not part of this audit.
