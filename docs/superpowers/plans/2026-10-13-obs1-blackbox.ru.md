# OBS-1 «чёрный ящик» — план реализации

> **Исполнение:** актуальные правила делегирования и классификации данных —
> в `AGENTS.md` и инструкциях владельца. Исходные план и спецификация содержат
> реальные сведения о хосте; внешним моделям они целиком не передаются.
> DeepSeek получает только отдельно подготовленный контракт `public`/`project-own`
> без закрытых данных и автоматической загрузки смешанного репозитория.
> Старые назначения исполнителей ниже сохраняют историю плана; финальное ревью,
> безопасность и принятие результата остаются у ведущего. Секреты — никому.

**Состояние 22.10.2026:** задачи 1–13 интегрированы в `621c21f`, исправления
живой приёмки — в `2f4edaa`. Установлены и сверены 39 runtime-файлов.
32 проверки на Python 3.6.9 / SQLite 3.22 прошли; час 21.10 14:11:59–15:11:59 UTC
принят: CPU 2,604%, VmHWM 20,875 МиБ, 3491 fast / 59 minute / 82 process snapshots.
**Обновление задачи 14, 22.10:** двухчасовая приёмка после `b21b81c` завершилась
`accepted=true` / success: 121 замер / 7200,053 с, CPU 2,5665%, VmHWM peak
22,3008 МиБ, cgroup peak 35,9883 МиБ, heartbeat max 11 с, рестартов 0. Дельты
`write_bytes` процесса +59 826 176 Б и раздела SSD +181 403 648 Б относятся только
к двум часам; счётчик раздела включает других писателей. Суточный бюджет ≤60 МБ
не подтверждён, экстраполяции нет. Исторический ночной пик 43,89 МиБ / 64 МиБ
относится к состоянию до правки. Отдельный 24-часовой observer идёт до 23.10
около 08:48 UTC; переход через полночь ещё не проверен.

**Цель:** на Jetson работает «чёрный ящик» — сборщик на SSD, снимок при загрузке, недельный архив на HDD и команда
`nas-why`, которая по собранному восстанавливает причину нештатной ситуации.

**Архитектура:** пакет `services/blackbox/blackbox/` из небольших модулей с чистыми функциями (источники →
хранилище → правила); три тонкие точки входа в `scripts/monitoring/`; три юнита systemd и таймер. Все пути к
`/sys`, `/proc`, `/dev`, сокету Docker и каталогам — параметры, поэтому всё проверяется на подставных деревьях.

**Технологии:** Python 3.6.9 (только стандартная библиотека: `sqlite3`, `json`, `gzip`, `lzma`, `tarfile`,
`hashlib`, `socket`, `http.client`, `threading`, `subprocess`), SQLite 3.22, systemd 237, pytest (только на станции).

**Спецификация:** [`docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md`](../specs/2026-10-13-blackbox-forensics-design.ru.md)
— канон для ведущего и нативного ревью; внешнему исполнителю — только контракт public/project-own без закрытых данных.

## Общие ограничения (из спецификации, дословно по значениям)

- Хостовой код — Python 3.6: без f-строк с `=`, без `dataclasses`, без `:=`, без `asyncio.run`; `vermin` в воротах.
- Новые функции — **≤ 40 строк и цикломатическая сложность ≤ 10** (храповик R3).
- Юниты — правила systemd 237 (`tests/unit/test_systemd237_units.py`): не `oneshot` вместе с `Restart=`, `StartLimit*` — в `[Unit]`.
- Пути хоста — из `nas_layout.resolve()` / `/etc/nas-layout.env`, никаких литеральных `/home/admin` (SD-2).
- Пути «чёрного ящика»: SSD `/mnt/storage/blackbox`, запасной `/var/lib/nas-blackbox/fallback` (≤ 20 МБ),
  HDD `/mnt/hdd2tb/backups/blackbox/<ГГГГ>/`.
- Частоты: fast 1 с; procs 60 с, при аномалии 10 с; heartbeat 10 с; logs 60 с; journal 5 мин; probes 60 с; rollup 60 с; guard 60 мин.
- Аномалия: есть D-state, или `MemAvailable` < 300 МБ, или `load1` > 6, или подкачка растёт > 50 МБ/мин.
- Пороги вердиктов: вход 5 В < 4 750 мВ; `MemAvailable` < 150 МБ; ноль операций диска ≥ 60 с.
- Предел «горячего» на SSD — 1 ГБ (удалять сначала `metrics.db`, затем `procs.db`; журналы и события — никогда).
- Архив: ISO-неделя, последний день которой старше 7 суток; воскресенье 05:30 UTC + ежедневный повтор; HDD — 365 дней.
- Сутки — по UTC; время в базах — целые секунды эпохи UTC.
- Бюджет: RSS ≤ 40 МБ (предел юнита 64 МБ), CPU ≤ 5 % в среднем (предел 10 %).
- Никогда не сохранять: `.env`, вывод `docker inspect`, тела HTTP. Маскирование — раздел 4.3 спецификации.
- К `/mnt/hdd2tb` сборщик не обращается в своём процессе — только `timeout 5 stat -f` в дочернем, один одновременно.

## Фокус ревью (что тестами задач не покрыто напрямую и чаще всего ломается у живого человека)

1. **Зависший `ntfs-3g` во время работы сборщика** — ни один цикл не должен встать: проба монтирования одна, с
   таймаутом, следующая не стартует, пока висит прошлая. → тест в задаче 5 (`test_mount_probe_single_flight`).
2. **SSD отвалился посреди работы** (не только «не было при загрузке») — запись в базы падает с `OSError`; сборщик
   переключается на запасной каталог, не умирает. → тест в задаче 7 (`test_collector_switches_to_fallback_on_oserror`).
3. **Часы прыгнули** (нет RTC-батарейки, NTP поправил время после загрузки на годы назад/вперёд) — день вычисляется
   по времени замера; запись «из 1970 года» не должна создавать каталог `1970-01-01` в «горячем». → тест в задаче 3
   (`test_day_for_ts_rejects_pre_2020`).
