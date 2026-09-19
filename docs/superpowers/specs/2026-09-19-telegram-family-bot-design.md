# Семейный бот в Telegram — дизайн / Telegram family bot — design (2026-09-19)

> 🇷🇺 Утверждено владельцем по частям 2026-09-19. EN summary — в конце.
> Статус: **спецификация**, реализация — после плана (writing-plans) и отдельного «деплой».

## 1. Зачем

Дети и жена не пользуются Nextcloud Talk, а Telegram у них уже есть. `@бобик` и
уведомления NAS должны прийти туда, где семья уже общается. Talk **остаётся параллельно**
как запасной домашний канал: на случай блокировки или замедления Telegram в РФ и падения VPS.

**Не делаем:** Telegram Serverless (статья habr 1083944). Код там живёт в облаке Telegram
и не видит NAS без открытия его в интернет (правило №4). Ключ GigaChat пришлось бы
держать там, в обход шлюза. Платформа только JavaScript.

**Осознанная цена:** переписка семьи с ботом хранится у Telegram. Фото проходят через
серверы Telegram, но оседают только в Immich дома.

## 2. Пользователи

| Логин (Nextcloud/Immich) | Роль |
|---|---|
| `admin` | владелец (вы): технические подробности, алерты |
| `olga`, `ivan`, `ulyana` | семья |

`anna` исключена (решение владельца). Сопоставление Telegram user_id → логин — в `.env`
устройства; значений в git нет (C7).

## 3. Архитектура

```
Telegram ⇄ интернет ⇄ VPS ══ SSH SOCKS (новый юнит) ══► Jetson: контейнер NAS API
                                                        ├─ telegram_front  (новый)
                                                        ├─ talk_front      (нынешний talk_bot)
                                                        └─ bot_core        (выделен из talk_bot.py)
                                                             ├─ команды статус/диск/фото (локально)
                                                             ├─ safety gate ADR-0011 → LLM Gateway (токен, квоты, redaction)
                                                             └─ фото → Immich
```

| Компонент | Ответственность | Зависит от |
|---|---|---|
| `bot_core` | канал-независимая логика: `handle(IncomingMessage) -> list[Reply]` | gate, шлюз, Immich, локальные команды |
| `talk_front` | опрос Talk, отправка ответов; поведение для семьи не меняется | `bot_core`, Nextcloud OCS |
| `telegram_front` | `getUpdates` (long polling), `sendMessage` / `sendChatAction` / `getFile`, offset | `bot_core`, SOCKS `127.0.0.1:1080` |
| юнит SOCKS | `ssh -N -D 127.0.0.1:1080` к VPS, autossh-перезапуск | ключ туннеля; **рабочий обратный туннель не трогается** |

## 4. Функции

> **Поправка 2026-09-19 (решение владельца):** в группе к боту обращаются **по имени** — «@бобик …» или
> «бобик, …», как в Talk; режим приватности в группе **выключается**, сообщения без обращения отбрасываются
> сразу, не хранятся и не пишутся в журнал. Первый срез бота — качалка **и** вопросы к GigaChat
> (`2026-09-19-home-downloader-design.md`, ред. 5); фото — следующим срезом.

1. **Вопросы.** В личке — любое сообщение. В группе — только с обращением «@бобик» / «бобик,»,
   упоминанием `@bobik_borovskoy_bot` или ответом боту. Путь: gate → шлюз (`X-Service-Token`) → GigaChat. Квота по логину, общая с Talk.
   Во время ожидания показывается «печатает…».
2. **Фото → Immich.** Из лички — в личную библиотеку отправителя (его API-ключ Immich). Из группы —
   в альбом «Из Telegram», которым поделились с семьёй (ключ `admin`), и **только** при подписи
   с обращением к боту («@бобик»). Режим приватности в группе выключается (см. поправку выше).
   «Фото» (сжатое Telegram) сохраняется с подсказкой «для оригинала — файлом»; «файл» приходит
   оригиналом с EXIF. Лимит Bot API — 20 МБ: больше — честный отказ и совет загрузить через
   приложение Immich. Анализа фото нет: `LLM_ALLOW_IMAGE_ANALYSIS=false`.
3. **Уведомления.** Уведомления NAS API идут в Talk **и** Telegram. Технические — в личку
   владельца, семейные — в группу. Ежедневный отчёт остаётся на ретрансляторе через VPS.
4. **Команды.** `/status`, `/disk`, `/photos` и русские «статус», «диск», «фото» — из данных
   NAS, наружу ничего. Подробности (контейнеры, логи) — только владельцу (роли C2).
