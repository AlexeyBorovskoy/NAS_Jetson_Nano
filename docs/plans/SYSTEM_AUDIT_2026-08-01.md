# Live-аудит системы 2026-08-01 / Live system audit 2026-08-01

> 🇷🇺 Сводный отчёт read-only аудита живой системы (jump `VPS → Jetson`). Детальные замеры и методика —
> в [MEASUREMENTS_EN.md](../articles/MEASUREMENTS_EN.md); проверенная фактура — в
> [PROJECT_FACTS_EN.md](../articles/PROJECT_FACTS_EN.md); блокеры — в [GAPS_EN.md](../articles/GAPS_EN.md).
>
> 🇬🇧 Summary of a read-only audit of the live system (`VPS → Jetson` jump). Detailed measurements and method are
> in [MEASUREMENTS_EN.md](../articles/MEASUREMENTS_EN.md); verified facts in
> [PROJECT_FACTS_EN.md](../articles/PROJECT_FACTS_EN.md); blockers in [GAPS_EN.md](../articles/GAPS_EN.md).

## ⚠️ Требует действия / Action required

### 1. Сервисы открыты в интернет / Services exposed to the internet — 🔴
- 🇷🇺 На VPS публично (`0.0.0.0`) слушают Nextcloud (8080/8443), Immich (2283/2443), **LLM Gateway (8090/9443)** и
  **admin-API `nas-api` (8099)**, Beszel (8091). Правило №4 («сервисы не открыты напрямую в интернет») **нарушено** —
  замечание читателей Habr про открытые порты справедливо. Самое опасное — публичные admin-API и LLM-шлюз.
  **Рекомендация:** увести за VPN/Tailscale, admin-API и LLM наружу не публиковать.
- 🇬🇧 On the VPS, public `0.0.0.0` listeners: Nextcloud (8080/8443), Immich (2283/2443), **LLM Gateway (8090/9443)**,
  **admin API `nas-api` (8099)**, Beszel (8091). Rule #4 is **violated**; the readers' "open ports" criticism is
  correct. The public admin API and LLM gateway are the worst offenders. **Fix:** move behind VPN/Tailscale.

### 2. Бэкапы устарели / Backups are stale — 🔴
- 🇷🇺 Последний дамп — **2026-07-24 (8 дней назад)**, хотя таймер `nasa-backup` активен. 14 файлов = 7-дневная
  ротация (Jul 18–24), затем пусто → запись, вероятно, сломалась ~24 июля. **Восстановление ни разу не проверялось.**
  Это риск потери данных. **Рекомендация:** разобрать причину (mount/fail-closed), проверить restore.
- 🇬🇧 Newest dump is **2026-07-24 (8 days old)** although the `nasa-backup` timer is active. 14 files = a 7-day
  rotation (Jul 18–24), then nothing → writes likely broke ~Jul 24. **Restore has never been tested.** Data-loss
  risk. **Fix:** find the cause (mount / fail-closed guard) and test restore.

## ✅ Измерено / Measured (2026-08-01)

| Показатель / Metric | Значение / Value |
|---|---|
| Питание платы простой / Board power idle | **2.30 W** (min 1.33, max 4.36; INA3221 rail0, 120×1 s) |
| Питание под нагрузкой / Board power load | **4.17 W** (4× `yes`, all cores) — SSD не входит / SSD not included |
| Immich | **7 098** объектов = **6 686 фото + 412 видео**, 8.9 ГБ |
| Nextcloud | 5 пользователей / users; данные 254 МБ; БД 349 МБ (на SSD) |
| API | **21** эндпоинт (15 GET + 6 POST) |
| Задержка / Latency | локально NC ~45 мс / Immich ~7 мс; туннель ~230 мс; цена туннеля ≈ **+190 мс** |
| Стабильность / Stability | **0 OOM**, **0 рестартов контейнеров** за 30 д; аптайм 23 д |
| Туннель / Tunnel | сервис рестартовал 6×, ~160 реконнектов autossh (самовосстановление) |
| Recovery | `nasa-ssd-recovery` 1×, `nasa-usb-monitor` 2× за 30 д |

## 🔍 Снятые противоречия / Contradictions resolved

- 🇷🇺 **Immich**: `immich_server` и `immich_microservices` — один образ `ghcr.io/immich-app/immich-server:release`,
  различие только в команде → Immich 2.7.5 в **легаси-топологии** (отдельный microservices-воркер). Тег `:release`
  не запинён. 🇬🇧 Immich 2.7.5 in the **legacy two-container topology**; `:release` tag is unpinned.
- 🇷🇺 **Память**: сумма `mem_limit` ≈ 94% ОЗУ + `homecloud_samba` **без лимита** → конфиг оверкоммитит (факт ~1.7 ГБ).
  🇬🇧 Mem limits ≈ 94% of RAM + samba unbounded → config overcommits (live use ~1.7 GB).
- 🇷🇺 **Давление на память**: PSI нет (ядро 4.9); в swap ~714 МБ, но `si/so=0` в простое — swap есть, трэшинга нет,
  запаса под тяжёлое почти нет. 🇬🇧 No PSI; ~714 MB in zram but no thrashing at idle; little headroom.

## ⏳ Осталось / Still open

| Пункт / Item | Статус / Status | Как снять / How |
|---|---|---|
| `fio` по диску / disk fio | pending (разрешено / authorized) | окно низкой нагрузки; сверить с ~250 МБ/с |
| Пропускная способность туннеля / tunnel throughput | pending | 100 МБ WebDAV, LAN vs туннель |
| Контакты/календари / contacts & calendars | pending | `oc_cards` / `oc_calendarobjects` |
| Тест восстановления бэкапа / backup restore test | pending | восстановить дамп в тестовую БД |
| Температура SSD / SSD temperature | 🔴 blocked | JMS583 SAT не отдаёт атрибут; smartmontools 6.6 стар |

## Методика и гигиена / Method & hygiene

- 🇷🇺 Всё read-only; привилегированные чтения — через helper, берущий sudo-пароль из `~/nasa/config/.env`
  (`NEXTCLOUD_ADMIN_PASSWORD`); пароль **не передавался по SSH, не печатался, не коммитился**. Нагрузка — синтетическая
  (`yes` по ядрам). Temp-скрипты в `/tmp` устройства (эфемерны, чистятся при ребуте).
- 🇬🇧 All read-only; privileged reads via a helper that sources the sudo password from `~/nasa/config/.env`; the
  password was **never sent over SSH, printed, or committed**. Load was synthetic (`yes` per core). Temp scripts live
  in the device `/tmp` (ephemeral).