4. **Ротация журнала контейнера между двумя дочитываниями** (файл заменён, inode другой, новый файл короче) —
   сбросить курсор при новом inode и не дублировать прочитанное; намеренно
   пропущенный backlog/oversized-записи учитывать явными маркерами и байтами.
   → тест в задаче 4 (`test_tailer_rotation_new_inode`).
5. **`nas-why` за период, которого уже нет нигде** (старше года или архив повреждён) — ответ «неизвестно: данных
   нет за …», а не исключение. → тест в задаче 11 (`test_why_window_without_data`).

---

## Структура файлов

| Файл | Ответственность |
|---|---|
| `services/blackbox/blackbox/__init__.py` | версия пакета |
| `services/blackbox/blackbox/config.py` | `Config`, `load_config()` — значения по умолчанию, пороги, пути из раскладки |
| `services/blackbox/blackbox/redact.py` | маскирование секретов и русского текста семьи |
| `services/blackbox/blackbox/sources/sysfs.py` | питание, температуры, CPU, память, нагрузка, диски, сеть (чтение) |
| `services/blackbox/blackbox/sources/procs.py` | снимок процессов, признак аномалии |
| `services/blackbox/blackbox/sources/docker_api.py` | клиент сокета Docker: контейнеры, поток событий |
| `services/blackbox/blackbox/sources/container_logs.py` | дочитывание `json-file` с ротацией, счётчик проверок здоровья |
| `services/blackbox/blackbox/sources/journal.py` | порция журнала systemd по курсору |
| `services/blackbox/blackbox/sources/probes.py` | пробы сети и монтирований |
| `services/blackbox/blackbox/store.py` | SQLite-схемы, `DayStore`, `Catalog`, heartbeat, gzip-дописывание, закрытие дня |
| `services/blackbox/blackbox/collector.py` | расписание циклов, переключение на запасной каталог, предохранитель SSD |
| `services/blackbox/blackbox/bootsnap.py` | снимок загрузки и вердикт прошлой загрузки |
| `services/blackbox/blackbox/archive.py` | недельный архив на HDD |
| `services/blackbox/blackbox/why/evidence.py` | сбор доказательств за окно (SSD, каталог, архив HDD) |
| `services/blackbox/blackbox/why/rules.py` | правила вердиктов (чистые функции) |
| `services/blackbox/blackbox/why/cli.py` | `nas-why`: аргументы, вывод, `--short` |
| `scripts/monitoring/nas_jetson_nano-blackbox.py` | точка входа сборщика |
| `scripts/monitoring/nas_jetson_nano-blackbox-boot.py` | точка входа снимка загрузки |
| `scripts/monitoring/nas_jetson_nano-blackbox-archive.py` | точка входа архиватора |
| `scripts/monitoring/nas-why` | точка входа `nas-why` |
| `systemd/nas_jetson_nano-blackbox.service`, `…-blackbox-boot.service`, `…-blackbox-archive.service`, `…-blackbox-archive.timer` | юниты |
| `scripts/monitoring/install_blackbox.sh` | установка на хост (копии юнитов, каталоги, `daemon-reload`) |
| `tests/blackbox/conftest.py` + `tests/blackbox/test_*.py` | тесты; `conftest.py` добавляет `services/blackbox` в `sys.path` (как `tests/watchdog/conftest.py`) |
| `docs/plans/DEPLOY_OBS1_BLACKBOX.ru.md` (+ `.md`) | runbook выката и отката |
| изменить: `scripts/monitoring/nas_jetson_nano-boot-alert.py`, `…-container-watchdog.py`, `scripts/quality/preflight.sh` | интеграция (задачи 12–13) |

Точки входа — тонкие: найти пакет (`services/blackbox` рядом с репозиторием через `nas_layout`, либо
`/usr/local/lib/nas_jetson_nano/blackbox`), вызвать `main()` модуля. Вся логика — в пакете.

## Контракты данных (общие для всех задач)

```python
# sample — dict секундного замера (ключи ровно такие; отсутствующее значение — None)
{"ts": 1791861274, "vin_mv": 5080, "vin_ma": 1450, "cpu_mw": 1200, "gpu_mw": 40,
 "t_cpu": 630, "t_gpu": 605, "t_pmic": 500, "t_ao": 645,          # десятые °C
 "cpu_pct": 37.5, "freq_mhz": 1479, "mem_avail_mb": 1327, "swap_mb": 272, "zram_mb": 455,
 "load1": 1.76, "net_rx": 123456789, "net_tx": 98765432}
# disk_sample — кортеж (ts, disk_id, rios, wios, rsect, wsect, busy_ms); disk_id — имя из /dev/disk/by-id (usb-…)
# proc row — dict {"ts","pid","comm","owner","cmd","state","wchan","cpu_pct","rss_mb"}; owner — имя контейнера или "host"
# event — dict {"ts","source","kind","subject","severity","detail"}; severity ∈ {"info","warn","crit"}; detail — dict (в БД JSON)
#   source ∈ {"docker","probe","kernel","archiver","guard","boot","collector"}
# boot row — dict {"boot_id","start","end","clean","last_heartbeat","reset_source","pstore","verdict","confidence"}
# verdict — dict {"cls","verdict","confidence","evidence"}; confidence ∈ {"fact","probable","unknown"};
#   evidence — список (ts, source, text)
```

---

### Задача 1: каркас пакета, `config`, `redact`

**Файлы:** создать `services/blackbox/blackbox/__init__.py`, `config.py`, `redact.py`, `sources/__init__.py`,
`why/__init__.py`; тесты `tests/blackbox/conftest.py`, `tests/blackbox/test_config.py`, `tests/blackbox/test_redact.py`.

**Интерфейсы (производит):**
- `class Config(object)` с атрибутами по разделу «Общие ограничения»: `ssd_root`, `fallback_root`, `hdd_archive_root`,
  `ssd_mount="/mnt/storage"`, `hdd_mount="/mnt/hdd2tb"`, `sysfs_root="/sys"`, `proc_root="/proc"`, `dev_root="/dev"`,
  `docker_sock="/var/run/docker.sock"`, `docker_root="/var/lib/docker"`, `family_containers` (кортеж из трёх имён),
  `vin_low_mv=4750`, `mem_low_mb=300`, `mem_crit_mb=150`, `load_high=6.0`, `swap_growth_mb_min=50`, `disk_stall_s=60`,
  `hot_cap_bytes=1<<30`, `fallback_cap_bytes=20<<20`, `hot_min_days=7`, `hdd_retention_days=365`,
  `hdd_busy_units` (кортеж: `nas_jetson_nano-immich-hdd-copy.service`, `nas_jetson_nano-config-backup.service`, `nasa-backup.service`).
  `Config(**overrides)` — переопределение любого атрибута; неизвестный ключ → `TypeError`.
