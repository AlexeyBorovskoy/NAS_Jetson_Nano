# Домашняя качалка на Jetson — дизайн / Home downloader on the Jetson — design (2026-09-19)

> 🇷🇺 Запрос сына, приоритет владельца. Утверждено владельцем 2026-09-19; **редакция 2** того же дня:
> главный интерфейс — **чат с ботом @bobik_borovskoy_bot** (бот добавлен в семейную группу «Боровские»);
> **редакция 3:** обращение к боту — по имени: «@бобик скачай <ссылка>» (решение владельца);
> **редакция 4:** закачки до 100 ГБ и больше — большие пишутся сразу на HDD (вопрос владельца);
> **редакция 5:** в этот же срез входят **вопросы к GigaChat** по обращению «@бобик <вопрос>» (решение владельца);
> SOCKS слушает `172.17.0.1:1080` — Jetson напрямую до Telegram не доходит (замер 2026-09-19: 3 из 3 таймаут).
> EN summary — в конце. Статус: **спецификация**; реализация — после плана; выкат — только по «деплой».

## 1. Зачем и что считается готовым

Сын хочет ставить закачку больших файлов и торрентов, когда его нет дома, а потом дома забирать
результат по Wi-Fi или кабелем на свой компьютер. Команду он даёт **в Telegram** — там, где семья уже общается.

**Готово, когда:** в семейной группе или в личке написано «@бобик скачай <magnet или HTTP-ссылка>» (или
`.torrent`-файл с подписью «@бобик скачай») → бот отвечает «принял» → файл качается на SSD (большой — сразу на HDD) → по завершении сам оказывается в
`\\192.168.0.50\hdd2tb\Downloads\` → бот пишет в тот же чат «✅ Готово: <имя>».

## 2. Решения

| Вопрос | Решение | Почему |
|---|---|---|
| Где качать | **Jetson, домашний интернет** | VPS держит VPN ~25 человек: жалоба правообладателя хостеру (AEZA) грозит блокировкой IP (правило №13); места на VPS мало |
| Чем | **aria2** — один демон на торренты (magnet, `.torrent`) и HTTP/HTTPS | ≈30–60 МБ ОЗУ, есть в Alpine для arm64, JSON-RPC |
| Интерфейс | **чат с ботом** — главный (решение владельца); AriaNg в LAN — запасной | команды там, где семья; веб-страница — если бот недоступен |
| Обращение | **по имени**: «@бобик …» или «бобик, …» — как позывной `@бобик` в Talk (решение владельца) | одно имя во всех каналах семьи |
| Режим приватности бота в группе | **выключен** (`/setprivacy` → Disable в @BotFather, бота перезайти в группу) | иначе Telegram не отдаёт боту текст «@бобик»: это не упоминание аккаунта, а слово. Цена — в §7 |
| Кому | **вся семья** (решение владельца): белый список Telegram user_id + одна группа | общая папка `Downloads` |
| Транспорт бота | как в спецификации Telegram-бота: long polling через SSH SOCKS к VPS, код в контейнере NAS API | портов наружу нет; рабочий обратный туннель не трогается |
| Порядок с Telegram-ботом | **первый срез Telegram-бота**: транспорт, белый список, команды закачек **и вопросы к GigaChat** («@бобик <вопрос>» — тот же путь, что `@бобик` в Talk: safety gate → шлюз с токеном → квота по логину). Фото — следующим срезом | решение владельца |
| Steam | **не делаем** на Jetson | SteamCMD только x86, у Jetson ARM; игры Steam привязаны к аккаунту. У сына — удалённая установка из мобильного Steam на свой ПК |
| Размер закачки | **без искусственного предела**; ≤ `DL_SSD_MAX_GB` (20 ГБ) и помещается на SSD с запасом → через SSD; больше → **сразу на HDD** (`/mnt/hdd2tb/Downloads/.incomplete`), без переноса | канал ≈ 11 МБ/с, HDD через ntfs-3g пишет ≈ 90 МБ/с — не узкое место; перенос 100 ГБ с SSD — лишние ~20 мин CPU и риск забить SSD |
| 20 МБ в Telegram | это предел **только для `.torrent`-файла**, который бот забирает из чата (лимит Bot API на `getFile`); сам торрент по нему — любого размера. Magnet и HTTP этого предела не имеют | — |
| Флешка в Jetson | **не на этом этапе** | два необъяснённых аппаратных сброса Jetson; SSD и HDD уже на USB |

## 3. Схема

```
Telegram (группа «Боровские» / личка) ⇄ VPS ══ SSH SOCKS 172.17.0.1:1080 ══► Jetson
                                                                             │
   контейнер NAS API: telegram_front ─► downloads (команды, учёт) ─JSON-RPC+секрет─► aria2 :6800
                                     └─► «@бобик <вопрос>» → safety gate → LLM-шлюз (токен) → GigaChat
                                                                                      │
   ≤ 20 ГБ:               /mnt/storage/downloads/.incomplete  (SSD, идёт закачка)     │
   > 20 ГБ:               /mnt/hdd2tb/Downloads/.incomplete    (HDD, идёт закачка)     │
                                                                                      │ on-download-complete
                          /mnt/hdd2tb/Downloads/<имя>          (HDD, готово)      ◄───┘
                                     │
          Samba \\192.168.0.50\hdd2tb\Downloads  ·  Nextcloud /HDD-2TB/Downloads (снаружи — через VPN)

   запасной путь: браузер в LAN ─► :6880 AriaNg ─► aria2