5. **Регистрация.** `/start` от неизвестного аккаунта: один ответ «вы не в семейном списке»
   и сообщение владельцу с его user_id. Больше таким аккаунтам бот не отвечает. Из чужих групп бот выходит.

## 5. Конфигурация (`.env` устройства; в git — только пустые ключи в `.env.example`)

| Ключ | Смысл |
|---|---|
| `TELEGRAM_BOT_TOKEN` | токен бота (записан 2026-09-19, права 600; копия — Windows Credential Manager `nas-telegram-bot-token`) |
| `TELEGRAM_USERS` | `user_id:логин` через пробел |
| `TELEGRAM_FAMILY_CHAT_ID` | ID семейной группы |
| `TELEGRAM_OWNER_LOGIN` | `admin` — кому технические алерты |
| `TELEGRAM_PROXY` | `socks5://127.0.0.1:1080` |
| `IMMICH_USER_KEYS` | `логин:ключ` через пробел (olga, ivan, ulyana, admin) |
| `IMMICH_TELEGRAM_ALBUM` | имя общего альбома, по умолчанию «Из Telegram» |

## 6. Ошибки

| Ситуация | Поведение |
|---|---|
| SOCKS/VPS недоступен | повторы с паузой до 60 с; > 15 мин — алерт владельцу через Talk |
| Telegram 429 | ждать `retry_after` |
| шлюз/Immich недоступны | вежливый ответ в чат; ошибка и счётчики — в `/v1/talk/bot/status` |
| сбой посреди обработки | offset сохраняется атомарно **после** обработки; повтор возможен, потеря — нет; дубли фото — по `file_unique_id` |
| файл > 20 МБ / не картинка | отказ с объяснением |

## 7. Безопасность

- Белый список user_id и одна семейная группа; остальным — только ответ из §4 п. 5.
- Секреты — только `.env` устройства (C7). Тест `test_no_identifiers` расширяется хэшем токена.
- SOCKS слушает только `127.0.0.1`. Портов наружу нет, Amnezia не затрагивается (правило №13).
- В логах только метаданные (кто, тип, размер), без текста сообщений.
- ⚠️ Текущий токен виден в чате сессии. Перед подключением семьи — **Revoke** в @BotFather,
  новый токен передать через файл, а не через чат.

## 8. Тесты

- `bot_core`: команды, gate до фото, квоты, роли — через фейковый канал.
- `telegram_front`: `httpx.MockTransport` — белый список, группа без обращения «@бобик», 20 МБ,
  сжатое фото против файла, повтор offset, 429 с `retry_after`, выход из чужой группы.
- Регрессия Talk: существующие тесты `tests/nas_api` и `tests/unit` зелёные после выделения ядра.
- Ворота и CI без изменений (тесты сервисов уже в них).

## 9. Выкат (по «деплой»)

1. Юнит SOCKS-туннеля; проверить `curl --socks5 127.0.0.1:1080 https://api.telegram.org`.
2. Ключи Immich для olga, ivan, ulyana, admin — создаются в их учётных записях → `IMMICH_USER_KEYS`.
3. Альбом «Из Telegram» с доступом для семьи.
4. Пересборка API; smoke `@бобик` в Talk (регрессия) и в Telegram.
5. `/start` от каждого → `TELEGRAM_USERS`; бота добавить в семейную группу → `TELEGRAM_FAMILY_CHAT_ID`.
6. Правило №13 до и после.

---

### EN summary
A Telegram front-end for the existing family bot, because the family does not use Nextcloud Talk.
Talk stays in parallel as a fallback. The bot runs on the Jetson inside the NAS API container, and
its logic is shared with Talk through a new `bot_core` extracted from `talk_bot.py`. It reaches
Telegram by long polling through a separate SSH SOCKS tunnel to the VPS: no open ports, and the
existing reverse tunnel is untouched. Features: LLM questions through the gateway (safety gate,
per-login quotas), photos to Immich (DMs to the sender's personal library, group photos with a
mention to a shared album), notifications in both channels, and local status commands. Access is
limited by a whitelist of user IDs (admin, olga, ivan, ulyana) and one family group. Telegram
Serverless was rejected because it cannot reach the NAS without exposing it to the internet.

Amendment 2026-09-19: in the group the bot is addressed by name ("@бобик ..."), as in Talk. Group privacy
mode is turned off, and messages without the name are dropped at once, unstored and unlogged. The first slice
of the bot is the home downloader.