- `load_config(path=None, env=None) -> Config`: JSON-файл (по умолчанию `/etc/nas-blackbox.json`, отсутствует — значения
  по умолчанию), затем переменные `NAS_BLACKBOX_<АТРИБУТ>` из `env` (числа приводятся к типу умолчания).
- `mask_secrets(line: str) -> str`, `mask_family_text(line: str) -> str`, `redact_line(container: str, line: str, cfg) -> str`
  (секреты — всегда; русский текст — только если `container in cfg.family_containers`).

**Случаи для тестов (DeepSeek):**

| Функция | Вход | Ожидание |
|---|---|---|
| `load_config` | нет файла, пустое окружение | `hot_cap_bytes == 1073741824`, `vin_low_mv == 4750` |
| `load_config` | файл `{"vin_low_mv": 4700}` | `4700`; остальные — по умолчанию |
| `load_config` | env `NAS_BLACKBOX_MEM_LOW_MB=250` | `mem_low_mb == 250` (int) |
| `Config` | `Config(no_such=1)` | `TypeError` |
| `mask_secrets` | `GET /x?token=abc123def HTTP/1.1` | `token=<скрыто>` |
| `mask_secrets` | `Authorization: Bearer eyJhbGciOi...` | `Authorization: <скрыто>` |
| `mask_secrets` | `password=` + 9 любых символов + ` user=admin` (в тесте собирать конкатенацией, чтобы сканер секретов не ловил литерал) | `password=<скрыто> user=admin` |
| `mask_secrets` | `x-api-key: k_ABCDEF0123456789` | `x-api-key: <скрыто>` |
| `mask_secrets` | `id_token":"eyJ..."` | значение после `id_token` скрыто (грабли проекта 20.09) |
| `mask_secrets` | `GET /healthcheck HTTP/1.1 200` | без изменений |
| `mask_family_text` | `stt INFO распознано за 1.2 с: мама купи хлеба пожалуйста` | `… <текст скрыт>` (≥ 3 русских слов подряд) |
| `mask_family_text` | `ошибка: диск` | без изменений (2 слова) |
| `redact_line` | `homecloud_nextcloud`, русская фраза из 4 слов | русский текст сохранён |
| `redact_line` | `homecloud_stt`, та же фраза | `<текст скрыт>` |

- [ ] **Шаг 1.** DeepSeek: карточка с таблицей выше → `tests/blackbox/conftest.py`, `test_config.py`, `test_redact.py`.
- [ ] **Шаг 2.** `python -m pytest -q tests/blackbox/test_config.py tests/blackbox/test_redact.py` → падают (`ModuleNotFoundError`).
- [ ] **Шаг 3.** Sonnet: реализация `config.py`, `redact.py` (регулярные выражения секретов — по образцам `scripts/security/check_no_secrets.sh`).
- [ ] **Шаг 4.** Тесты зелёные; `vermin -t=3.6 services/blackbox` без замечаний.
- [ ] **Шаг 5.** Коммит `feat(obs1): blackbox package skeleton, config, redaction`.

### Задача 2: чтение `sysfs`/`proc` (`sources/sysfs.py`)

**Интерфейсы (производит):**
- `read_power(sysfs_root) -> dict` — `{"vin_mv","vin_ma","cpu_mw","gpu_mw"}`; каналы по `rail_name_N`
  (`POM_5V_IN` → `vin_*`, `POM_5V_CPU` → `cpu_mw`, `POM_5V_GPU` → `gpu_mw`); ищет `bus/i2c/drivers/ina3221x/*/iio:device*`;
  нет датчика или `PermissionError` → все значения `None`.
- `read_thermal(sysfs_root) -> dict` — `{"t_cpu","t_gpu","t_pmic","t_ao"}` из `class/thermal/thermal_zone*/{type,temp}`
  (`CPU-therm`, `GPU-therm`, `PMIC-Die`, `AO-therm`), миллиградусы → десятые доли.
- `read_cpu_times(proc_root) -> tuple` (total, idle) из первой строки `/proc/stat`; `cpu_pct(prev, cur) -> float|None`.
- `read_freq_mhz(sysfs_root) -> int|None` (максимум по `cpu*/cpufreq/scaling_cur_freq`).
- `read_mem(proc_root) -> dict` `{"mem_avail_mb","swap_mb"}`; `read_zram_mb(sysfs_root) -> int|None` (сумма `block/zram*/mm_stat` поле 1).
- `read_load1(proc_root) -> float`; `read_net(proc_root, ifaces=("eth0",)) -> dict` `{"net_rx","net_tx"}`.
- `disk_id_map(dev_root) -> dict` `{"sda": "usb-…", …}` по ссылкам `disk/by-id` (без `-part`), только `usb-`/`ata-`;
  `read_disks(proc_root, idmap, ts) -> list` кортежей `disk_sample` только для дисков из `idmap`.
- `read_fast_sample(cfg, prev_cpu, ts) -> (sample, disk_samples, cur_cpu)` — собирает всё выше.

**Случаи для тестов (подставные деревья в `tmp_path`):**