```

## 4. Команды в чате

Обращение к боту — по имени, в начале сообщения: **«@бобик»** или **«бобик,»** (регистр не важен). Настоящее
упоминание `@bobik_borovskoy_bot` и ответ на сообщение бота тоже считаются обращением. В личке имя можно не писать.

| Команда | Что делает |
|---|---|
| `@бобик скачай <magnet или http(s)-ссылка>` | ставит закачку |
| `.torrent`-файл с подписью `@бобик скачай` | ставит закачку из файла (≤ 20 МБ) |
| `@бобик закачки` | список: номер, имя, %, скорость, осталось; последней строкой — свободно на SSD и HDD (за вычетом запаса) |
| `@бобик отмени N` | отменяет N-ю закачку из списка |
| `@бобик <любой другой текст>` | вопрос к GigaChat (как `@бобик` в Talk; квота общая по логину) |

Сообщения группы без обращения бот **отбрасывает сразу**: не обрабатывает, не хранит, не пишет в журнал.

Ответы бота: «⏬ Принял: <имя>» · «✅ Готово: <имя> — `\\192.168.0.50\hdd2tb\Downloads`» · «⏸ Пауза: на SSD
меньше 40 ГБ» · «❌ Не скачалось: <причина>». Уведомление о готовности — **в тот чат, откуда пришла команда**.

## 5. Компоненты

| Компонент | Где | Ответственность |
|---|---|---|
| образ `homecloud_downloads` | `services/downloads/`, сборка на Jetson | Alpine + `aria2` + AriaNg (версия и SHA-256 закреплены) + `busybox httpd` |
| `aria2.conf` | в образе | `.incomplete` на SSD по умолчанию, `seed-time=0`, ≤ 2 закачек одновременно, `pause-metadata=true`, сессия переживает перезапуск; `file-allocation`: `falloc` на SSD (ext4), `none` на HDD — ставится на закачку вместе с `dir` (предвыделение 100 ГБ через ntfs-3g заняло бы часы) |
| `on_stop.sh` | в образе | при отмене или ошибке удаляет недокачанное из `.incomplete` (иначе отменённые 100 ГБ остались бы на HDD). Страж места — в модуле `downloads` раз в 30 с (закачки из AriaNg он тоже видит), отдельный хук на старт не нужен |
| `on_complete.sh` | в образе | перенос файла или **верхнего каталога** многофайлового торрента в `Downloads/`: с SSD — копированием на HDD, из `Downloads/.incomplete` — переименованием в пределах HDD; при ошибке — остаётся на месте |
| `downloads` (модуль NAS API) | `services/nas_jetson_nano-api/app/` | разбор ссылки/файла; **выбор диска по размеру** (HTTP — размер из `HEAD` до старта; торрент — `pause-metadata`: после метаданных закачка на паузе, бот ставит `dir` и снимает паузу); отказ, если размер больше свободного на HDD минус запас; учёт «GID → чат, кто поставил» в атомарном JSON; опрос раз в 30 с: уведомления о готовности и **страж обоих дисков** (SSD ≥ `DL_SSD_MIN_FREE_GB`=40, HDD ≥ `DL_HDD_MIN_FREE_GB`=50 → пауза всех активных + сообщение) |
| `telegram_front` (минимальный) | там же | `getUpdates`/`sendMessage`/`getFile` через SOCKS, offset после обработки, белый список, выход из чужих групп, 429 → `retry_after` |
| юнит SOCKS | systemd на Jetson | `ssh -N -D 172.17.0.1:1080` к VPS с автоперезапуском: адрес docker0, иначе контейнер NAS API прокси не увидит; в LAN не слушает. Jetson напрямую до Telegram не доходит (замер 2026-09-19) |
| `speed_schedule` | systemd-таймеры | 08:00 — `DL_DAY_LIMIT` (6M ≈ 48 Мбит/с), 23:00 — без лимита |
| compose `docker-compose.downloads.yml` | `docker/compose/` | `mem_limit: 192m`, 6800/6880 в LAN, тома SSD и HDD, `ARIA2_RPC_SECRET` |

Samba, Nextcloud и VPS-сервисы **не меняются**. На VPS — только SSH-сессия SOCKS от Jetson (ключ уже есть).

## 6. Конфигурация (`config/.env` устройства; в git — пустые ключи)

`TELEGRAM_BOT_TOKEN` (записан) · `TELEGRAM_USERS` (`user_id:логин` через пробел) · `TELEGRAM_FAMILY_CHAT_ID` ·
`TELEGRAM_PROXY=socks5://172.17.0.1:1080` · `ARIA2_RPC_SECRET` · `DL_SSD_MIN_FREE_GB=40` · `DL_HDD_MIN_FREE_GB=50` ·
`DL_SSD_MAX_GB=20` · `DL_DAY_LIMIT=6M`.
Значения ID — `docs/local/IDENTIFIERS.md` (вне git): группа и владелец получены `getUpdates` 2026-09-19.

