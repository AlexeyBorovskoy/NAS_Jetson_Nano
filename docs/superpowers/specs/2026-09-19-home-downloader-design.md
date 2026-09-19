# Домашняя качалка на Jetson — дизайн / Home downloader on the Jetson — design (2026-09-19)

> 🇷🇺 Запрос сына, приоритет владельца. Утверждено владельцем 2026-09-19. EN summary — в конце.
> Статус: **спецификация**; реализация — после плана; выкат — только по «деплой».

## 1. Зачем и что считается готовым

Сын хочет ставить закачку больших файлов и торрентов, когда его нет дома, а потом дома забирать
результат по Wi-Fi или кабелем на свой компьютер.

**Готово, когда:** с телефона в домашней сети вставлена magnet-ссылка или HTTP-ссылка → файл качается на
SSD → по завершении сам оказывается в `\\192.168.0.50\hdd2tb\Downloads\` → его можно скопировать на ПК.

## 2. Решения

| Вопрос | Решение | Почему |
|---|---|---|
| Где качать | **Jetson, домашний интернет** | VPS держит VPN ~25 человек: жалоба правообладателя хостеру (AEZA) грозит блокировкой IP (правило №13); места на VPS мало |
| Чем | **aria2** — один демон на торренты (magnet, `.torrent`) и HTTP/HTTPS | ≈30–60 МБ ОЗУ, есть в Alpine для arm64, JSON-RPC для бота |
| Интерфейс, этап 1 | **AriaNg** — статическая веб-страница к aria2, в LAN | работает сразу, от бота не зависит |
| Интерфейс, этап 2 | команды в Telegram-боте: «скачай <ссылка>», «закачки», «отмени N» | семья не пользуется Talk; зависит от Telegram-бота (отдельная спецификация) |
| Кому | **вся семья** (решение владельца) | общая папка `Downloads`, без разбиения по людям |
| Steam | **не делаем** на Jetson | SteamCMD только x86, у Jetson ARM; игры Steam привязаны к аккаунту. У сына есть удалённая установка из мобильного Steam на свой ПК |
| Флешка в Jetson | **не на этапе 1** | два необъяснённых аппаратных сброса Jetson; SSD и HDD уже на USB — лишний потребитель на шине. Флешку — в свой ПК, копировать из шары |

## 3. Схема

```
телефон/ПК в LAN ──http──► :6880 AriaNg (статика) ──JSON-RPC + секрет──► :6800 aria2
                                                                              │
                          /mnt/storage/downloads/.incomplete  (SSD, идёт закачка)
                                                                              │ on-download-complete
                          /mnt/hdd2tb/Downloads/<имя>          (HDD, готово) ◄┘
                                     │
          Samba \\192.168.0.50\hdd2tb\Downloads  ·  Nextcloud /HDD-2TB/Downloads (снаружи — через VPN)
```

## 4. Компоненты

| Компонент | Где | Ответственность |
|---|---|---|
| образ `homecloud_downloads` | `services/downloads/`, собирается на Jetson | Alpine + `aria2` + AriaNg (версия и SHA-256 архива закреплены) + `busybox httpd` для страницы |
| `aria2.conf` | в образе | каталог `.incomplete` на SSD, `seed-time=0`, не больше 2 закачек одновременно, `file-allocation=falloc`, сессия сохраняется (закачки переживают перезапуск) |
| `on_start.sh` | в образе | **SSD-страж**: если на `/mnt/storage` свободно меньше `DL_SSD_MIN_FREE_GB` (40), закачка ставится на паузу через RPC, причина — в журнал |
| `on_complete.sh` | в образе | переносит готовое (файл или **верхний каталог** многофайлового торрента) на HDD; при ошибке оставляет на SSD и пишет в журнал |
| `speed_schedule` | systemd-таймеры на хосте | 08:00 — лимит `DL_DAY_LIMIT` (6M ≈ 48 Мбит/с), 23:00 — без лимита; через `aria2.changeGlobalOption` |
| compose `docker-compose.downloads.yml` | `docker/compose/` | `mem_limit: 192m`, порты 6800/6880 в LAN, тома SSD и HDD, `ARIA2_RPC_SECRET` из `config/.env` |

Samba, Nextcloud и VPS **не меняются**: `Downloads` — обычный каталог внутри уже расшаренного `/mnt/hdd2tb`.

## 5. Ошибки и безопасность

- RPC и AriaNg только в LAN (как остальные сервисы); доступ по секрету `ARIA2_RPC_SECRET` (в `config/.env`,
  в git — пустой ключ). Внутри LAN сегментации нет — это известное свойство сети, не новое.
- Снаружи управления нет (этап 2 — через Telegram-бота). Порты на VPS не открываются.
- Раздача торрентов выключена (`seed-time=0`), исходящий канал не забивается; что качать — ответственность
  семьи (торрент с домашнего IP виден в рое).
- Перенос на HDD (NTFS через ntfs-3g) нагружает CPU — поэтому закачки не больше двух одновременно.
- HDD заполнен или не смонтирован → файл остаётся на SSD, SSD-страж не даст забить SSD (Immich/Nextcloud).
- Контейнер не от root (UID 1000 = владелец шары), без `docker.sock`.

## 6. Тесты (TDD, в воротах)

- `on_complete.sh`: однофайловая закачка; многофайловый торрент → переносится верхний каталог целиком;
  имя с пробелами и кириллицей; HDD недоступен → файл остаётся, код ≠ 0; файл уже есть на HDD → суффикс, без перезаписи.
- `on_start.sh`: свободно меньше порога → вызывается pause по RPC (RPC подменён); больше — ничего.
- `speed_schedule`: отправляет правильный JSON-RPC с секретом; секрет не попадает в вывод.
- compose: `mem_limit`, порты, тома — статическая проверка (как `test_container_hardening.py`).

## 7. Выкат (по «деплой»)

1. `ARIA2_RPC_SECRET` в `config/.env` (значение — в Windows Credential Manager `nas-aria2-rpc-secret`).
2. Каталоги `/mnt/storage/downloads/.incomplete`, `/mnt/hdd2tb/Downloads`.
3. Сборка и запуск контейнера; таймеры скорости.
4. Проверка: маленький легальный торрент (образ дистрибутива Linux) и HTTP-файл → оба в `Downloads` на HDD;
   видно с Windows по `\\192.168.0.50\hdd2tb\Downloads`.
5. 13 прежних контейнеров здоровы, свободная память не ниже 1 ГБ. VPS не трогается.

---

### EN summary
A home downloader for the family, requested by the owner's son. aria2 runs on the Jetson in one small
container and handles both torrents and plain HTTP links, with the AriaNg web page for control from the home
network. Downloads land on the SSD and are moved to `/mnt/hdd2tb/Downloads` when finished, so they appear in
the existing Samba share and in Nextcloud. An SSD guard pauses downloads when less than 40 GB is free, seeding
is off, at most two downloads run at once, and the speed is capped during the day. The VPS is not used, because
it carries the family VPN and a copyright complaint could get its IP blocked. Steam is out of scope (SteamCMD is
x86-only), and a USB stick in the Jetson is deferred because of the USB power risk. Telegram bot commands come
in a second stage.