| Случай | Ожидание |
|---|---|
| INA3221 с тремя каналами `POM_5V_IN/GPU/CPU`, значения 5080/1450/7368 | `vin_mv=5080`, `vin_ma=1450`, `gpu_mw`, `cpu_mw` по именам, не по номерам (перемешать порядок каналов) |
| Нет каталога `ina3221x` | все четыре `None`, без исключения |
| Файл `in_voltage0_input` недоступен (`chmod 000`; на Windows — подменить `open`, бросающий `PermissionError`) | `None` |
| Терм-зоны `CPU-therm=63000`, `GPU-therm=60500` | `t_cpu=630`, `t_gpu=605` |
| `cpu_pct((1000, 800), (1100, 850))` | `50.0`; при `prev=None` → `None` |
| `/proc/meminfo` с `MemAvailable: 1359456 kB`, `SwapTotal 2029560`, `SwapFree 1750000` | `mem_avail_mb=1327`, `swap_mb=273` |
| `disk/by-id`: `usb-JMicron_…-0:0 → ../../sdb`, `…-part1 → ../../sdb1` | `{"sdb": "usb-JMicron_…-0:0"}` |
| `/proc/diskstats` со строками `sda`, `sda1`, `sdb`, `mmcblk0` и `idmap` только для `sda`,`sdb` | ровно 2 кортежа, поля по индексам 3, 7, 5, 9, 12 |
| `read_fast_sample` на полном подставном дереве | все ключи контракта `sample` присутствуют |

- [ ] Шаг 1 DeepSeek: тесты `tests/blackbox/test_sysfs.py` · Шаг 2 падают · Шаг 3 Sonnet: `sources/sysfs.py` ·
  Шаг 4 зелёные + `vermin` · Шаг 5 коммит `feat(obs1): sysfs/proc readers keyed by disk id`.

### Задача 3: хранилище (`store.py`)

**Интерфейсы (производит):**
- `day_for_ts(ts) -> str` — `"ГГГГ-ММ-ДД"` по UTC; `ts` < 1577836800 (2020-01-01) → `ValueError`.
- `class DayStore(object)`: `__init__(self, hot_root, day)`; `add_samples(list)`, `add_disk_samples(list)`, `add_procs(list)`
  (накопление в памяти); `flush()` (одна транзакция на файл, `PRAGMA journal_mode=WAL`); `samples(since, until)`,
  `disk_samples(since, until)`, `procs(since, until)` → списки; `close()`. Файлы: `<hot>/<day>/metrics.db`, `procs.db`.
- `class Catalog(object)`: `__init__(self, path)`; `add_events(list)`, `add_minute(dict)`, `upsert_boot(dict)`, `get_boot(boot_id)`,
  `boots(limit=20)` (новые первыми), `events(since, until, source=None, subject=None)`, `minutes(since, until)`,
  `get_cursor(name)`, `set_cursor(name, value)`, `add_archive(dict)`, `archives()`, `archive_for_day(day) -> dict|None`.
- `write_heartbeat(path, boot_id, ts, power)` — временный файл + `fsync` + `os.replace` + `fsync` каталога;
  `read_heartbeat(path) -> dict|None` (повреждённый/пустой → `None`).
- `append_gz_lines(path, lines)` — новый gzip-блок в конец файла (конкатенация блоков читается `gzip.open`).
- `close_day(hot_root, day)` — `journal.log` → `journal.log.xz` (через временный файл), исходник удалить.
- `hot_size_bytes(hot_root) -> int`; `prune_hot(hot_root, cap_bytes, keep_days) -> list` удалённых путей
  (сначала самые старые `metrics.db`, затем `procs.db`; `containers/`, `journal.log*` — никогда; сегодняшний день — никогда).

**Случаи для тестов:**

| Случай | Ожидание |
|---|---|
| `day_for_ts(1791861274)` | `"2026-10-13"` |
| `day_for_ts(5)` | `ValueError` (фокус ревью №3) |
| `DayStore`: 3 замера, `flush`, новый объект на том же дне | `samples(…)` возвращает 3 в порядке `ts` |
| Два `flush` подряд с одинаковым `ts` | вторая запись заменяет (PK по `ts`), без исключения |
| `Catalog.events` с фильтром `source="docker"` | только события Docker; `detail` вернулся `dict` |
| `upsert_boot` дважды с одним `boot_id` | одна строка, поля обновлены |
| `get_cursor` неизвестного имени | `None` |
| `write_heartbeat` → `read_heartbeat` | тот же `boot_id`, `ts`; файл после записи цел (нет `.tmp`) |
| `read_heartbeat` на пустом файле | `None` |
| `append_gz_lines` дважды по 2 строки | `gzip.open(...).read()` даёт 4 строки по порядку |
| `close_day` | есть `journal.log.xz`, нет `journal.log`, содержимое совпадает |
| `prune_hot`: 9 дней × (`metrics.db` 200 КБ, `procs.db` 50 КБ, `containers/x.log.gz` 10 КБ), предел 1 МБ | удалены самые старые `metrics.db`, потом `procs.db`; ни одного `containers/`; сегодняшний день цел; итог ≤ предела или удалять больше нечего |

- [ ] Шаги 1–5 как в задаче 1; коммит `feat(obs1): sqlite day stores, catalog, heartbeat, hot pruning`.

### Задача 4: Docker — сокет, события, журналы контейнеров

**Файлы:** `sources/docker_api.py`, `sources/container_logs.py`; тесты `test_docker_api.py`, `test_container_logs.py`.

**Интерфейсы (производит):**
- `class DockerClient(object)`: `__init__(self, sock_path, timeout=10)`; `containers() -> list` `[{"id","name","image","state"}]`
  (`GET /containers/json?all=1`, имя без `/`); `events(since_ts) -> генератор dict` (`GET /events?since=…`, поток
  JSON-объектов по строкам; разрыв соединения → генератор завершается, вызывающий переподключается).
  Транспорт подменяется: `DockerClient(sock_path, opener=callable)` для тестов.
- `event_from_docker(raw: dict) -> dict|None` — в контракт `event`: `die`/`oom`/`kill`/`stop`/`start`/`restart` и
  `health_status: unhealthy|healthy` (`kind` — действие, `subject` — имя контейнера, `detail` — `exitCode`, `signal`,
  образ; остальное → `None`). Severity: `oom` и `die` с кодом ≠ 0 и ≠ 143 → `crit`; `unhealthy`, `kill`, `die` 143 → `warn`.
- `class LogTailer(object)`: `__init__(self, state: dict)`; `read_new(name, path, max_bytes=4<<20) -> list` строк `log`
  из `json-file` (`{"log": "...", "stream": "...", "time": "..."}`); состояние `{name: {"inode", "offset"}}` хранит
  вызывающий (в `Catalog` через `set_cursor("logs", json)`). Новый inode → читать новый файл с 0; файл короче смещения
  (усечение) → с 0; неполная последняя строка — не потреблять до следующего раза.
