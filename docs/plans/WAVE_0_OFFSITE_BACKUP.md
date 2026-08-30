# Волна 0 — off-site бэкап на Vostro

> **Обновлено 2026-08-24 (конец дня).** Владелец согласовал перенос семейных данных на
> Vostro («это наша корпоративная сеть»). **Фаза 1 закрыта в тот же день**: доступ для
> установки restic/таймера получен, шаги 3–9 выполнены, restic-репозиторий и ночной
> таймер работают, восстановление проверено реальным накатом (снэпшот `ab975984`, все
> `*.sql.gz` прошли `gzip -t`). Подробности — раздел «Сделано 2026-08-24» ниже. Следующий
> шаг — **фаза 2** (фото Immich, ~6 ГБ, отдельное решение) и L2-задача «запретить
> засыпание» на Vostro (общая с соседним проектом, ещё не сделана).

## Решение владельца / Owner's decision

🇷🇺 Off-site цель — **Vostro** (`192.168.75.153`, ~814 ГБ свободно, в другом здании).
Согласовано 2026-08-22.

🇬🇧 The off-site target is **Vostro** (`192.168.75.153`, ~814 GB free, in a different building).
Agreed on 2026-08-22.

🇷🇺 Я рекомендовал внешний диск и высказал оговорки; владелец выбрал Vostro.
Решение принято, оговорки остаются в силе как известные риски:

- машина стала **боевой** для соседнего проекта — бэкап делит с ним диск и ввод-вывод;
- **весь её трафик идёт в туннель Amnezia** — копия пойдёт туннель-в-туннель через VPS;
- это чужая сеть, и лишний повод трогать её настройки.

🇬🇧 I recommended an external drive and voiced reservations; the owner chose Vostro.
The decision has been made, and the reservations remain in force as known risks:

- the machine is **in production** for the neighboring project — the backup shares its disk and I/O with it;
- **all of its traffic goes through the Amnezia tunnel** — the copy will travel tunnel-through-tunnel via the VPS;
- it is someone else's network, and one more reason to touch its settings.

## Архитектура: Vostro забирает сам / Architecture: Vostro pulls it itself

🇷🇺 Ключевое ограничение — **оба узла за NAT и ни один не принимает входящие**.
Jetson за CGNAT, Vostro в корпоративной сети с исходящим доступом. Значит:

🇬🇧 The key constraint is that **both nodes are behind NAT and neither accepts inbound connections**.
The Jetson is behind CGNAT, Vostro is on a corporate network with outbound access only. Therefore:

```
Vostro ──исходящий SSH──> VPS 95.163.176.103:22
                            │
                            └─ ProxyJump ─> 127.0.0.1:10022 ─> Jetson
```

🇷🇺 `10022` на VPS — уже существующий обратный туннель Jetson, слушает **только
loopback**. Новых портов не требуется.

🇬🇧 `10022` on the VPS is the already-existing Jetson reverse tunnel, listening on
**loopback only**. No new ports are needed.

🇷🇺 **Направление выбрано не случайно:** инициирует Vostro, потому что только он
может. Побочная выгода — Jetson не хранит учётных данных для записи на Vostro;
компрометация Jetson не даёт доступа к off-site копии.

🇬🇧 **The direction was not chosen at random:** Vostro initiates because it is the
only one that can. A side benefit is that the Jetson holds no credentials for
writing to Vostro; compromising the Jetson does not grant access to the off-site copy.

🇷🇺 Схема работы: Vostro забирает дампы к себе, затем кладёт их в **локальный
restic-репозиторий** `/srv/nas-offsite`. Restic шифрует — посторонний на чужой
машине увидит непрозрачные блобы.

🇬🇧 How it works: Vostro pulls the dumps to itself, then stores them in a **local
restic repository** `/srv/nas-offsite`. Restic encrypts — an outsider on that
machine sees only opaque blobs.

## Сделано на 2026-08-12 / Done on 2026-08-12

| Шаг / Step | Статус / Status |
|---|---|
| Путь проверен: Vostro → VPS:22 доступен / Path verified: Vostro → VPS:22 reachable | ✅ |
| Порт `10022` на VPS живёт, loopback-only / Port `10022` on the VPS is alive, loopback-only | ✅ |
| Выделенный ключ на Vostro `~/.ssh/id_nas_offsite` / Dedicated key on Vostro `~/.ssh/id_nas_offsite` | ✅ создан / created |

