# Домашняя качалка на Jetson — дизайн / Home downloader on the Jetson — design (2026-09-19)

> 🇷🇺 Запрос сына, приоритет владельца. Утверждено владельцем 2026-09-19; **редакция 2** того же дня:
> главный интерфейс — **чат с ботом @bobik_borovskoy_bot** (бот добавлен в семейную группу «Боровские»).
> EN summary — в конце. Статус: **спецификация**; реализация — после плана; выкат — только по «деплой».

## 1. Зачем и что считается готовым

Сын хочет ставить закачку больших файлов и торрентов, когда его нет дома, а потом дома забирать
результат по Wi-Fi или кабелем на свой компьютер. Команду он даёт **в Telegram** — там, где семья уже общается.

**Готово, когда:** в семейной группе или в личке с ботом отправлена magnet-ссылка, HTTP-ссылка или
`.torrent`-файл → бот отвечает «принял» → файл качается на SSD → по завершении сам оказывается в
`\\192.168.0.50\hdd2tb\Downloads\` → бот пишет в тот же чат «✅ Готово: <имя>».

## 2. Решения

| Вопрос | Решение | Почему |
|---|---|---|
| Где качать | **Jetson, домашний интернет** | VPS держит VPN ~25 человек: жалоба правообладателя хостеру (AEZA) грозит блокировкой IP (правило №13); места на VPS мало |
| Чем | **aria2** — один демон на торренты (magnet, `.torrent`) и HTTP/HTTPS | ≈30–60 МБ ОЗУ, есть в Alpine для arm64, JSON-RPC |
| Интерфейс | **чат с ботом** — главный (решение владельца); AriaNg в LAN — запасной | команды там, где семья; веб-страница — если бот недоступен |
| Кому | **вся семья** (решение владельца): белый список Telegram user_id + одна группа | общая папка `Downloads` |
| Транспорт бота | как в спецификации Telegram-бота: long polling через SSH SOCKS к VPS, код в контейнере NAS API | портов наружу нет; рабочий обратный туннель не трогается |
| Порядок с Telegram-ботом | **качалка — первый срез Telegram-бота**: транспорт, белый список, команды закачек. Вопросы к LLM и фото — следующими срезами той же спецификации | приоритет владельца |
| Steam | **не делаем** на Jetson | SteamCMD только x86, у Jetson ARM; игры Steam привязаны к аккаунту. У сына — удалённая установка из мобильного Steam на свой ПК |
| Флешка в Jetson | **не на этом этапе** | два необъяснённых аппаратных сброса Jetson; SSD и HDD уже на USB |

## 3. Схема

```
Telegram (группа «Боровские» / личка) ⇄ VPS ══ SSH SOCKS 127.0.0.1:1080 ══► Jetson
                                                                             │
   контейнер NAS API: telegram_front ─► downloads (команды, учёт) ─JSON-RPC+секрет─► aria2 :6800
                                                                                      │
                          /mnt/storage/downloads/.incomplete  (SSD, идёт закачка)     │
                                                                                      │ on-download-complete
                          /mnt/hdd2tb/Downloads/<имя>          (HDD, готово)      ◄───┘
                                     │
          Samba \\192.168.0.50\hdd2tb\Downloads  ·  Nextcloud /HDD-2TB/Downloads (снаружи — через VPN)

   запасной путь: браузер в LAN ─► :6880 AriaNg ─► aria2
```

## 4. Команды в чате

| Где | Как |
|---|---|
| личка | любое сообщение с magnet/HTTP-ссылкой или `.torrent`-файл — сразу закачка |
| группа | `/dl <ссылка>`, ответ на сообщение бота, или упоминание `@bobik_borovskoy_bot` со ссылкой; `.torrent` — с подписью-упоминанием. Режим приватности группы включён: остальные сообщения бот не видит |
| обе | `/dls` — список: имя, %, скорость, осталось; `/cancel N` — отменить N-ю из списка |

Ответы бота: «⏬ Принял: <имя>» · «✅ Готово: <имя> — `\\192.168.0.50\hdd2tb\Downloads`» · «⏸ Пауза: на SSD
меньше 40 ГБ» · «❌ Не скачалось: <причина>». Уведомление о готовности — **в тот чат, откуда пришла команда**.
Русские синонимы без слэша («скачай <ссылка>», «закачки», «отмени N») — в личке и с упоминанием в группе.

## 5. Компоненты

| Компонент | Где | Ответственность |
|---|---|---|
| образ `homecloud_downloads` | `services/downloads/`, сборка на Jetson | Alpine + `aria2` + AriaNg (версия и SHA-256 закреплены) + `busybox httpd` |
| `aria2.conf` | в образе | `.incomplete` на SSD, `seed-time=0`, ≤ 2 закачек одновременно, `file-allocation=falloc`, сессия переживает перезапуск |
| `on_start.sh` | в образе | **SSD-страж**: свободно на `/mnt/storage` < `DL_SSD_MIN_FREE_GB` (40) → пауза через RPC |
| `on_complete.sh` | в образе | перенос файла или **верхнего каталога** многофайлового торрента на HDD; при ошибке — остаётся на SSD |
| `downloads` (модуль NAS API) | `services/nas_jetson_nano-api/app/` | разбор ссылки/файла, вызовы aria2 RPC, учёт «GID → чат, кто поставил» в атомарном JSON, опрос завершённых раз в 30 с и уведомления |
| `telegram_front` (минимальный) | там же | `getUpdates`/`sendMessage`/`getFile` через SOCKS, offset после обработки, белый список, выход из чужих групп, 429 → `retry_after` |
| юнит SOCKS | systemd на Jetson | `ssh -N -D 127.0.0.1:1080` к VPS с автоперезапуском |
| `speed_schedule` | systemd-таймеры | 08:00 — `DL_DAY_LIMIT` (6M ≈ 48 Мбит/с), 23:00 — без лимита |
| compose `docker-compose.downloads.yml` | `docker/compose/` | `mem_limit: 192m`, 6800/6880 в LAN, тома SSD и HDD, `ARIA2_RPC_SECRET` |

Samba, Nextcloud и VPS-сервисы **не меняются**. На VPS — только SSH-сессия SOCKS от Jetson (ключ уже есть).

## 6. Конфигурация (`config/.env` устройства; в git — пустые ключи)

`TELEGRAM_BOT_TOKEN` (записан) · `TELEGRAM_USERS` (`user_id:логин` через пробел) · `TELEGRAM_FAMILY_CHAT_ID` ·
`TELEGRAM_PROXY=socks5://127.0.0.1:1080` · `ARIA2_RPC_SECRET` · `DL_SSD_MIN_FREE_GB=40` · `DL_DAY_LIMIT=6M`.
Значения ID — `docs/local/IDENTIFIERS.md` (вне git): группа и владелец получены `getUpdates` 2026-09-19.