- `split_health(lines) -> (kept_lines, health_count)` — строки доступа `GET /health`, `/healthcheck`, `/status.php` с кодом 200 → счётчик.
- `tail_lines(path, n=200) -> list` — последние `n` строк `log` файла `json-file` (для событий падения).

**Случаи для тестов:**

| Случай | Ожидание |
|---|---|
| `containers()` на ответе с `"Names": ["/homecloud_stt"]` | `name == "homecloud_stt"` |
| `events()`: поток из трёх JSON-строк и обрыв | три события, затем `StopIteration` |
| `event_from_docker` `die` с `exitCode=143` | `kind="die"`, `severity="warn"`, `detail["exitCode"]==143` |
| `event_from_docker` `oom` | `severity="crit"` |
| `event_from_docker` `health_status: unhealthy` | `kind="unhealthy"`, `severity="warn"` |
| `event_from_docker` `exec_start` | `None` |
| `LogTailer`: 3 строки, затем дописали 2 | второй вызов — ровно 2 |
| Неполная последняя строка (без `\n`) | не возвращается, пока не допишется |
| **Ротация: файл заменён (другой inode), новый короче** | возвращены строки нового файла с начала, без дублей (фокус ревью №4) |
| Усечение (тот же inode, размер < смещения) | чтение с 0 |
| `split_health` 4 строки `GET /healthcheck … 200` и 1 `POST /v1/chat` | `kept` = 1 строка, `health_count` = 4 |
| `tail_lines(n=2)` на 5 строках | 2 последние |

- [ ] Шаги 1–5; коммит `feat(obs1): docker socket events and json-file log tailer`.

### Задача 5: журнал systemd и пробы (`sources/journal.py`, `sources/probes.py`)

**Интерфейсы (производит):**
- `journal_since(cursor, run=subprocess_run) -> (lines, new_cursor)` — `journalctl --no-pager -o short-iso-precise
  --show-cursor` плюс `--after-cursor=<c>` (если курсор есть) или `--since=-5min`; последняя строка `-- cursor: …`
  отделяется; `run` подменяется в тестах (сигнатура как `subprocess.run`).
- `class MountProbe(object)`: `__init__(self, path, timeout_s=5, popen=subprocess.Popen)`; `poll(now) -> dict|None` —
  запускает `timeout 5 stat -f <path>` **только если предыдущий процесс завершён**; если предыдущий ещё жив дольше
  `timeout_s + 5` с — возвращает событие `{"kind": "mount_hung", "subject": path, "since": ts_start}` один раз; ответ
  вернулся с ошибкой → `mount_error`; после зависания пришёл ответ → `mount_recovered`.
- `probe_gateway(run)`, `probe_dns(name="api.telegram.org", timeout=3)`, `probe_tunnel(proc_root, vps_hosts)`
  (есть ли `ESTABLISHED` к одному из адресов VPS на 22-м порту в `/proc/net/tcp`), `probe_tcp(host, port, timeout=3)` →
  каждая `bool`; `probes_event(results: dict, prev: dict) -> list` событий только при **смене** состояния.

**Случаи для тестов:**

| Случай | Ожидание |
|---|---|
| `journal_since(None, run)` | команда содержит `--since=-5min`; курсор взят из последней строки |
| `journal_since("s=abc", run)` | команда содержит `--after-cursor=s=abc`; строк курсора в `lines` нет |
| **`MountProbe`: процесс не завершается** (подставной `Popen`, `poll()` всегда `None`) | за 10 вызовов запущен **ровно один** процесс; событие `mount_hung` ровно одно (фокус ревью №1) |
| `MountProbe`: процесс завершился с кодом 1 | событие `mount_error` |
| Зависание, затем процесс завершился с 0 | событие `mount_recovered` |
| `/proc/net/tcp` с `ESTABLISHED` (state `01`) на адрес VPS:22 в hex little-endian | `probe_tunnel` → `True` |
| `probes_event` без изменений | `[]` |
| `probes_event` `dns: True→False` | одно событие `warn` `dns_down` |

- [ ] Шаги 1–5; коммит `feat(obs1): journal cursor export, mount probe single-flight, network probes`.

### Задача 6: процессы (`sources/procs.py`)

**Интерфейсы (производит):**
- `read_procs(proc_root, container_of) -> list` сырых записей `{pid, comm, cmd, state, wchan, ticks, start, rss_mb, owner}`;
  `container_of(pid) -> str` (по `/proc/<pid>/cgroup`, `/docker/<64 hex>` → имя через карту id→имя; иначе `"host"`).
- `snapshot(prev_raw, cur_raw, dt_s, hz, ts, top_n=10) -> list` строк контракта `proc row`: топ-`top_n` по CPU ∪ топ-`top_n`
  по RSS ∪ **все** с `state == "D"`.
- `is_anomaly(sample, prev_sample, d_count, cfg) -> bool` — по правилу «Аномалия» из общих ограничений.

**Случаи для тестов:**

| Случай | Ожидание |
|---|---|
| Процесс исчез между снимками | не в выдаче, без исключения |
| PID переиспользован (другой `start`) | CPU считается от нуля, не отрицательный |
| 25 процессов, 3 в `D` вне топов | все 3 в выдаче, у них `wchan` заполнен |
| `cgroup` с `/docker/<id>` и картой | `owner` = имя контейнера |
| `is_anomaly`: `mem_avail_mb=280` | `True`; `load1=6.5` → `True`; подкачка +60 МБ за 60 с → `True`; спокойный → `False` |

- [ ] Шаги 1–5; коммит `feat(obs1): process snapshots with D-state and anomaly rule`.

### Задача 7: сборщик (`collector.py` + `scripts/monitoring/nas_jetson_nano-blackbox.py`)

**Потребляет:** всё из задач 1–6. **Производит:** `run(cfg, clock=time.time, sleep=time.sleep, sources=None, stop=None)`;
`class Collector` с методами `tick_fast(now)`, `tick_procs(now)`, `tick_heartbeat(now)`, `tick_logs(now)`,
`tick_journal(now)`, `tick_probes(now)`, `tick_rollup(now)`, `tick_guard(now)`; поток событий Docker — отдельный
`threading.Thread(daemon=True)` с переподключением (пауза 5 с), события кладёт в `queue.Queue`, основной цикл забирает.

