# Точка проекта 2026-08-30 / Project checkpoint 2026-08-30

🇷🇺 День аудита и приведения документации в порядок. Устройство и VPS **не менялись** —
все проверки read-only, все правки в git.

🇬🇧 A day of auditing and putting documentation in order. The device and the VPS were
**not modified** — every check was read-only, every change landed in git.

**Коммиты дня / Commits:** `42ee9dd`, `fbb98e1`, `7707d0e`, `25d1140`, `8d397b8`, `15981bd`.

---

## 1. Расхождение git ↔ устройство: часть A закрыта / divergence, part A closed

🇷🇺 Построчно сверены все 13 изменённых на устройстве файлов с текущим git. Найдены
**3 реальных прод-фикса, которых в git не было** — они пропали бы молча при будущем
деплое: шара `hdd2tb` в Samba, `/mnt/hdd2tb` как bind-mount в Nextcloud и Samba,
увеличенные `mem_limit` netdata (256→320m) и uptime-kuma (128→192m). Перенесены в git.

🇬🇧 All 13 files modified on the device were compared line by line against current git.
Three real production fixes were missing from git and would have been silently lost on a
future deploy: the `hdd2tb` Samba share, the `/mnt/hdd2tb` bind mount in Nextcloud and
Samba, and raised `mem_limit` values. They are now in git.

🔴 **Отдельно закрыт риск дублирования сервиса.** `docker-compose.nas_jetson_nano-api.yml`
переименовывал реально работающий контейнер `homecloud_nasa_api` →
`homecloud_nas_jetson_nano_api`. Порт 8099 занят старым контейнером — наивный деплой
поднял бы **второй, конкурирующий** контейнер Talk-бота либо упал по конфликту порта.
Решение владельца: контейнер не переименовывать. Откачено.

🇬🇧 A service-duplication risk was closed: the compose file renamed the live
`homecloud_nasa_api` container, and a naive deploy would have started a second competing
Talk-bot container on the occupied port 8099. Per the owner's decision the container keeps
its old name.

🟠 **Часть B (физический переезд устройства) не выполнялась** — требует окна обслуживания,
трогает активный туннель, USB-watchdog и работающий `jetson-nas-health.timer`. Готовый
пошаговый runbook с процедурой отката — в плане сессии (см. `AUDIT_REPORT.md` §29
Protected Components и `TECHNICAL_DEBT.md` TD-01).

---

## 2. Полный технический аудит проекта / full technical audit

🇷🇺 Выполнен по промту `docs/audit/jetson_project_full_audit_prompt.md` — три параллельных
read-only проверки живой системы + синтез. Результат: **12 файлов + машиночитаемая сводка**
в `docs/audit/`.

🇬🇧 Performed per the prompt in `docs/audit/` — three parallel read-only investigations of
the live system plus synthesis. Result: 12 report files plus a machine-readable summary.

**Главные находки / key findings:**

| Приоритет | Находка / Finding |
|---|---|
| **P0** | Фото Immich (~6–9 ГБ) без off-site бэкапа — единственная находка уровня CRITICAL / Immich photos have no off-site copy |
| **P1** | Расхождение git↔устройство (часть B) / device migration not done |
| **P1** | Ubuntu 18.04.6 (EOL 04/2023) и Python 3.6.9 (EOL 12/2021) как база хоста; ESM не подтверждён / host OS and Python are EOL |
| **P2** | `coturn` описан в compose, но **никогда не разворачивался на VPS** — видеозвонки Talk вне LAN, вероятно, не проходят NAT (гипотеза, живым звонком не проверена) |
| **P2** | CORS `*` на API :8099; JWT-секрет может генерироваться заново при каждом рестарте |
| **факт** | GPU/CUDA 10.2/TensorRT 8.2 установлены, но **не используются ни одним сервисом** — `GR3D_FREQ 0%` на всех замерах. Осознанный выбор: 4 ГБ RAM не оставляют запаса |

🇷🇺 **Итоговые оценки (0–5):** архитектура 4, надёжность 4, производительность 5,
безопасность 3, наблюдаемость 3, сопровождаемость 3, документация 3,
воспроизводимость 2, готовность к обновлению 2, запас железа 2.

🇷🇺 **Восстановление с нуля: PARTIALLY.** БД — да (проверено дважды). Фото — нет
(единственная копия). `.env` существует только на устройстве без redacted-снапшота.

---

## 3. Документация приведена в соответствие правилу №15 / documentation brought in line

🇷🇺 Отдельная проверка нашла два класса проблем.

**Актуальность:** пять документов описывали off-site бэкап как несделанный, хотя фаза 1
в бою с 24.08. Исправлены `README.md`, `docs/12_BACKUP_RESTORE.md`,
`docs/31_MASTER_PLAN.md`, `docs/plans/WAVE_0_OFFSITE_BACKUP.md` (врезка противоречила
собственному телу файла), `CHANGELOG.md` (две записи от 24.08 отсутствовали вовсе).

