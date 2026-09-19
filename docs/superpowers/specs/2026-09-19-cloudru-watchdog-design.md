# Внешний сторож в Cloud.ru — дизайн / External watchdog on Cloud.ru — design (2026-09-19)

> 🇷🇺 Задача **D3** плана `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`. Утверждено владельцем в двух частях
> 2026-09-19. EN summary — в конце.
> Статус: **спецификация**; реализация — после плана (writing-plans); выкат — только по «деплой».

## 1. Зачем

Сегодня о болезни системы сообщает только сама система (`31_MASTER_PLAN.md` §4.2). Если Jetson
обесточен (два случая: 17.08, 18.09; ИБП отложен владельцем 2026-09-19), умирают и его алерты.
Нужен наблюдатель, который **переживает смерть наблюдаемого** и стоит вне дома и вне VPS.

**Готово, когда:** выключенный туннель Jetson → тревога в Telegram владельцу за ≤ 20 мин, после
восстановления — «снова на связи, простой N мин».

## 2. Схема (выбор владельца: опрос через VPS)

```
Cloud.ru Container Job (раз в 10 мин, max instances=1, таймаут 60 с)
   │ ssh naswatch@VPS — ключ с restrict,command="/usr/local/bin/nas-liveness"
   ▼
VPS: nas-liveness (пользователь naswatch, без sudo)
   ├─ HTTP-запрос (urllib, таймаут 10 с) 127.0.0.1:18099/healthcheck   NAS API через обратный туннель
   ├─ HTTP-запрос (urllib, таймаут 10 с) 127.0.0.1:18080/status.php    Nextcloud через обратный туннель
   └─ /var/lib/naswatch/state.json — с какого момента не отвечает, когда слали тревогу
   ▲ одна строка JSON: {"event": "none|down|repeat|recovered", "text": "...", ...}
   │
Job → Telegram @bobik_borovskoy_bot → личный чат владельца
      запасной путь: `nas-liveness notify` — отправка через VPS (как ежедневный отчёт)
```

Отвергнуто: пульс от Jetson в постоянно работающий контейнер (≈150–1000 ₽/мес вне free tier и не
видит отказ VPS/туннеля); healthchecks.io (иностранный сервис, то же слепое пятно).

## 3. Компоненты

| Компонент | Где | Ответственность |
|---|---|---|
| `nas-liveness` | VPS, `/usr/local/bin` | проверки, состояние, решение «тревожить или нет»; подкоманды `check` и `notify` (текст и токен — через stdin) |
| пользователь `naswatch` + `authorized_keys` | VPS | `restrict,command=...`: ни оболочки, ни проброса, ни pty |
| `watchdog-job` | образ в Cloud.ru | ssh → разбор JSON → Telegram напрямую, при неудаче — через `notify`; правило «VPS молчит» |
| секреты | Cloud.ru | `TELEGRAM_BOT_TOKEN`, `OWNER_CHAT_ID`, приватный ключ ssh, `known_hosts` VPS |

Состояние живёт на VPS: задача в Cloud.ru ничего не помнит между запусками.

## 4. Правила тревог

| Условие | Сообщение |
|---|---|
| туннель закрыт (порт на VPS не отвечает) 2 проверки подряд | 🔴 NAS не отвечает с ЧЧ:ММ — туннель закрыт (питание, интернет дома или сам Jetson) |
| туннель открыт, сервис отвечает не 200 2 проверки подряд (любой код, включая 4xx — например, отказ Nextcloud по доверенному домену) | 🟠 Nextcloud (или NAS API) отвечает ошибкой, туннель жив |
| беда продолжается | повтор — раз в сутки |
| всё снова отвечает | ✅ NAS снова на связи, простой N мин |
| VPS не отвечает по ssh | 🔴 VPS не отвечает: у семьи нет внешнего доступа и VPN — **только в запуске с минутой 00–09 каждого часа** (состояние хранить негде; решение владельца) |

