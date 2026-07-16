# ARTICLE_FACTS_TABLE — Проверка фактов в статье для Хабра
> Generated: 2026-06-29; live verification updated: 2026-07-16
> Article: `docs/articles/publication/habr_final.md`
> Evidence source: read-only checks on VPS and Jetson through the implemented reverse SSH tunnel, article screenshots, project operational documents

---

## Таблица фактов

| # | Утверждение в статье | Значение в тексте | Источник доказательства | Статус | Примечание |
|---|---|---|---|---|---|
| 1 | Фотографий и видео на момент исторического снимка | 6 697 | Исторический скриншот Android | ✅ SNAPSHOT | Это не дата публикации и не текущее значение. / This is neither a publication date nor a current value. |
| 2 | Активные изображения Immich | 6 622 | Live SQL count из таблицы `asset`, `deletedAt IS NULL`, status `active` | ✅ LIVE | Проверено 2026-07-16. |
| 3 | Активные видео Immich | 357 | Live SQL count из таблицы `asset`, `deletedAt IS NULL`, status `active` | ✅ LIVE | Проверено 2026-07-16. |
| 4 | Immich итого | 6 979 | 6 622 изображения + 357 видео | ✅ LIVE | Текущий счётчик отделён в статье от исторических скриншотов 6 697 / 6 719. |
| 5 | Контактов в DAVx⁵ | 2 151 | Статья, Шаг 5 | ✅ OK | Принято как есть; верификация через CardDAV невозможна без SSH. |
| 6 | Docker-контейнеров | 13 | Live `docker ps` | ✅ LIVE | Все 13 запущены; 12 имеют health status `healthy`, у Portainer healthcheck не задан. |
| 7 | goss 40/40 | 40/40 | CLAUDE.md v1.4.0 state, checkpoint 2026-06-28b | ✅ OK | Последнее подтверждение 2026-06-28; нужна повторная проверка перед публикацией. |
| 8 | Скорость записи SSD | 250 MB/s | Checkpoint 2026-06-28, CLAUDE.md | ✅ OK | Измерено после включения UAS quirk (usb-storage BOT). |
| 9 | Скорость чтения SSD | 172 MB/s | Checkpoint 2026-06-28, CLAUDE.md | ✅ OK | Измерено после включения UAS quirk. |
| 10 | SSD объём | 229 GB | Live `findmnt` / `df` | ✅ LIVE | `/dev/sda1` → `/mnt/storage`, ext4, 228.2 GiB total, около 208.5 GiB свободно. |
| 11 | RAM Jetson | 4 GB | Спецификация Jetson Nano Dev Kit | ✅ OK | LPDDR4 4 GB — факт Hardware. |
| 12 | RAM использование | ~2.3 GB | Пример Telegram-отчёта в статье | ⚠️ SNAPSHOT | Число из примера отчёта, не текущее измерение. Реальное может отличаться. |
| 13 | Пользователей Nextcloud / участников семейного контура | 5 | Live `occ user:list --output=json`, подсчитано без вывода имён | ✅ LIVE | Проверено 2026-07-16. |
| 14 | Чип энклоужера | JMS583 | Live `lsusb` | ✅ LIVE | USB ID `152d:a583`. |
| 15 | USB скорость | 5 Gbps | CLAUDE.md, checkpoint 2026-06-28b | ✅ OK | USB 3.0 SuperSpeed подтверждено. |
| 16 | Docker версия | 20.10.7 | Live `docker version --format` | ✅ LIVE | Корректно; это JetPack ограничение. |
| 17 | Self-signed cert срок | 10 лет (3650 дней) | Статья Шаг 4, openssl команда | ✅ OK | -days 3650 в команде. |
| 18 | Off-site backup | не настроен | Статья «Что ещё не сделано» | ✅ OK | Честно указано. restic скрипты готовы. |
| 19 | ML в Immich | отключён | Live container configuration: `IMMICH_DISABLE_MACHINE_LEARNING=true` | ✅ LIVE | Подтверждено без вывода секретов. |
| 20 | Число эндпоинтов NAS_Jetson_Nano API | 20 | Live `/openapi.json` | ✅ LIVE | 20 paths и 20 HTTP operations. |
| 21 | Swap | четыре zram-устройства, около 2 GB суммарно | Live `/proc/meminfo` и `swapon --show --bytes` | ✅ LIVE | Старое утверждение «нет swap» исправлено на «изначально не было дискового swap; позднее добавлен zram». |
| 22 | VPS | Ubuntu 24.04.4 LTS, около 2 GB RAM | Live `/etc/os-release`, `/proc/meminfo` | ✅ LIVE | Reverse-порты Jetson слушают только на loopback VPS. |
| 23 | Версии приложений | Nextcloud 33.0.4; Immich 2.7.5 | Live `occ status` и `/api/server/version` | ✅ LIVE | Сервисы отвечают локально и через публичные VPS endpoints. |

---

## Устранённые несоответствия

### 1. Число фото/видео

Скриншоты 6 697 / 6 719 явно помечены как исторические. Текущие значения из базы Immich вынесены отдельно: 6 622 изображения + 357 видео = 6 979 активных объектов.

### 2. RAM 2.3 GB — это snapshot из примера Telegram-отчёта
Реальное потребление может отличаться. Не выдавать за точное актуальное значение.

### 3. Swap

Фраза «нет swap» относилась к начальному состоянию. На 2026-07-16 активны четыре zram-устройства общим объёмом около 2 GB; активные версии статьи исправлены.

---

## Операционное замечание вне фактов статьи

Во время read-only аудита `smartd.service` обнаружен в состоянии `failed`. Статья не утверждает, что все systemd units исправны, поэтому это не меняет её факты. Исправление сервиса требует отдельного безопасного шага и в этот аудит не входило.