**Поведение:**
- Основной цикл раз в секунду вызывает `tick_fast`; остальные — по своим интервалам (сравнение с временем последнего
  вызова); буферы сбрасываются в базы каждые 10 с (`flush`).
- Корень записи: `cfg.ssd_root`, если `ssd_mount` смонтирован (`os.path.ismount`) и запись удаётся; иначе
  `cfg.fallback_root` (в запасном режиме — только heartbeat раз в 60 с, минутные сводки и события; кольцо ≤ 20 МБ).
  **Любой `OSError` при записи → переход в запасной режим + событие `collector/ssd_write_failed`** (фокус ревью №2);
  раз в 60 с — попытка вернуться на SSD, при успехе перенос событий/сводок из запасного каталога в `catalog.db`.
- Смена суток (UTC) → `close_day` прошлого дня.
- На падение/OOM/unhealthy контейнера → событие с `detail["tail"]` = `redact_line` от `tail_lines(..., 200)`.
- Журналы контейнеров: `LogTailer.read_new` → `split_health` → `redact_line` → `append_gz_lines(<hot>/<day>/containers/<name>.log.gz)`;
  счётчики проверок здоровья — в минутную сводку.

**Случаи для тестов (подставные источники и часы):**

| Случай | Ожидание |
|---|---|
| 125 тиков по 1 с | 125 записей `sample`, 2 минутные сводки, 12 heartbeat, procs — 2 раза (нет аномалии) |
| Аномалия с 30-й секунды | procs каждые 10 с после неё |
| **`flush` бросает `OSError`** | сборщик жив, режим `fallback`, событие `ssd_write_failed`, heartbeat пишется в запасной каталог (фокус ревью №2) |
| SSD вернулся | режим `ssd`, события из запасного каталога в `catalog.db` |
| Переход через 00:00 UTC | `close_day` вызван для прошлого дня ровно раз |
| Событие `die` 137 с флагом OOM | в `catalog.events` есть `detail["tail"]`, маскирование применено |

- [ ] Шаги 1–5; коммит `feat(obs1): collector loops, fallback mode, docker event tails`.

### Задача 8: снимок загрузки (`bootsnap.py` + точка входа)

**Уточнение интеграции от 20.10.2026:** сохранённые строки журналов контейнера
получают UTC-префикс времени наблюдения с явной меткой `(observed)`, поскольку
источник возвращает поле Docker `log` без поля `time`, а приложение не обязано
писать собственный ISO timestamp. Исходное сообщение после маскирования
сохраняется полностью. Время наблюдения не выдаётся за точное время события.
Снимок после загрузки также записывает переход `boot` в каталог и ассоциацию
`boot-snapshot:<previous_id>` с текущим снимком; иначе `nas-why --boot -1`
не получил бы реальные записи для анализа. Сборщик запускается после boot-unit.

**Производит:** `take_snapshot(cfg, boot_id, run=subprocess_run, now=time.time) -> str` (путь каталога `boots/<boot_id>/`);
`previous_boot_summary(catalog, heartbeat, journal_prev_tail, pstore_files, reset_source) -> dict` (строка `boot`
для прошлой загрузки без вердикта; вердикт выставляет задача 10/11 через `why.rules.evaluate`).
Состав файлов — раздел 4.2 спецификации: `uname.txt`, `nv_tegra_release.txt`, `dmesg.txt`, `reset_source.txt`,
`lsblk.txt`, `by-id.txt`, `lsusb.txt`, `mounts.txt`, `pstore/` (копии), `prev_journal_tail.txt`, `docker_ps.txt`, `summary.json`.
**Запрещено:** `docker inspect`. Нет SSD → писать в `cfg.fallback_root/boots/`.

**Случаи для тестов:** каждая команда упала → файл с текстом ошибки, снимок всё равно создан; pstore пуст →
`summary.pstore == []`; pstore с `dmesg-ramoops-0` → копия и `summary.pstore == ["dmesg-ramoops-0"]`; SSD нет →
каталог в запасном корне; в списке выполненных команд нет `inspect`.

- [ ] Шаги 1–5; коммит `feat(obs1): boot snapshot with pstore copy`.

### Задача 9: недельный архив (`archive.py` + точка входа)

**Уточнение безопасности ведущего от 20.10.2026:** все обращения к HDD, включая
создание каталогов, rename, проверку хеша и retention, выполняет отдельный
worker-процесс. Основной supervisor не обращается к HDD и завершает ожидание
по deadline через poll без блокирующего wait/communicate после kill.
Если прежний worker остался жив (в том числе D-state), следующий запуск
откладывается; PID сверяется со временем запуска из proc, чтобы учесть reuse.
Перед записью worker подтверждает действительное монтирование HDD. Исходные
дни SSD удаляются только после проверки копии и фиксации её в каталоге;
при любой ошибке они сохраняются. Эти требования дополняют контракт `ship`
ниже: прямые файловые операции допустимы внутри изолированного worker,
а не в процессе, отвечающем за deadline. На боевом HDD это пока не запускалось.

**Производит:** `weeks_due(hot_root, today, min_age_days=7) -> list` ISO-недель (`"2026-W41"`), все дни которых старше
`min_age_days`; `hdd_busy(cfg, run) -> str|None` (имя активного юнита/процесса или `None`); `hdd_alive(cfg, run) -> bool`;
`build_archive(hot_root, week, staging) -> (path, sha256)`; `ship(path, sha, hdd_dir, run) -> bool`
(`timeout 1800 cp` во временное имя → `sync` → `os.rename` → `timeout 600 sha256sum` и сверка);
`archive_week(cfg, catalog, week, run) -> dict` (итог: `shipped`/`deferred`/`failed` + причина; дни удаляются **только**
при `shipped`); `prune_hdd(hdd_root, today, retention_days)`; `main()` — все недели к отправке по очереди.

**Случаи для тестов (временные каталоги вместо SSD/HDD, подставной `run`):**