**Двуязычность:** 56 файлов не отвечали правилу №15 — 14 переведены только в заголовке,
~42 монолингвальны. **50 документов доведены до RU+EN** шестью параллельными субагентами
и ручной доводкой. Проверка перед коммитом: сверено множество кириллических слов до и
после по каждому файлу — ни одно русское слово не потеряно.

🇬🇧 A documentation audit found five documents still describing the off-site backup as
not done (phase 1 has been live since 2026-08-24) and 56 files failing the bilingual rule.
Both are fixed; 50 documents were brought to RU+EN.

🇷🇺 Удалён `docs/prompts/Востановление общения.md` — случайно сохранённая распечатка
сессии агента (XML-обёртки, пути к temp-файлам), а не документ. В git он никогда не
попадал.

---

## 4. Мелкие, но важные починки / small but load-bearing fixes

🇷🇺 **`check_no_secrets.sh` ломал каждый коммит.** Ловил `RESTIC_PASSWORD_FILE=/root/...`
— это **путь** к секрету, а не значение; тот же паттерн у docker secrets
(`password_file: /run/secrets/...`). Добавлено узкое исключение для `*_FILE`/`*_PATH`
со значением-путём. Проверено, что настоящий секрет по-прежнему ловится.

🇬🇧 The secret scanner was blocking every commit on a *path to* a secret rather than a
secret value. A narrow exception was added; verified that a real secret is still caught.

🇷🇺 **`nas_jetson_nano-ddns-update.service`** ссылался на `/root/nas_jetson_nano/...` —
путь, не совпадающий ни с текущим (`/home/admin/nasa`), ни с целевым. Исправлен.

---

## 5. AmneziaVPN: разведка новой версии / new client version reconnaissance

🇷🇺 Вышла **5.0.1.5** (21.08.2026), у владельца стоит 4.8.19.0. Проверено: ни в одном
changelog от 4.8.18.0 до 5.0.1.5 **нет упоминаний SSH-провижининга**. Два наиболее
похожих issue (#2011 — тот же `ErrorCode 305`; #2837 — приложение не пишет в
`clientsTable`) **открыты без ответа мейнтейнеров**. Единственный закрытый смежный
(#845) закрыт не фиксом логики, а подсказкой в UI.

**Вывод:** обновление даёт security-фикс и AWG 3.1, но **рассчитывать на починку нашего
дефекта нельзя**. Ручной обход через `wg set` остаётся основным путём. VPS обновление не
затрагивает — это только Windows-клиент.

🇬🇧 Version 5.0.1.5 is out, but no changelog entry or closed issue indicates the SSH
provisioning defect is fixed; the manual `wg set` workaround remains the working path.

---

## 6. Инструкция для семьи / family onboarding guide

🇷🇺 Собрана пошаговая инструкция для Вани, Оли и Ули: установка Nextcloud Talk и Immich,
вход, включение автозагрузки фото, доступ вне дома через VPN, раздел «если не работает».
Все данные проверены на живом сервере, паролей в документе нет намеренно.

🔴 **Хранится вне git** — `docs/local/domashnee-oblako-instrukciya.html` (папка исключена
через `.git/info/exclude`). Причина: репозиторий **публичный**, а документ содержит
логины членов семьи и внутренние адреса.

🇬🇧 A step-by-step onboarding guide for three family members was produced and is kept
**outside git** — the repository is public and the document contains family logins.

---

## 7. Что осталось открытым / what stays open

| Вопрос / Question | Состояние |
|---|---|
| Off-site бэкап фото Immich (фаза 2) | **P0**, не начата |
| Часть B миграции устройства | runbook готов, окно не назначено |
| Решение по EOL Ubuntu 18.04 | принять риск / ESM / план замены платы — не решено |
| `coturn` на VPS | развернуть или явно списать; живым звонком не проверялось |
| Второй IP на VPS | идея владельца, оценка дана, плана нет |
| Аня без аккаунта Immich | есть в Nextcloud, в Immich отсутствует — решение за владельцем |
| План развития `plan_new.md` | разобран; три расхождения с фактами аудита — см. ниже |

🇷🇺 **По `plan_new.md`:** фаза 0 (off-site фото) верна и совпадает с P0. Но план
пропускает P1 (миграция устройства), содержит шаги «JetPack 4.6.6» и «Ubuntu 20.04+»,
которых для Jetson Nano **не существует** (4.6.1 — потолок платформы), а фаза 4
(GPU-инференс на самом Nano) противоречит собственному разделу «не трогать» и факту
1.4–1.5 ГБ свободной RAM. Рекомендовано: GPU-эксперименты увести в Kaggle/Lightning.ai
или на Vostro.

---

## 8. Обнаруженные расхождения в самой документации / doc drift found

🇷🇺 `CLAUDE.md` называет логин администратора Immich `admin@nas_jetson_nano.local` —
**на устройстве он `admin@nasa.local`**. Тот же rename-долг. Не исправлено в этой
сессии, зафиксировано здесь.

🇷🇺 Число незакоммиченных правок на устройстве уточнено: **33 строки `git status`**
(13 изменённых файлов + 20 бэкапов `.bak.*`), а не «более 10».