## Сделано 2026-08-22 — шаги 1 и 2 закрыты / Done 2026-08-22 — steps 1 and 2 closed

🇷🇺 Обе авторизации выполнены с нашей стороны; Vostro для этого не требовался.

🇬🇧 Both authorizations were performed on our side; Vostro was not required for this.

| Шаг / Step | Где / Where | Что стоит / What is set | Проверено / Verified |
|---|---|---|---|
| 1 | VPS `/root/.ssh/authorized_keys` | `restrict,permitopen="127.0.0.1:10022"` — только проброс на туннель Jetson, ни шелла, ни pty, ни агента / `restrict,permitopen="127.0.0.1:10022"` — forwarding to the Jetson tunnel only, no shell, no pty, no agent | строк ключей 2 → 3, наш root-ключ на месте; бэкап `.bak.20260822` / key lines 2 → 3, our root key in place; backup `.bak.20260822` |
| 2 | Jetson `/home/admin/.ssh/authorized_keys` | `command="/usr/local/sbin/nasa-offsite-export.sh",restrict` — ключ приколот к одной команде на чтение / `command="/usr/local/sbin/nasa-offsite-export.sh",restrict` — the key is pinned to a single read command | бэкап `.bak.20260822`; свои три ключа не тронуты / backup `.bak.20260822`; the existing three keys untouched |
| 2а | Jetson `/usr/local/sbin/nasa-offsite-export.sh` | root:root 755, отдаёт `tar` дампов в stdout, запрос клиента игнорирует / root:root 755, streams a `tar` of the dumps to stdout, ignores client input | самопроверка: **158 126 080 байт** (~151 МБ) — совпадает с каталогом дампов / self-check: **158,126,080 bytes** (~151 MB) — matches the dump directory |

🇷🇺 **Свойство схемы, которое надо назвать вслух:** restic шифрует репозиторий *на Vostro*,
но по пути забора дампы приходят туда **открытым текстом**. Кто владеет Vostro — видит
их в этот момент. Владелец это принял (машина в корпоративной сети организации), но это
свойство, а не недосмотр, и оно должно быть известно.