| Случай | Ожидание |
|---|---|
| Дни 2026-10-01…10-13, `today=2026-10-13` | `["2026-W40"]` (W40 = 28.09–04.10, последний день ≤ 06.10); `W41` (05–11.10) и `W42` — не к отправке |
| `hdd_busy` → `nas_jetson_nano-immich-hdd-copy.service` | итог `deferred`, на HDD ничего, дни на SSD |
| `hdd_alive` → `False` | `deferred` |
| sha256 на HDD не совпал | `failed`, дни на SSD целы, событие `archiver/verify_failed` |
| Успех | архив в `<hdd>/2026/blackbox-2026-W40.tar.xz` + `.sha256`, дни удалены, запись в `catalog.archives()` |
| `prune_hdd`: архив за 2025-W30 при `today=2026-10-13` | удалён; архив 2026-W02 — на месте |

- [ ] Шаги 1–5; коммит `feat(obs1): weekly sha256-verified archive to the HDD`.

### Задача 10: правила вердиктов (`why/rules.py`)

**Производит:** `class Evidence(object)` с атрибутами `window=(since, until)`, `boot` (dict|None), `samples`, `disk_samples`,
`procs`, `events`, `journal` (список `(ts, text)`), `pstore` (список имён), `heartbeat` (dict|None), `snapshots` (список
`boot summary.json` — для сравнения «буква ↔ by-id»); функции `rule_unclean_boot`, `rule_container`, `rule_disk_hang`,
`rule_memory`, `rule_network`, `rule_thermal`, `rule_usb` — каждая `(ev, cfg) -> list[verdict]`; `evaluate(ev, cfg) -> list`
(все правила; пустое окно → один вердикт `{"cls": "data", "confidence": "unknown", "verdict": "данных нет за <окно>"}`).

**Случаи для тестов (синтетические хронологии, по одному на ветку раздела 6 спецификации):**

| Случай | Ожидание |
|---|---|
| `boot.clean=False`, `pstore=["dmesg-ramoops-0"]` | `unclean_boot`, `fact`, «паника ядра» |
| Нештатно; за 60 с до heartbeat `vin_mv` 5080→4610 | `probable`, «питание» |
| Нештатно; питание ровно 5080 до последней секунды | `probable`, «внезапное пропадание питания или аппаратный сброс», в тексте «различить нечем» |
| Нештатно; событие `boot/poweroff_command` перед концом | вердикт «штатное выключение командой» |
| Нештатно; рост D-state и `mem_avail_mb`=120 за минуту до конца | `probable`, «зависание, затем сброс» |
| `die` 143 + строка журнала сторожа OPS-1 «docker restart» в ±2 мин | `container`, «перезапущен сторожем OPS-1», `fact` |
| `die` 137 + флаг OOM | «убит по нехватке памяти», `fact` |
| `die` 1 без сторожа | «ошибка приложения (код 1)», приложен хвост журнала |
| 3 процесса D с `wchan=request_wait_answer`, диск HDD 0 операций 90 с, `mount_hung` | `disk_hang`, `probable` |
| `oom-kill` в журнале ядра | `memory`, `fact`, назван процесс |
| `dns_down` при живом шлюзе | `network`, «DNS» |
| Шлюз недоступен | `network`, «домашняя сеть/роутер» |
| `t_cpu` ≥ 950 и частота упала | `thermal`, `probable` |
| В снимке прошлой загрузки `sda=usb-WD…`, в текущей `sdb=usb-WD…` | `usb`, «буквы дисков поменялись», `fact` |
| Окно без данных | один вердикт `unknown` «данных нет» |

- [ ] Шаги 1–5; коммит `feat(obs1): verdict rules for nas-why`.

### Задача 11: сбор доказательств и `nas-why` (`why/evidence.py`, `why/cli.py`, `scripts/monitoring/nas-why`)

**Потребляет:** `store.Catalog`, `store.DayStore`, `archive.*` (имена архивов), `rules.evaluate`.
**Производит:** `collect(cfg, since, until, container=None) -> Evidence` (дни из «горячего»; дни из архива — распаковать
нужные файлы в `cfg.ssd_root/tmp/<pid>/`, удалить после; журнал — из `journal.log[.xz]` дней, а за текущие сутки —
`journalctl --since/--until`); `collect_boot(cfg, which=-1) -> Evidence`; `main(argv=None) -> int` с аргументами
`--boot N`, `--since`, `--until`, `--container`, `--short`; вывод: хронология (`ЧЧ:ММ:СС источник текст`) + вердикты;
`--short` — ≤ 6 строк: вердикт(ы), «последний признак жизни», питание перед ним.

**Случаи для тестов:**

| Случай | Ожидание |
|---|---|
| **Окно 2024 года (нет ни в «горячем», ни в каталоге архивов)** | код 0, вывод «неизвестно: данных нет за …» (фокус ревью №5) |
| Окно в архиве HDD (подложенный архив) | данные найдены; `tmp/<pid>` удалён после |
| Архив повреждён (обрезанный `.tar.xz`) | вердикт `unknown` с причиной «архив повреждён», без исключения |
| `--short` на нештатной загрузке | ≤ 6 строк, первая — вердикт |
| `--container homecloud_stt` | в хронологии только события и строки этого контейнера |

- [ ] Шаги 1–5; коммит `feat(obs1): nas-why evidence collection and CLI`.

### Задача 12: интеграция с D2 и OPS-1

**Изменить:** `scripts/monitoring/nas_jetson_nano-boot-alert.py` — в текст алерта добавить вывод
`nas-why --boot -1 --short` (подпроцесс, таймаут 60 с; ошибка/таймаут → прежний текст); убрать ссылку на `CLAUDE.md`
и вопрос «выключали сами?». `scripts/monitoring/nas_jetson_nano-container-watchdog.py` — проверка свежести
`<ssd_root>/heartbeat` (или запасного): старше 120 с при `systemctl is-active nas_jetson_nano-blackbox` = `active` →
алерт «чёрный ящик молчит» не чаще раза в час (состояние — рядом с существующим состоянием сторожа).

**Случаи для тестов** (дополнить существующие тесты этих скриптов): `nas-why` вернул текст → он в алерте; `nas-why`
упал → алерт с прежним текстом; heartbeat свежий → тишина; старый → один алерт, повтор через 30 мин — тишина, через 61 — снова.