Одиночный сбой тревогой не считается.

## 5. Ошибки и безопасность

- Битый или отсутствующий `state.json` → считать «всё было хорошо», записать заново; проверку не ронять.
  Запись атомарная (tmp + rename).
- Ключ сторожа: отдельный пользователь без sudo, одна команда. Утечка раскрывает только «жив ли NAS»
  и даёт отправку текста через VPS токеном, который злоумышленник принесёт сам, и может «съесть»
  тревогу, вызвав `check` во время аварии.
- `known_hosts` VPS зафиксирован в секретах — подмена VPS не пройдёт молча.
- В журналах задачи нет токена и текста ответа Telegram, только код.
- VPS: новых портов нет, Amnezia и nginx не трогаются, sshd не перезапускается (`authorized_keys`
  читается при входе); `sshd -t` до и после. Правило №13 до/после.
- Токен семейного бота лежит в двух местах (`.env` Jetson и секреты Cloud.ru). **При смене токена
  менять в обоих** — пункт в runbook Telegram-бота.
- Стоимость: ≈4300 запусков/мес по несколько секунд — free tier Container Jobs (5 vCPU·ч, 10 ГБ·ч)
  или десятки рублей; контроль — E5.

## 6. Неизвестное — первым шагом (спайк в Cloud.ru)

| Вопрос | Если «нет» |
|---|---|
| Container Job доходит до `api.telegram.org` | основной путь — через VPS; при мёртвом VPS тревога не доставляется — слепое пятно записывается |
| Container Jobs умеют запуск по расписанию | Container Service с холодными экземплярами + внешний триггер — отдельное решение владельца |
| Образ: публичный `alpine` доступен из Cloud.ru | свой образ (alpine + openssh-client + скрипт) собирается на VPS (amd64) → Artifact Registry Cloud.ru |

## 7. Тесты (TDD, в воротах `preflight.sh`)

- `nas-liveness`: HTTP подменён (локальный http.server) — переходы жив → не отвечает (1 раз: тишина) → тревога → повтор
  через сутки → восстановление с длительностью простоя; различение «туннель закрыт» / «сервис 5xx»;
  битое состояние; атомарность.
- `watchdog-job`: `ssh` и HTTP подменены — правило «VPS молчит» по минуте часа; запасной путь через
  `notify`; токен не попадает в вывод.

## 8. Выкат (по «деплой»)

1. Правило №13 — ДО.
2. VPS: `naswatch`, скрипт, `authorized_keys`, `sshd -t`; ручной `ssh naswatch@VPS` → JSON.
3. Владелец: `/start` в @bobik_borovskoy_bot → `OWNER_CHAT_ID`.
4. Cloud.ru: секреты, задача раз в 10 мин (API сервисного аккаунта `home-nas-api` или пошагово в консоли).
5. Боевая проверка: туннель Jetson остановлен на 20 мин (время выбирает владелец; дома всё работает,
   снаружи NAS не виден) → тревога → туннель поднят → «снова на связи».
6. Правило №13 — ПОСЛЕ.

---

### EN summary
An outside watchdog for the NAS that survives the death of what it watches. A Cloud.ru Container Job runs
every 10 minutes and SSHes to the VPS with a key limited to a single command (a dedicated user with no sudo).
That command checks the NAS API and Nextcloud through the reverse tunnel, and keeps the alert state on the VPS.
Alerts go to the owner through the family Telegram bot, falling back to sending via the VPS. The watchdog tells
a closed tunnel (power, home internet or the Jetson itself) from a failing service. It alerts after two failed
checks in a row, repeats once a day and reports recovery with the downtime. When the VPS itself is down, it
alerts once an hour, because there is nowhere to keep state. No new ports are opened and Amnezia is not
touched. A first spike checks whether Cloud.ru can reach Telegram, whether Container Jobs support schedules,
and where the container image comes from.