🇬🇧 **A property of the scheme that must be stated out loud:** restic encrypts the repository
*on Vostro*, but along the way the dumps arrive there in **plain text**. Whoever controls
Vostro sees them at that moment. The owner accepted this (the machine is on the
organization's corporate network), but it is a property, not an oversight, and it needs
to be known.

🇷🇺 ✅ **Блокер снят 2026-08-24.** Разовый bootstrap выполнен: `work` поднял на Vostro
обратный туннель (`nas-offsite-tunnel.service`, ключ `id_ed25519_nas_offsite`,
генерировался прямо на Vostro — приватная часть машину не покидала) на порт **10222**
общего VPS, `restrict,port-forwarding`. Проверено по правилу №13 до/после: Amnezia не
перезапускались, наружу только 22/443/40568/udp, число пиров не уменьшилось; `ss -tlnp`
на VPS подтвердил `127.0.0.1:10222` слушает. Разбор — доска, сообщения m0063–m0071.

🇬🇧 ✅ **Blocker cleared on 2026-08-24.** A one-time bootstrap was performed: `work` set up
a reverse tunnel on Vostro (`nas-offsite-tunnel.service`, key `id_ed25519_nas_offsite`,
generated directly on Vostro — the private part never left the machine) on port **10222**
of the shared VPS, `restrict,port-forwarding`. Verified per rule #13 before/after: Amnezia
containers did not restart, only 22/443/40568/udp are exposed, peer count did not decrease;
`ss -tlnp` on the VPS confirmed `127.0.0.1:10222` is listening. Details — board messages
m0063–m0071.

🇷🇺 ⚠️ Уточнение: сам туннель даёт только **путь**, не **вход** — ключ `restrict,port-forwarding`
пускает исключительно проброс, попытка залогиниться через 10222 как `alexey` вернула
`Permission denied`. Для реальной установки restic и таймера запрошен (m0072, открыт)
отдельный несвязанный ключ `nas-vostro-admin-2026-08-24`, публичная часть в
`shared/nas/nas-vostro-admin.pub`, ждёт добавления в `authorized_keys` alexey на Vostro.

🇬🇧 ⚠️ Clarification: the tunnel itself only provides a **path**, not **entry** — the key
`restrict,port-forwarding` allows forwarding only, and an attempt to log in through 10222
as `alexey` returned `Permission denied`. To actually install restic and the timer, a
separate, unrelated key `nas-vostro-admin-2026-08-24` was requested (m0072, open); its
public part is in `shared/nas/nas-vostro-admin.pub`, awaiting addition to alexey's
`authorized_keys` on Vostro.

🇷🇺 ✅ **Проверено эмпирически 2026-08-24 (не по тексту ниже, а прямым замером обеих сторон):**
шаги 1 и 2 из раздела «Сделано 2026-08-22» — **оба закрыты и подтверждены живьём**, а не
только по табличке. VPS `authorized_keys` строка 3 — ключ `vostro-nas-offsite-backup-2026-08-12`
с `restrict,permitopen="127.0.0.1:10022"` на месте. Jetson `admin` `authorized_keys` строка
4 — тот же ключ, `command="/usr/local/sbin/nasa-offsite-export.sh",restrict`, скрипт на
месте и рабочий. Формулировка «ключ пока нигде не авторизован» ниже была **устаревшей**
(осталась от черновика 08-12, не вычищена при обновлении 08-22) — вычеркнута.

🇬🇧 ✅ **Verified empirically on 2026-08-24 (not from the text below, but by directly
measuring both sides):** steps 1 and 2 from the "Done on 2026-08-22" section — **both
closed and confirmed live**, not just on paper. VPS `authorized_keys` line 3 — key
`vostro-nas-offsite-backup-2026-08-12` with `restrict,permitopen="127.0.0.1:10022"` is
in place. Jetson `admin` `authorized_keys` line 4 — the same key,
`command="/usr/local/sbin/nasa-offsite-export.sh",restrict`, the script is in place and
working. The earlier statement "the key is not yet authorized anywhere" was **stale**
(left over from the 08-12 draft, not cleaned up during the 08-22 update) — struck out.

🇷🇺 Отпечаток ключа:

🇬🇧 Key fingerprint:

```
SHA256:MkeaAvXClglpAgEIPOV/Nh8mD7LG77uXFouw46CgCQE
vostro-nas-offsite-backup-2026-08-12
```

## Сделано 2026-08-24 — шаги 3–9 закрыты, фаза 1 в бою / Done 2026-08-24 — steps 3–9 closed, phase 1 in production

🇷🇺 1. ~~Авторизовать ключ на VPS~~ — **сделано 22.08, подтверждено 24.08**.

🇬🇧 1. ~~Authorize the key on the VPS~~ — **done 08-22, confirmed 08-24**.

🇷🇺 2. ~~Авторизовать тот же ключ на Jetson~~ — **сделано 22.08, подтверждено 24.08**.

🇬🇧 2. ~~Authorize the same key on the Jetson~~ — **done 08-22, confirmed 08-24**.

🇷🇺 3. ✅ **Сквозной путь проверен и почин**ен: ключ на VPS был авторизован 22.08
   **без флага `port-forwarding`** — `restrict,permitopen=...` без него не
   включает форвардинг вообще, только сужает уже включённый. Путь был прописан,
   но ни разу не пройден до сегодня. Поправлено на VPS (правило №13 пройдено
   до/после, `authorized_keys.bak.20260824` рядом), путь подтверждён численно:
   158 228 480 байт тар-потока дампов через `Vostro → VPS:10022 → Jetson`.

🇬🇧 3. ✅ **The end-to-end path was checked and fixed:** the key on the VPS had been
   authorized on 08-22 **without the `port-forwarding` flag** — `restrict,permitopen=...`
   without it does not enable forwarding at all, it only narrows forwarding that is
   already enabled. The path had been written down but never actually traversed until
   today. Fixed on the VPS (rule #13 passed before/after, `authorized_keys.bak.20260824`
   kept alongside), the path confirmed numerically: 158,228,480 bytes of a tar stream of
   dumps through `Vostro → VPS:10022 → Jetson`.

🇷🇺 4. ✅ **restic 0.16.4** установлен на Vostro (`apt-get install -y restic`).

🇬🇧 4. ✅ **restic 0.16.4** installed on Vostro (`apt-get install -y restic`).

🇷🇺 5. ✅ **Репозиторий создан**: `/srv/nas-offsite`, root:root 700, ID `0ae1f72d33`.
   Пароль — root-only `/root/.nas-offsite-restic-password` на Vostro; копия вне
   обеих машин передана владельцу через чат в момент создания — переложить в
   постоянное хранилище (менеджер паролей) на его стороне.

🇬🇧 5. ✅ **Repository created**: `/srv/nas-offsite`, root:root 700, ID `0ae1f72d33`.
   Password — root-only `/root/.nas-offsite-restic-password` on Vostro; a copy outside
   both machines was handed to the owner via chat at creation time — to be moved into
   permanent storage (a password manager) on his side.

🇷🇺 6. ✅ **Начато с малого**: фаза 1 = только дампы БД. Фото Immich — отдельным
   решением позже (согласовано в m0068), сейчас не трогаем.

🇬🇧 6. ✅ **Started small**: phase 1 = database dumps only. Immich photos — a separate
   decision later (agreed in m0068), not touched now.

🇷🇺 7. ✅ **Таймер на Vostro**: `nas-offsite-backup.timer`, ночью в 04:00 MSK
   (после бэкапа Jetson в 03:05, с запасом), `nas-offsite-backup.service` —
   `IOSchedulingClass=idle`, `CPUSchedulingPolicy=idle`, `Nice=19`,
   `MemoryMax=512M`. `earlyoom --avoid` на Vostro дополнен `restic|nas-offsite-backup`.
   Юниты и скрипт — `systemd/nas-offsite-backup.{service,timer}`,
   `scripts/setup/nas-offsite-backup.sh` в этом репозитории.

🇬🇧 7. ✅ **Timer on Vostro**: `nas-offsite-backup.timer`, nightly at 04:00 MSK
   (after the Jetson backup at 03:05, with margin), `nas-offsite-backup.service` —
   `IOSchedulingClass=idle`, `CPUSchedulingPolicy=idle`, `Nice=19`,
   `MemoryMax=512M`. `earlyoom --avoid` on Vostro extended with `restic|nas-offsite-backup`.
   Units and script — `systemd/nas-offsite-backup.{service,timer}`,
   `scripts/setup/nas-offsite-backup.sh` in this repository.

🇷🇺 8. ✅ **Восстановление проверено** 24.08 11:02–11:03 MSK: снэпшот `ab975984`,
   14 файлов, 150.885 MiB (114.45 MiB после сжатия restic). `restic check` —
   без ошибок. `restic restore latest` во временный каталог, все 14 `*.sql.gz`
   прошли `gzip -t`, размер восстановленного совпал с исходным. Таймер включён
   и активен (`systemctl is-enabled/is-active` → enabled/active), следующий
   прогон — по расписанию, ручной проверочный уже состоялся.

🇬🇧 8. ✅ **Restore verified** on 08-24 11:02–11:03 MSK: snapshot `ab975984`,
   14 files, 150.885 MiB (114.45 MiB after restic compression). `restic check` —
   no errors. `restic restore latest` into a temporary directory, all 14 `*.sql.gz`
   files passed `gzip -t`, the restored size matched the original. The timer is
   enabled and active (`systemctl is-enabled/is-active` → enabled/active), the next
   run is on schedule, a manual verification run has already taken place.

🇷🇺 9. ✅ **HOST_CONTRACT.md на Vostro дополнен** своей секцией (было 1127 строк /
   16 разделов, стало 1177 / 17 — только дописано, не переписано), доска
   уведомлена.

🇬🇧 9. ✅ **HOST_CONTRACT.md on Vostro was extended** with its own section (was 1127
   lines / 16 sections, became 1177 / 17 — only appended, not rewritten), the board
   was notified.

🇷🇺 **Доступ для администрирования:** отдельный ключ `nas-vostro-admin-2026-08-24`
(без ограничений, решение владельца через доску m0072) даёт полный вход
`alexey@` через тот же туннель (порт 10222). Приватная часть создана и живёт
только на рабочей машине nas-проекта.

🇬🇧 **Administrative access:** a separate key `nas-vostro-admin-2026-08-24`
(unrestricted, owner's decision via board message m0072) grants full `alexey@`
login through the same tunnel (port 10222). The private part was created and
lives only on the working machine of the nas project.

🇷🇺 **Пароль restic-репозитория** — root-only на Vostro, копия вне обеих машин
лежит в Windows Credential Manager рабочей станции (`cmdkey`, цель
`NAS_Jetson_Nano-restic-offsite-vostro`) — не только в истории чата.

🇬🇧 **The restic repository password** is root-only on Vostro; a copy outside both
machines lives in the workstation's Windows Credential Manager (`cmdkey`, target
`NAS_Jetson_Nano-restic-offsite-vostro`) — not only in chat history.

## Алерт о забое канала (добавлено 24.08.2026) / Channel-stall alert (added 2026-08-24)

🇷🇺 Одностороннее доверие Vostro→Jetson (Jetson не может проверить, что делает
Vostro) намеренно не нарушено ради алерта. Вместо этого **Jetson сам
свидетельствует о своей половине**: forced-command экспортёр
(`/usr/local/sbin/nasa-offsite-export.sh` на устройстве,
`scripts/setup/nasa-offsite-export.sh` в git) при каждой успешной раздаче
дампов обновляет `/mnt/storage/backups/offsite-pull-last.stamp` — файл
пишет `admin`, читает `root` (существующий Phase E алерт `nasa-talk-alert.py`,
таймер каждые 15 мин). Новая проверка `check_offsite_pull()`: тревога, если
штамп старше 30 ч. Не подтверждает успех `restic` на Vostro — только то, что
Jetson этой ночью кому-то отдал дампы; ровно тот класс отказа, что стрелял
22–24.08 (путь без `port-forwarding`).

🇬🇧 The one-way trust Vostro→Jetson (the Jetson cannot verify what Vostro does)
was deliberately not broken for the sake of this alert. Instead, **the Jetson
testifies to its own half**: the forced-command exporter
(`/usr/local/sbin/nasa-offsite-export.sh` on the device,
`scripts/setup/nasa-offsite-export.sh` in git) updates
`/mnt/storage/backups/offsite-pull-last.stamp` on every successful dump handout
— the file is written by `admin`, read by `root` (the existing Phase E alert
`nasa-talk-alert.py`, timer every 15 min). The new check `check_offsite_pull()`:
alarms if the stamp is older than 30 h. It does not confirm that `restic` on
Vostro succeeded — only that the Jetson handed dumps to someone that night;
exactly the class of failure that hit on 08-22–08-24 (the path missing
`port-forwarding`).

🇷🇺 Оба файла на Jetson изменены на устройстве с бэкапами
(`*.bak.20260824` рядом), синтаксис проверен (`py_compile`, `bash -n`) до
установки, регрессия проверена реальным прогоном с Vostro (снэпшот
`21501345`, штамп обновился сам). Тестовое сообщение дошло в комнату
владельца (`nx4ud9c6`), не в общий чат.

🇬🇧 Both files on the Jetson were changed on the device with backups
(`*.bak.20260824` kept alongside), syntax was checked (`py_compile`, `bash -n`)
before installation, regression was verified with a real run from Vostro
(snapshot `21501345`, the stamp updated on its own). The test message arrived
in the owner's room (`nx4ud9c6`), not in the shared chat.

## Отложено отдельным решением / Deferred to a separate decision

🇷🇺 **Фаза 2** (фотографии Immich, ~6 ГБ разово, дальше приросты) — не сейчас,
отдельным запросом на доску, когда будем готовы (условие m0068: не молчаливое
расширение фазы 1).

🇬🇧 **Phase 2** (Immich photos, ~6 GB once, incremental after that) — not now,
a separate request on the board when we are ready (condition m0068: not a
silent expansion of phase 1).

🇷🇺 **Фаза E** (алерты в семейный чат) — транспорт готов и проверен
(`POST /v1/talk/notify` работает), нужен только вызов из скриптов мониторинга.
Отложено владельцем 2026-08-12, напоминаний не требует.

🇬🇧 **Phase E** (alerts into the family chat) — the transport is ready and tested
(`POST /v1/talk/notify` works), only a call from monitoring scripts is needed.
Deferred by the owner on 2026-08-12, needs no reminders.