- [ ] Шаги 1–5; коммит `feat(obs1): verdict in the D2 alert, blackbox heartbeat check in OPS-1`.

### Задача 13: юниты, установка, ворота, runbook

**Создать:** `systemd/nas_jetson_nano-blackbox.service` (`Type=simple`, `Restart=on-failure`, `RestartSec=10`,
`StartLimitBurst`/`StartLimitIntervalSec` в `[Unit]`, `EnvironmentFile=/etc/nas-layout.env`, `ExecStart=/usr/bin/python3
"${NAS_PROJECT_DIR}/scripts/monitoring/nas_jetson_nano-blackbox.py"`, `After=docker.service local-fs.target`,
`ProtectSystem=strict`, `ReadWritePaths=-/mnt/storage/blackbox /var/lib/nas-blackbox`, `ProtectHome=read-only`,
`NoNewPrivileges=yes`, `PrivateTmp=yes`, `MemoryLimit=64M`, `CPUQuota=10%`, `Nice=10`, `IOSchedulingClass=idle`);
`…-blackbox-boot.service` (`Type=oneshot`, без `Restart=`, `After=local-fs.target docker.service`, `Wants=mnt-storage.mount`);
`…-blackbox-archive.service` (`Type=oneshot`, `Nice=19`, `IOSchedulingClass=idle`, `TimeoutStartSec=3600`) и
`…-blackbox-archive.timer` (`OnCalendar=*-*-* 05:30:00 UTC`, `Persistent=true` — архиватор сам решает, есть ли долг).
`scripts/monitoring/install_blackbox.sh` (по образцу `install_container_watchdog.sh`: каталоги `0750 root:adm`,
копии юнитов, `systemd-analyze verify`, `daemon-reload`; **не** включает службы — это делает runbook).
Добавить `tests/blackbox` в список раздела 9 `scripts/quality/preflight.sh`.
`docs/plans/DEPLOY_OBS1_BLACKBOX.ru.md` (+ EN-пара — DeepSeek): шаги выката, проверка «работает новый код»
(`ActiveEnterTimestamp` против `stat`), приёмка — раздел 9 спецификации, откат — раздел 10.

**Проверка:** `python tests/unit/test_systemd237_units.py` зелёный на новых юнитах; полный `bash scripts/quality/preflight.sh` зелёный.

- [x] Шаги: юниты и скрипт (Sonnet) → тест юнитов → `preflight.sh` → runbook (DeepSeek по тексту ведущего) → коммит
  `feat(obs1): units, installer, gate wiring, deploy runbook`.

### Задача 14: выкат и приёмка (ведущий, разрешение sudo — 21.10)

- [x] Сохранены исходники, mode/uid/gid, Git HEAD/status, scoped diff, таймеры,
  состояния юнитов и прежние systemd/CLI. Раскладка и отдельное SSD-монтирование
  проверены; готовый пакет перенесён без Git pull/checkout поверх ручных правок.
- [x] Установка и доступ к трём каналам INA3221 проверены от root; boot snapshot
  успешен. Установленные юниты сверены с принятыми исходниками.
- [x] Включены collector и boot-service. Изолированная synthetic SSD→HDD приёмка
  (checksum, immutable conflict, отказ копирования) завершена **до** включения
  persistent archive timer. Плановая служба 22.10 завершилась успешно;
  следующий таймер — 23.10 05:30 UTC, создание недельного архива этим не доказано.
- [x] Час 21.10 14:11:59–15:11:59 UTC принят: fast 3491, minute 59, process snapshots 82.
  CPU 2,604%, VmHWM 20,875 МиБ, cgroup peak 28,0195 МиБ, heartbeat ≤11 с, рестартов 0.
- [x] Двухчасовая ресурсная приёмка после `b21b81c`: 121 замер / 7200,053 с,
  CPU 2,5665%, VmHWM 22,3008 МиБ, cgroup peak 35,9883 МиБ, heartbeat max 11 с,
  process snapshots росли, PID/restarts без изменений, `failcnt` delta 0.
- [ ] Суточный бюджет SSD ≤60 МБ/сутки: двухчасовые дельты его не подтверждают.
  24-часовой observer идёт до 23.10 около 08:48 UTC; итог/UTC-переход ожидаются.
  Более ранние показатели VmHWM/cgroup относятся к состоянию до `b21b81c`;
  двухчасовая приёмка после исправления завершена, а суточное наблюдение продолжается.
  Для повторной часовой проверки после исправлений: fast >3000, minute ≥55, отдельные process
  snapshots ≥55, CPU ≤5% в среднем, VmHWM ≤40 MiB, cgroup peak ≤64 MiB,
  heartbeat текущего boot ≤120 с, без смены PID/рестартов. Результат — после часа.
- [x] Stale heartbeat/cooldown и честный unknown проверены синтетически и через
  bounded CLI без отправки уведомлений. Исходники и данные сохранены для отката.
- [ ] Настоящие Docker die/oom/unhealthy, доставка новой секции D2 и связь двух
  реальных загрузок остаются непроверенными вживую; ради приёмки не перезапускать
  семейные контейнеры, не вызывать reboot или обрыв питания.
- [ ] Через неделю уточнить пороги по базовой линии и проверить суточный объём
  записи; приёмка настоящей нештатной загрузки — при первом таком событии.

---

## Порядок и параллельность

1 → (2, 3, 4, 5, 6 — параллельно; тесты DeepSeek для всех пяти — одной серией карточек) → 7, 8, 9, 10 (параллельно,
10 зависит только от контрактов) → 11 → 12 → 13 → 14.

## Самопроверка плана (ведущий, 13.10)

- Покрытие спецификации: 4.1 → задачи 2, 4, 5, 6, 7; 4.2 → 8; 4.3 → 1; 4.4 → 11; 4.5 → 12; 5.1–5.2 → 3; 5.3 → 9, 3 (`prune_hot`);
  5.4 → 7; 6 → 10; 7 → 13; 9 → все задачи + 14; 10 → 13, 14. Пробелов нет.
- Заглушек нет; имена между задачами сверены (`DayStore`, `Catalog`, `append_gz_lines`, `redact_line`, `tail_lines`,
  `evaluate`, `collect`).
- Фокус ревью: пять случаев, у каждого — тест в задаче-владельце.