Замер 2026-09-19: SSD 229 ГБ, занято 14 ГБ (Immich 13 ГБ), свободно 204 ГБ → под закачки ≈ 164 ГБ; HDD свободно
438 ГБ → ≈ 390 ГБ с запасом. Узкое место — HDD (общий с архивом 1,4 ТБ): скачанное удалять после копирования на ПК.

## 7. Ошибки и безопасность

- **Режим приватности выключен**: Telegram отдаёт боту все сообщения группы «Боровские». Бот сразу отбрасывает
  всё без обращения «@бобик»; в журнал — только метаданные обращений. Бот состоит только в семейной группе,
  из чужих выходит.
- Чужие аккаунты и группы: один ответ «вы не в семейном списке» + сообщение владельцу с user_id; из чужих групп бот выходит.
- Ссылки только `magnet:`, `http://`, `https://` и `.torrent`-файл ≤ 20 МБ (лимит Bot API на сам файл-описание, не на закачку); `file://`, адреса LAN и
  `localhost` в HTTP-ссылках отклоняются (закачка не должна ходить во внутреннюю сеть).
- RPC aria2 и AriaNg — только LAN, по секрету. Снаружи управление — только через бота.
- Раздача торрентов выключена; что качать — ответственность семьи (торрент с домашнего IP виден в рое).
- Не больше двух закачек одновременно (CPU ntfs-3g). Страж раз в 30 с держит запас на SSD (Immich/Nextcloud)
  и на HDD (семейный архив 1,4 ТБ): при нехватке — пауза и сообщение «нужно ещё N ГБ». HDD недоступен → закачки
  на HDD на паузе, малые остаются на SSD.
- Бот недоступен (VPS/SOCKS) → закачки идут дальше, уведомления приходят после восстановления; AriaNg в LAN работает.
- В журналах — метаданные (кто, тип, размер), без ссылок целиком.

## 8. Тесты (TDD, в воротах)