## 7. Ошибки и безопасность

- Чужие аккаунты и группы: один ответ «вы не в семейном списке» + сообщение владельцу с user_id; из чужих групп бот выходит.
- Ссылки только `magnet:`, `http://`, `https://` и `.torrent` ≤ 20 МБ (лимит Bot API); `file://`, адреса LAN и
  `localhost` в HTTP-ссылках отклоняются (закачка не должна ходить во внутреннюю сеть).
- RPC aria2 и AriaNg — только LAN, по секрету. Снаружи управление — только через бота.
- Раздача торрентов выключена; что качать — ответственность семьи (торрент с домашнего IP виден в рое).
- Перенос на NTFS нагружает CPU — не больше двух закачек. HDD недоступен → файл остаётся на SSD; SSD-страж
  бережёт место Immich/Nextcloud.
- Бот недоступен (VPS/SOCKS) → закачки идут дальше, уведомления приходят после восстановления; AriaNg в LAN работает.
- В журналах — метаданные (кто, тип, размер), без ссылок целиком.

## 8. Тесты (TDD, в воротах)

- `downloads`: разбор magnet/HTTP/`.torrent`; отказ `file://` и LAN-адресов; учёт GID→чат переживает
  перезапуск; уведомление уходит в исходный чат один раз; `/dls` и `/cancel N`.
- `telegram_front` (`httpx.MockTransport`): белый список, группа без упоминания — тишина, `/dl@bot`,
  `.torrent`-документ через `getFile`, offset после обработки, 429 с `retry_after`, выход из чужой группы.
- `on_complete.sh`: один файл; многофайловый торрент — переносится каталог; пробелы и кириллица; HDD недоступен;
  имя занято → суффикс без перезаписи. `on_start.sh`: страж по порогу (RPC подменён).
- compose: `mem_limit`, порты, тома — статическая проверка.

## 9. Выкат (по «деплой»)

1. Правило №13 — ДО (на VPS появляется только SSH-сессия SOCKS).
2. `ARIA2_RPC_SECRET` (копия — Windows Credential Manager `nas-aria2-rpc-secret`), каталоги SSD/HDD.
3. Контейнер aria2, таймеры скорости; юнит SOCKS, `curl --socks5 127.0.0.1:1080 https://api.telegram.org`.
4. Пересборка NAS API. Семья пишет боту `/start` → `TELEGRAM_USERS`; `TELEGRAM_FAMILY_CHAT_ID` — группа «Боровские».
5. Проверка: в группе `/dl <magnet легального образа Linux>` и HTTP-файл → «принял» → «готово» → файл в
   `\\192.168.0.50\hdd2tb\Downloads`. 13 прежних контейнеров здоровы, свободно ≥ 1 ГБ ОЗУ.
6. Правило №13 — ПОСЛЕ.

---

### EN summary
A home downloader for the family, requested by the owner's son. Revision 2: the main interface is the
Telegram bot @bobik_borovskoy_bot, which is now in the family group. The downloader is the first slice of
the Telegram bot: transport over an SSH SOCKS tunnel to the VPS, a whitelist, and download commands. LLM
questions and photos come in later slices. Anyone in the family can send a magnet link, an HTTP link or a
`.torrent` file in a direct message, or use `/dl` or a mention in the group. aria2 on the Jetson downloads it to
the SSD, moves it to `/mnt/hdd2tb/Downloads` when done (visible in Samba and Nextcloud), and the bot reports back
in the same chat. An SSD guard, no seeding, at most two parallel downloads and a daytime speed cap protect the
system and the family's internet. AriaNg on the LAN is a fallback. The VPS only carries the SOCKS session, so
nothing is downloaded there. Steam and a USB stick in the Jetson are out of scope.