- `downloads`: разбор magnet/HTTP/`.torrent`; отказ `file://` и LAN-адресов; выбор диска по размеру (19 ГБ → SSD,
  100 ГБ → HDD, не помещается на SSD с запасом → HDD, больше свободного на HDD → отказ); страж: порог пересечён
  во время закачки → пауза всех и одно сообщение; учёт GID→чат переживает
  перезапуск; уведомление уходит в исходный чат один раз; «закачки» и «отмени N».
- `telegram_front` (`httpx.MockTransport`): белый список, группа без обращения — тишина и ничего не записано,
  «@бобик скачай», «Бобик, закачки», упоминание `@bobik_borovskoy_bot`, ответ боту,
  `.torrent`-документ через `getFile`, offset после обработки, 429 с `retry_after`, выход из чужой группы.
- `on_complete.sh`: один файл; закачка из `Downloads/.incomplete` на HDD — переименование, без копирования; многофайловый торрент — переносится каталог; пробелы и кириллица; HDD недоступен;
  имя занято → суффикс без перезаписи. `on_stop.sh`: перед удалением недокачанного спрашивает статус по RPC (заглушка) — удаляет только `removed`/`error`, `active` и недоступный RPC не трогает. Страж по порогу — в модуле `downloads`, отдельного хука на старт нет.
- compose: `mem_limit`, порты, тома — статическая проверка.

## 9. Выкат (по «деплой»)

1. Правило №13 — ДО (на VPS появляется только SSH-сессия SOCKS).
2. `ARIA2_RPC_SECRET` (копия — Windows Credential Manager `nas-aria2-rpc-secret`), каталоги SSD/HDD.
3. Контейнер aria2, таймеры скорости; юнит SOCKS, `curl --socks5 127.0.0.1:1080 https://api.telegram.org`.
4. Владелец: @BotFather → `/setprivacy` → Disable; убрать бота из группы «Боровские» и добавить снова;
   проверить `getMe` → `can_read_all_group_messages=true`. Пересборка NAS API. `TELEGRAM_USERS` — `/start` семьи
   собран 2026-09-19 (4 человека, `docs/local/IDENTIFIERS.md`); `TELEGRAM_FAMILY_CHAT_ID` — группа «Боровские».
5. Проверка: в группе «@бобик скачай <magnet легального образа Linux>» и HTTP-файл → «принял» → «готово» → файл в
   `\\192.168.0.50\hdd2tb\Downloads`. 13 прежних контейнеров здоровы, свободно ≥ 1 ГБ ОЗУ.
6. Правило №13 — ПОСЛЕ.

---

### EN summary
A home downloader for the family, requested by the owner's son. Revision 2: the main interface is the
Telegram bot @bobik_borovskoy_bot, which is now in the family group. Revision 3: the bot is addressed by
name, as in Talk: "@бобик скачай <link>". Telegram does not treat that word as a mention, so the bot's group
privacy mode is turned off and every message without the name is dropped at once, unstored and unlogged. The downloader is the first slice of
the Telegram bot: transport over an SSH SOCKS tunnel to the VPS, a whitelist, download commands, and (revision 5)
GigaChat questions. Photos come in a later slice. Anyone in the family can send a magnet link, an HTTP link or a
`.torrent` file with "@бобик скачай". aria2 on the Jetson downloads it to
the SSD, moves it to `/mnt/hdd2tb/Downloads` when done (visible in Samba and Nextcloud), and the bot reports back
in the same chat. Revision 4: there is no size cap. Downloads up to 20 GB go through the SSD; larger ones (100 GB and more) are
written straight to the HDD, which keeps up with the home line. The 20 MB Telegram limit applies only to a
`.torrent` file sent in the chat. A guard checks both disks every 30 seconds (40 GB reserve on the SSD, 50 GB on
the HDD). No seeding, at most two parallel downloads and a daytime speed cap protect the system and the
family's internet. AriaNg on the LAN is a fallback. The VPS only carries the SOCKS session, so
nothing is downloaded there. Steam and a USB stick in the Jetson are out of scope.
Revision 5: GigaChat questions ("@бобик <question>") are part of the same slice and reuse the Talk path (safety
gate, gateway token, per-login quota). The SOCKS proxy listens on the docker0 address 172.17.0.1, because the
Jetson cannot reach Telegram directly (3 of 3 attempts timed out on 2026-09-19).
