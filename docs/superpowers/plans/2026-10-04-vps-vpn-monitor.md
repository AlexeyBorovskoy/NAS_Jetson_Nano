# Учёт нагрузки VPS и трафика пользователей VPN — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Цель:** раз в минуту снимать на VPS счётчики пиров AmneziaWG и метрики хоста (только чтение) и раз в сутки в 10:00 МСК присылать владельцу сводку в Telegram.

**Архитектура:** четыре модуля на стандартной библиотеке Python: разбор сырых данных, хранение и учёт в SQLite, выборки для отчёта, текст отчёта. Плюс два скрипта: `collect.py` под таймером раз в минуту и `report.py` под таймером в 10:00 МСК. Ставятся в `/usr/local/lib/nasa-vpnmon/` установщиком без пакетов и портов.

**Стек:** Python 3.12 на VPS (тесты: 3.11 на Windows и Linux), `sqlite3`, `urllib`, systemd; pytest — только в тестах.

**Спецификация:** `docs/superpowers/specs/2026-10-04-vps-vpn-monitor-design.ru.md` (EN — `…-design.md`). Исполнитель читает её вместе с планом.

## Общие ограничения

- Только стандартная библиотека. **`zoneinfo` не использовать:** на Windows у него нет базы поясов. МСК = `timezone(timedelta(hours=3), "MSK")`.
- Храповик метрик (`scripts/quality/code_metrics.py`): **у новой функции цикломатическая сложность ≤ 10 и длина ≤ 40 строк**, модуль ≤ 600 строк, параметров ≤ 5.
- Идентификаторы на английском, комментарии и строки для людей на русском, как в остальном репозитории.
- В `collect.py` нигде, включая комментарии, нет слов `dump`, `showconf` и `private`. `docker` вызывается только с `exec` и `inspect`. Это проверяется тестом.
- Пути на VPS: код — `/usr/local/lib/nasa-vpnmon/`; БД — `/var/lib/nasa-vpnmon/vpnmon.db` (каталог 0700, файл 0600); `/etc/nasa-vpnmon/names.conf` и `/etc/nasa-vpnmon/telegram.env` (0600).
- Юниты: `nasa-vpnmon-collect.{service,timer}` (раз в 60 с; `CPUQuota=20%`, `MemoryMax=64M`, `Nice=10`, `TimeoutStartSec=30`) и `nasa-vpnmon-report.{service,timer}` (`OnCalendar=*-*-* 10:00:00 Europe/Moscow`, `Persistent=true`, `TimeoutStartSec=300`).
- Новых портов, пакетов и пользователей нет. Amnezia, ufw, iptables, sshd и nginx не трогаются.
- В git не попадают настоящие ключи пиров, имена людей и токены: в тестах фиктивные ключи `"A" * 43 + "="` и имена «Клиент-А».
- Задачи 1–7 выполняются локально, без доступа к VPS и Jetson. Задача 8 — только ведущий и только после слова владельца «деплой».
- Тесты: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor` (Windows) или `python -m pytest -q tests/vpn_monitor`. Коммит запускает ворота `.githooks/pre-commit`. `--no-verify` запрещён. Последняя строка сообщения коммита: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## На что смотреть при приёмке

Случаи, которые спецификация подразумевает, но легко упустить. Тест на каждый — в задаче, которой принадлежит код.

1. **`wg` ответил пусто** (интерфейс пересоздаётся, контейнер в процессе запуска). Ожидание: это «awg2 недоступен», и пиры **не** помечаются удалёнными. Тест — задача 3, `test_zero_peers_is_unavailable_not_mass_removal`.
2. **Таймер отчёта сработал дважды за одни сутки** (`Persistent=true` после загрузки или ручной запуск). Ожидание: второе сообщение не уходит. Тест — задача 5, `test_second_send_same_day_is_skipped`.
3. **Имя клиента с `<`, `&` или длиннее столбца.** Ожидание: HTML остаётся корректным (Telegram не отклоняет сообщение), таблица не разъезжается. Тест — задача 4, `test_render_escapes_and_truncates_names`.
4. **Пир добавлен после начала учёта.** Ожидание: его счётчик засчитывается целиком, а не как точка отсчёта 0. Тест — задача 2, `test_new_peer_after_start_counts_whole_counter`.
5. **Пропуск сбора дольше 5 мин** (VPS занят, таймер стоял). Ожидание: байты учтены, пиковая скорость не завышена. Тест — задача 2, `test_long_gap_counts_bytes_without_peak`.

---

### Задача 1: разбор сырых данных и подключение тестов к воротам

**Файлы:**
- Создать: `services/vpn_monitor/vpnmon_parse.py`
- Создать: `tests/vpn_monitor/conftest.py`, `tests/vpn_monitor/test_parse.py`
- Изменить: `scripts/quality/preflight.sh` — список `for SVC_TESTS in …` в разделе 9
- Изменить: `.github/workflows/quality-checks.yml` — шаг после «STT tests»

**Интерфейсы:**
- Производит (`vpnmon_parse`): `split_sections(text, count) -> list[str]`; `parse_key_values(text) -> dict[str, list[str]]`; `parse_peers(allowed, transfer, handshakes) -> dict[key, {"vpn_ip": str|None, "rx": int, "tx": int, "handshake": int}]`; `parse_clients_table(text) -> dict[key, name]` (`ValueError` при ошибке); `parse_names_conf(text) -> list[(prefix, name)]`; `resolve_names(keys, table|None, conf) -> dict[key, name]`; `parse_cpu(stat) -> (busy, total)`; `parse_btime(stat) -> int`; `parse_mem(meminfo) -> (used, total)`; `parse_load1(loadavg) -> float`; `parse_net_dev(text, iface) -> (rx, tx)|None`; `parse_default_iface(route) -> str|None`; `parse_inspect(text) -> (pid, started, running)`; `shutdown_reason(journal) -> str|None`; константа `SECTION_MARK = "@@"`.

- [ ] **Шаг 1: conftest и падающие тесты**

`tests/vpn_monitor/conftest.py`:
```python
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SVC = os.path.join(ROOT, "services", "vpn_monitor")
if SVC not in sys.path:
    sys.path.insert(0, SVC)
```

`tests/vpn_monitor/test_parse.py`:
```python
"""Разбор сырых данных сборщика (спецификация 2026-10-04 §5–6). Ключи фиктивные."""
import json

import pytest

import vpnmon_parse as vp

KEY_A = "A" * 43 + "="
KEY_B = "B" * 43 + "="
KEY_C = "C+/c" + "c" * 39 + "="


def test_split_sections_by_marker():
    assert vp.split_sections("a\n@@\nb\nc\n@@\n\n@@\nd", 4) == ["a", "b\nc", "", "d"]


def test_split_sections_wrong_count_raises():
    with pytest.raises(ValueError):
        vp.split_sections("a\n@@\nb", 4)


def test_parse_peers_joins_three_fields():
    allowed = "%s\t10.8.1.2/32\n%s\t(none)\n" % (KEY_A, KEY_B)
    transfer = "%s\t100\t2000\n" % KEY_A
    handshakes = "%s\t1759560000\n%s\t0\n" % (KEY_A, KEY_B)
    peers = vp.parse_peers(allowed, transfer, handshakes)
    assert peers[KEY_A] == {"vpn_ip": "10.8.1.2", "rx": 100, "tx": 2000, "handshake": 1759560000}
    assert peers[KEY_B] == {"vpn_ip": None, "rx": 0, "tx": 0, "handshake": 0}


def test_parse_peers_garbage_number_raises():
    with pytest.raises(ValueError):
        vp.parse_peers("%s\t10.8.1.2/32" % KEY_A, "%s\tx\ty" % KEY_A, "")


def test_parse_clients_table_names():
    text = json.dumps([
        {"clientId": KEY_A, "userData": {"clientName": " Клиент-А "}},
        {"clientId": KEY_B, "userData": {}},
        {"clientId": KEY_C, "userData": "не словарь"},
        "мусор",
    ])
    assert vp.parse_clients_table(text) == {KEY_A: "Клиент-А"}


@pytest.mark.parametrize("text", ["", "не json", json.dumps({"a": 1})])
def test_parse_clients_table_bad_input_raises(text):
    with pytest.raises(ValueError):
        vp.parse_clients_table(text)


def test_parse_names_conf():
    text = "# комментарий\n\nC+/ccccc = Vostro\nshort = нет\nAAAAAAAA=запасной-1\nбез равенства\n"
    assert vp.parse_names_conf(text) == [("C+/ccccc", "Vostro"), ("AAAAAAAA", "запасной-1")]


def test_resolve_names_order():
    table = {KEY_A: "Клиент-А"}
    conf = [("AAAAAAAA", "из conf"), ("C+/ccccc", "Vostro")]
    names = vp.resolve_names([KEY_A, KEY_B, KEY_C], table, conf)
    assert names == {KEY_A: "Клиент-А", KEY_B: "ключ BBBBBBBB", KEY_C: "Vostro"}


def test_resolve_names_without_table_only_conf():
    conf = [("C+/ccccc", "Vostro")]
    assert vp.resolve_names([KEY_A, KEY_C], None, conf) == {KEY_C: "Vostro"}


def test_parse_cpu_counts_iowait_as_idle():
    stat = "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 1 2 3 4\n"
    assert vp.parse_cpu(stat) == (150, 1000)


def test_parse_cpu_missing_raises():
    with pytest.raises(ValueError):
        vp.parse_cpu("intr 1\n")


def test_parse_btime():
    assert vp.parse_btime("cpu  1 1 1 1\nbtime 1759555658\n") == 1759555658


def test_parse_mem():
    text = "MemTotal:        2014208 kB\nMemFree: 1 kB\nMemAvailable:    1572864 kB\n"
    assert vp.parse_mem(text) == ((2014208 - 1572864) * 1024, 2014208 * 1024)


def test_parse_mem_missing_raises():
    with pytest.raises(ValueError):
        vp.parse_mem("MemTotal: 1 kB\n")


def test_parse_load1():
    assert vp.parse_load1("0.25 0.10 0.05 1/120 4242\n") == 0.25


NET_DEV = (
    "Inter-|   Receive                            |  Transmit\n"
    " face |bytes    packets errs drop fifo frame compressed multicast|bytes\n"
    "    lo: 10 1 0 0 0 0 0 0 10 1 0 0 0 0 0 0\n"
    "enp0s3: 24561249442 20376542 0 0 0 0 0 0 25935795702 22654577 0 0 0 0 0 0\n"
)


def test_parse_net_dev():
    assert vp.parse_net_dev(NET_DEV, "enp0s3") == (24561249442, 25935795702)
    assert vp.parse_net_dev(NET_DEV, "awg0") is None


def test_parse_default_iface():
    route = ("Iface\tDestination\tGateway\tFlags\n"
             "docker0\t000011AC\t00000000\t0001\n"
             "enp0s3\t00000000\t0102A8C0\t0003\n")
    assert vp.parse_default_iface(route) == "enp0s3"
    assert vp.parse_default_iface("Iface\tDestination\n") is None


def test_parse_inspect():
    assert vp.parse_inspect("1764|2026-10-04T05:27:49.5Z|true\n") == (1764, "2026-10-04T05:27:49.5Z", True)
    with pytest.raises(ValueError):
        vp.parse_inspect("мусор")


def test_shutdown_reason_prefers_most_specific():
    journal = "Session closed\nSystem is powering down (hypervisor initiated shutdown).\n"
    assert vp.shutdown_reason(journal) == "hypervisor initiated shutdown"
    assert vp.shutdown_reason("ничего\n") is None
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_parse.py`
Expected: FAIL с `ModuleNotFoundError: No module named 'vpnmon_parse'`

- [ ] **Шаг 3: реализация**

`services/vpn_monitor/vpnmon_parse.py`:
```python
"""Учёт VPN и нагрузки VPS: разбор сырых данных (спецификация 2026-10-04 §5–6).

Только чистые функции: на вход текст, на выход числа и словари. Ни файлов, ни процессов.
"""
import json

SECTION_MARK = "@@"
# От самого точного к общему: строка «System is powering down (hypervisor initiated
# shutdown).» содержит два маркера, а нужен первый.
SHUTDOWN_MARKERS = (
    "hypervisor initiated shutdown",
    "Power key pressed",
    "System is rebooting",
    "System is powering down",
)


def split_sections(text, count):
    """Вывод постоянного скрипта чтения → `count` частей, разделённых строками «@@»."""
    parts = [[]]
    for line in text.splitlines():
        if line.strip() == SECTION_MARK:
            parts.append([])
        else:
            parts[-1].append(line)
    if len(parts) != count:
        raise ValueError("ожидалось %d секций, получено %d" % (count, len(parts)))
    return ["\n".join(part) for part in parts]


def parse_key_values(text):
    """Вывод `wg show <if> <поле>`: «ключ значение…» → {ключ: [значения]}."""
    out = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            out[fields[0]] = fields[1:]
    return out


def parse_peers(allowed_text, transfer_text, handshake_text):
    """Три поля `wg show` → {ключ: {vpn_ip, rx, tx, handshake}}.

    rx — получено сервером от клиента (отдача пользователя), tx — отправлено клиенту
    (загрузка пользователя); handshake — секунды эпохи, 0 = не было с запуска интерфейса.
    """
    transfer = parse_key_values(transfer_text)
    handshakes = parse_key_values(handshake_text)
    peers = {}
    for key, ips in parse_key_values(allowed_text).items():
        rx, tx = (transfer.get(key) or ["0", "0"])[:2]
        first_ip = ips[0].split("/")[0]
        peers[key] = {
            "vpn_ip": None if first_ip == "(none)" else first_ip,
            "rx": int(rx),
            "tx": int(tx),
            "handshake": int((handshakes.get(key) or ["0"])[0]),
        }
    return peers


def parse_clients_table(text):
    """`clientsTable` Amnezia (JSON-список) → {ключ: имя}. Ошибка разбора — ValueError."""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("clientsTable: ожидался список")
    names = {}
    for entry in data:
        user = entry.get("userData") if isinstance(entry, dict) else None
        name = user.get("clientName") if isinstance(user, dict) else None
        if name and entry.get("clientId"):
            names[entry["clientId"]] = str(name).strip()
    return names


def parse_names_conf(text):
    """`names.conf`: строки «префикс_ключа = имя» → [(префикс, имя)]; # — комментарий."""
    pairs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        prefix, name = (part.strip() for part in line.split("=", 1))
        if len(prefix) >= 6 and name:
            pairs.append((prefix, name))
    return pairs


def _name_from_conf(key, conf):
    for prefix, name in conf:
        if key.startswith(prefix):
            return name
    return None


def resolve_names(keys, table, conf):
    """Имя каждого пира: clientsTable → names.conf → «ключ abcd1234».

    table=None (clientsTable не прочитан): только имена из names.conf; остальных
    ключей в ответе нет — хранилище оставит им прежние имена.
    """
    out = {}
    for key in keys:
        name = table.get(key) if table is not None else None
        name = name or _name_from_conf(key, conf)
        if name is None and table is not None:
            name = "ключ " + key[:8]
        if name is not None:
            out[key] = name
    return out


def parse_cpu(stat_text):
    """Строка `cpu` из /proc/stat → (занято, всего) в тиках; iowait считается простоем."""
    for line in stat_text.splitlines():
        if line.startswith("cpu "):
            ticks = [int(x) for x in line.split()[1:9]]
            idle = ticks[3] + ticks[4]
            return sum(ticks) - idle, sum(ticks)
    raise ValueError("в /proc/stat нет строки cpu")


def parse_btime(stat_text):
    """Время загрузки (секунды эпохи) из /proc/stat."""
    for line in stat_text.splitlines():
        if line.startswith("btime "):
            return int(line.split()[1])
    raise ValueError("в /proc/stat нет btime")


def parse_mem(meminfo_text):
    """/proc/meminfo → (занято, всего) в байтах; занято = MemTotal − MemAvailable."""
    vals = {}
    for line in meminfo_text.splitlines():
        name, _, rest = line.partition(":")
        if name in ("MemTotal", "MemAvailable"):
            vals[name] = int(rest.split()[0]) * 1024
    if len(vals) != 2:
        raise ValueError("в /proc/meminfo нет MemTotal/MemAvailable")
    return vals["MemTotal"] - vals["MemAvailable"], vals["MemTotal"]


def parse_load1(loadavg_text):
    """Первое число /proc/loadavg."""
    return float(loadavg_text.split()[0])


def parse_net_dev(text, iface):
    """/proc/net/dev → (rx_bytes, tx_bytes) интерфейса; None, если его нет."""
    for line in text.splitlines():
        name, sep, rest = line.partition(":")
        if sep and name.strip() == iface:
            fields = rest.split()
            return int(fields[0]), int(fields[8])
    return None


def parse_default_iface(route_text):
    """/proc/net/route → интерфейс маршрута по умолчанию; None, если его нет."""
    for line in route_text.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 1 and fields[1] == "00000000":
            return fields[0]
    return None


def parse_inspect(text):
    """Вывод `docker inspect -f '{{.State.Pid}}|{{.State.StartedAt}}|{{.State.Running}}'`."""
    pid, started, running = text.strip().split("|")
    return int(pid), started, running == "true"


def shutdown_reason(journal_text):
    """Причина конца прошлой загрузки по её последним строкам журнала; None — не найдена."""
    for marker in SHUTDOWN_MARKERS:
        if marker in journal_text:
            return marker
    return None
```

- [ ] **Шаг 4: убедиться, что тесты проходят**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_parse.py`
Expected: все тесты PASS

- [ ] **Шаг 5: подключить каталог к воротам и CI**

`scripts/quality/preflight.sh`, раздел 9: в строке
`for SVC_TESTS in tests/llm_gateway tests/nas_api tests/watchdog tests/backup_api tests/stt; do`
добавить в конец ` tests/vpn_monitor`.

`.github/workflows/quality-checks.yml`: сразу после шага «STT tests» (тот же отступ):
```yaml
      # Учёт VPN и нагрузки VPS (спецификация 2026-10-04): только стандартная библиотека.
      - name: VPN monitor tests
        run: python -m pytest -q tests/vpn_monitor
```

- [ ] **Шаг 6: коммит**

```bash
git add services/vpn_monitor/vpnmon_parse.py tests/vpn_monitor scripts/quality/preflight.sh .github/workflows/quality-checks.yml
git commit -m "feat(vpnmon): parsers for wg, clientsTable and /proc" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: ворота пройдены, в разделе 9 строка `tests/vpn_monitor: N passed`.

---

### Задача 2: хранение и учёт приращений

**Файлы:**
- Создать: `services/vpn_monitor/vpnmon_store.py`
- Создать: `tests/vpn_monitor/test_store.py`

**Интерфейсы:**
- Потребляет: ничего из задачи 1.
- Производит (`vpnmon_store`): константы `HOUR=3600`, `DAY=86400`, `RETENTION_DAYS=400`, `MAX_RATE_INTERVAL=300`, `HOST_COUNTERS=("wan","awg","xray")`; `open_db(path) -> sqlite3.Connection`; `get_meta(db, key, default=None) -> str|default`; `set_meta(db, key, value)`; `get_state(db) -> dict[str,str]`; `set_state(db, mapping)`; `add_event(db, ts, kind, detail=None)` (`detail` — словарь, хранится JSON); `hour_of(ts) -> int`; `counter_delta(prev|None, cur, same_epoch) -> int`; `minute_rate(nbytes, elapsed) -> float|None`; `record_peers(db, now, peers, names, epoch)`; `record_host(db, now, host)`; `purge_old(db, now, days=RETENTION_DAYS)`. Функции `record_*`, `set_*`, `add_event` и `purge_old` **не делают commit**: транзакцией владеет вызывающий (`with db:`).
- Контракт словаря `host` для `record_host`:
  `{"boot_id": str, "btime": int, "cpu": (busy, total), "mem_used": int, "mem_total": int, "load1": float, "disk_pct": float, "conntrack": int|None, "counters": {"wan"|"awg"|"xray": (epoch, rx, tx)|None}, "started": {имя_контейнера: StartedAt|None}, "awg_ok": bool, "shutdown_reason": str|None (необязательно)}`.

- [ ] **Шаг 1: падающие тесты**

`tests/vpn_monitor/test_store.py`:
```python
"""Учёт приращений и хранение (спецификация 2026-10-04 §6). Ключи фиктивные."""
import json

import pytest

import vpnmon_store as vs

KEY_A = "A" * 43 + "="
KEY_B = "B" * 43 + "="
T0 = 1_759_600_800.0  # ровно начало часа UTC
MB = 1024 ** 2


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def peer(rx, tx, hs=0, ip="10.8.1.2"):
    return {"vpn_ip": ip, "rx": rx, "tx": tx, "handshake": hs}


def hourly(db, key):
    return db.execute("SELECT hour_utc, rx, tx, peak_bps FROM peer_hourly WHERE pubkey=? "
                      "ORDER BY hour_utc", (key,)).fetchall()


def make_host(**over):
    h = {
        "boot_id": "boot-1", "btime": 1_759_555_658, "cpu": (100, 1000),
        "mem_used": 500 * MB, "mem_total": 2000 * MB, "load1": 0.1, "disk_pct": 27.0,
        "conntrack": 400,
        "counters": {"wan": ("boot-1|enp0s3", 0, 0), "awg": ("boot-1|s1", 0, 0),
                     "xray": ("boot-1|x1", 0, 0)},
        "started": {"amnezia-awg2": "s1", "amnezia-xray": "x1"}, "awg_ok": True,
    }
    h.update(over)
    return h


def host_row(db, hour):
    cur = db.execute("SELECT * FROM host_hourly WHERE hour_utc=?", (hour,))
    names = [d[0] for d in cur.description]
    row = cur.fetchone()
    return dict(zip(names, row)) if row else None


def events(db):
    return [(k, json.loads(d)) for k, d in db.execute("SELECT kind, detail FROM events ORDER BY rowid")]


@pytest.mark.parametrize("prev, cur, same, expected", [
    (None, 5, True, 0), (5, 8, True, 3), (8, 3, True, 3), (5, 8, False, 8), (0, 9, True, 9),
])
def test_counter_delta(prev, cur, same, expected):
    assert vs.counter_delta(prev, cur, same) == expected


def test_minute_rate_bounds():
    assert vs.minute_rate(600, 60) == 80.0
    assert vs.minute_rate(600, 0) is None
    assert vs.minute_rate(600, 301) is None


def test_open_db_creates_private_file(tmp_path):
    import os
    import stat
    path = tmp_path / "x.db"
    vs.open_db(str(path)).close()
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert path.exists()


def test_first_run_is_baseline(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {KEY_A: "Клиент-А"}, "e1")
    assert hourly(db, KEY_A) == []
    assert vs.get_meta(db, "monitoring_start") == str(int(T0))
    assert db.execute("SELECT name, vpn_ip FROM peers").fetchall() == [("Клиент-А", "10.8.1.2")]


def test_increment_and_peak(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(160, 65000)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 60, 60000, 60060 * 8 / 60)]


def test_reset_by_epoch_counts_current_value(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(10, 20)}, {}, "e2")
    assert hourly(db, KEY_A) == [(int(T0), 10, 20, 0.0)]


def test_counter_decrease_same_epoch_is_reset(db):
    vs.record_peers(db, T0, {KEY_A: peer(100, 5000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(50, 100)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 50, 100, 0.0)]


def test_new_peer_after_start_counts_whole_counter(db):
    vs.record_peers(db, T0, {KEY_A: peer(1, 1)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(1, 1), KEY_B: peer(7, 9)}, {}, "e1")
    assert hourly(db, KEY_B) == [(int(T0), 7, 9, 0.0)]


def test_long_gap_counts_bytes_without_peak(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0)}, {}, "e1")
    vs.record_peers(db, T0 + 600, {KEY_A: peer(0, 6000)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 0, 6000, 0.0)]


def test_clock_backwards_resets_reference(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 100)}, {}, "e1")
    vs.record_peers(db, T0 - 10, {KEY_A: peer(0, 500)}, {}, "e1")
    assert hourly(db, KEY_A) == []
    vs.record_peers(db, T0 + 50, {KEY_A: peer(0, 800)}, {}, "e1")
    assert hourly(db, KEY_A) == [(int(T0), 0, 300, 300 * 8 / 60)]


def test_removed_and_returned(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0), KEY_B: peer(0, 0)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_B: peer(0, 0)}, {}, "e1")
    assert db.execute("SELECT removed_at FROM peers WHERE pubkey=?", (KEY_A,)).fetchone() == (int(T0 + 60),)
    vs.record_peers(db, T0 + 120, {KEY_A: peer(0, 0), KEY_B: peer(0, 0)}, {}, "e1")
    assert db.execute("SELECT removed_at FROM peers WHERE pubkey=?", (KEY_A,)).fetchone() == (None,)


def test_name_kept_when_missing_and_default_for_new(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0)}, {KEY_A: "Клиент-А"}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(0, 0), KEY_B: peer(0, 0)}, {}, "e1")
    rows = dict(db.execute("SELECT pubkey, name FROM peers"))
    assert rows == {KEY_A: "Клиент-А", KEY_B: "ключ BBBBBBBB"}


def test_handshake_survives_reset(db):
    vs.record_peers(db, T0, {KEY_A: peer(0, 0, hs=1_759_000_000)}, {}, "e1")
    vs.record_peers(db, T0 + 60, {KEY_A: peer(0, 0, hs=0)}, {}, "e2")
    assert db.execute("SELECT last_handshake FROM peers").fetchone() == (1_759_000_000,)


def test_host_first_sample_has_no_cpu(db):
    vs.record_host(db, T0, make_host())
    row = host_row(db, int(T0))
    assert (row["samples"], row["cpu_n"], row["mem_max"], row["disk_pct"]) == (1, 0, 500 * MB, 27.0)
    assert events(db) == []


def test_host_cpu_and_counters_between_samples(db):
    vs.record_host(db, T0, make_host())
    counters = {"wan": ("boot-1|enp0s3", 1000, 3000), "awg": ("boot-1|s1", 10, 20),
                "xray": ("boot-1|x1", 5, 6)}
    vs.record_host(db, T0 + 60, make_host(cpu=(200, 2000), counters=counters, conntrack=900))
    row = host_row(db, int(T0))
    assert (row["samples"], row["cpu_n"], row["cpu_sum"], row["cpu_max"]) == (2, 1, 10.0, 10.0)
    assert (row["wan_rx"], row["wan_tx"], row["awg_rx"], row["awg_tx"]) == (1000, 3000, 10, 20)
    assert (row["xray_rx"], row["xray_tx"], row["conntrack_max"]) == (5, 6, 900)


def test_boot_change_event_and_counter_reset(db):
    vs.record_host(db, T0, make_host(counters={"wan": ("boot-1|enp0s3", 9000, 9000),
                                               "awg": None, "xray": None}))
    counters = {"wan": ("boot-2|enp0s3", 100, 200), "awg": None, "xray": None}
    vs.record_host(db, T0 + 1900, make_host(boot_id="boot-2", btime=int(T0 + 1800),
                                            counters=counters,
                                            shutdown_reason="hypervisor initiated shutdown"))
    assert events(db) == [("vps_down", {"from": T0, "to": int(T0 + 1800),
                                        "reason": "hypervisor initiated shutdown"})]
    row = host_row(db, int(T0))
    assert (row["wan_rx"], row["wan_tx"], row["cpu_n"]) == (100, 200, 0)


def test_container_restart_event(db):
    vs.record_host(db, T0, make_host())
    vs.record_host(db, T0 + 60, make_host(started={"amnezia-awg2": "s2", "amnezia-xray": "x1"}))
    assert events(db) == [("container_start", {"name": "amnezia-awg2", "started": "s2"})]


def test_awg_availability_transitions(db):
    vs.record_host(db, T0, make_host())
    vs.record_host(db, T0 + 60, make_host(awg_ok=False))
    vs.record_host(db, T0 + 120, make_host(awg_ok=False))
    vs.record_host(db, T0 + 180, make_host())
    assert [k for k, _ in events(db)] == ["awg_unavailable", "awg_ok"]
    assert host_row(db, int(T0))["awg_miss"] == 2


def test_missing_counter_keeps_previous_reference(db):
    vs.record_host(db, T0, make_host(counters={"wan": None, "awg": None, "xray": ("boot-1|x1", 100, 100)}))
    vs.record_host(db, T0 + 60, make_host(counters={"wan": None, "awg": None, "xray": None}))
    vs.record_host(db, T0 + 120, make_host(counters={"wan": None, "awg": None, "xray": ("boot-1|x1", 150, 170)}))
    row = host_row(db, int(T0))
    assert (row["xray_rx"], row["xray_tx"]) == (50, 70)


def test_purge_old(db):
    old = int(T0) - 401 * vs.DAY
    db.execute("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, 1, 1, 0)", (KEY_A, old))
    db.execute("INSERT INTO host_hourly (hour_utc, samples) VALUES (?, 1)", (old,))
    vs.add_event(db, old, "vps_down", {})
    vs.record_peers(db, T0, {KEY_A: peer(0, 0)}, {}, "e1")
    vs.purge_old(db, T0)
    counts = [db.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
              for t in ("peer_hourly", "host_hourly", "events")]
    assert counts == [0, 0, 0]
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_store.py`
Expected: FAIL с `ModuleNotFoundError: No module named 'vpnmon_store'`

- [ ] **Шаг 3: реализация**

`services/vpn_monitor/vpnmon_store.py`:
```python
"""Учёт VPN и нагрузки VPS: SQLite и учёт приращений (спецификация 2026-10-04 §6).

Функции record_*, set_*, add_event и purge_old не делают commit: транзакцией
владеет вызывающий (`with db:`), чтобы один замер писался целиком или никак.
"""
import json
import os
import sqlite3

HOUR = 3600
DAY = 86400
RETENTION_DAYS = 400
MAX_RATE_INTERVAL = 300  # сек.: интервал длиннее — пропуск сбора, скорость не считаем
HOST_COUNTERS = ("wan", "awg", "xray")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS peers (
    pubkey TEXT PRIMARY KEY, name TEXT NOT NULL, vpn_ip TEXT,
    first_seen INTEGER NOT NULL, last_handshake INTEGER NOT NULL DEFAULT 0, removed_at INTEGER);
CREATE TABLE IF NOT EXISTS peer_state (
    pubkey TEXT PRIMARY KEY, rx INTEGER NOT NULL, tx INTEGER NOT NULL,
    ts REAL NOT NULL, epoch TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS peer_hourly (
    pubkey TEXT NOT NULL, hour_utc INTEGER NOT NULL, rx INTEGER NOT NULL DEFAULT 0,
    tx INTEGER NOT NULL DEFAULT 0, peak_bps REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (pubkey, hour_utc));
CREATE TABLE IF NOT EXISTS host_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS host_hourly (
    hour_utc INTEGER PRIMARY KEY, samples INTEGER NOT NULL DEFAULT 0,
    cpu_n INTEGER NOT NULL DEFAULT 0, cpu_sum REAL NOT NULL DEFAULT 0,
    cpu_max REAL NOT NULL DEFAULT 0, mem_max INTEGER NOT NULL DEFAULT 0,
    mem_total INTEGER NOT NULL DEFAULT 0, load_max REAL NOT NULL DEFAULT 0,
    disk_pct REAL NOT NULL DEFAULT 0, wan_rx INTEGER NOT NULL DEFAULT 0,
    wan_tx INTEGER NOT NULL DEFAULT 0, awg_rx INTEGER NOT NULL DEFAULT 0,
    awg_tx INTEGER NOT NULL DEFAULT 0, xray_rx INTEGER NOT NULL DEFAULT 0,
    xray_tx INTEGER NOT NULL DEFAULT 0, conntrack_max INTEGER NOT NULL DEFAULT 0,
    awg_miss INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS events (ts INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts);
"""

_HOST_COLS = ("cpu_n", "cpu_sum", "cpu_max", "mem_max", "mem_total", "load_max", "disk_pct",
              "wan_rx", "wan_tx", "awg_rx", "awg_tx", "xray_rx", "xray_tx", "conntrack_max",
              "awg_miss")
_HOST_MERGE = {"cpu_max": "MAX", "mem_max": "MAX", "load_max": "MAX", "conntrack_max": "MAX",
               "mem_total": "SET", "disk_pct": "SET"}


def _host_upsert_sql():
    sets = []
    for col in _HOST_COLS:
        how = _HOST_MERGE.get(col, "ADD")
        if how == "MAX":
            sets.append("%s=MAX(%s, excluded.%s)" % (col, col, col))
        elif how == "SET":
            sets.append("%s=excluded.%s" % (col, col))
        else:
            sets.append("%s=%s+excluded.%s" % (col, col, col))
    return ("INSERT INTO host_hourly (hour_utc, samples, %s) VALUES (?, 1, %s) "
            "ON CONFLICT(hour_utc) DO UPDATE SET samples=samples+1, %s"
            % (", ".join(_HOST_COLS), ", ".join("?" * len(_HOST_COLS)), ", ".join(sets)))


_HOST_UPSERT = _host_upsert_sql()


def open_db(path):
    """Открыть (и при нужде создать) БД. Новый файл создаётся с правами 0600."""
    if not os.path.exists(path):
        os.close(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600))
    db = sqlite3.connect(path, timeout=5)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    db.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1')")
    db.commit()
    return db


def get_meta(db, key, default=None):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(db, key, value):
    db.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def get_state(db):
    return dict(db.execute("SELECT key, value FROM host_state"))


def set_state(db, values):
    db.executemany("INSERT INTO host_state (key, value) VALUES (?, ?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   [(k, str(v)) for k, v in values.items()])


def add_event(db, ts, kind, detail=None):
    db.execute("INSERT INTO events (ts, kind, detail) VALUES (?, ?, ?)",
               (int(ts), kind, json.dumps(detail or {}, ensure_ascii=False)))


def hour_of(ts):
    return int(ts // HOUR) * HOUR


def counter_delta(prev, cur, same_epoch):
    """Прирост накопительного счётчика.

    prev=None — первый замер: точка отсчёта, прирост 0. Другая эпоха (перезагрузка,
    перезапуск контейнера) или уменьшение счётчика — сброс: прирост = cur.
    """
    if prev is None:
        return 0
    if not same_epoch or cur < prev:
        return cur
    return cur - prev


def minute_rate(nbytes, elapsed):
    """Бит/с за интервал между замерами; None, если интервал не годится для скорости."""
    if elapsed <= 0 or elapsed > MAX_RATE_INTERVAL:
        return None
    return nbytes * 8.0 / elapsed


def record_peers(db, now, peers, names, epoch):
    """Учёт одного замера пиров awg0. epoch = «boot_id|StartedAt контейнера»."""
    first_run = get_meta(db, "monitoring_start") is None
    if first_run:
        set_meta(db, "monitoring_start", int(now))
    for key, peer in peers.items():
        _upsert_peer(db, now, key, peer, names.get(key))
        _account_peer(db, now, key, peer, (epoch, first_run))
    _mark_removed(db, now, set(peers))


def _upsert_peer(db, now, key, peer, name):
    row = db.execute("SELECT name, last_handshake FROM peers WHERE pubkey=?", (key,)).fetchone()
    if row is None:
        db.execute("INSERT INTO peers (pubkey, name, vpn_ip, first_seen, last_handshake) "
                   "VALUES (?, ?, ?, ?, ?)",
                   (key, name or "ключ " + key[:8], peer["vpn_ip"], int(now), peer["handshake"]))
        return
    db.execute("UPDATE peers SET name=?, vpn_ip=?, last_handshake=?, removed_at=NULL WHERE pubkey=?",
               (name or row[0], peer["vpn_ip"], max(row[1], peer["handshake"]), key))


def _account_peer(db, now, key, peer, run):
    st = db.execute("SELECT rx, tx, ts, epoch FROM peer_state WHERE pubkey=?", (key,)).fetchone()
    drx, dtx, rate = _peer_increment(st, now, peer, run)
    db.execute("INSERT INTO peer_state (pubkey, rx, tx, ts, epoch) VALUES (?, ?, ?, ?, ?) "
               "ON CONFLICT(pubkey) DO UPDATE SET rx=excluded.rx, tx=excluded.tx, "
               "ts=excluded.ts, epoch=excluded.epoch", (key, peer["rx"], peer["tx"], now, run[0]))
    if drx or dtx:
        db.execute("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, ?, ?, ?) "
                   "ON CONFLICT(pubkey, hour_utc) DO UPDATE SET rx=rx+excluded.rx, "
                   "tx=tx+excluded.tx, peak_bps=MAX(peak_bps, excluded.peak_bps)",
                   (key, hour_of(now), drx, dtx, rate or 0.0))


def _peer_increment(st, now, peer, run):
    """(прирост rx, прирост tx, скорость бит/с или None) относительно прошлого замера.

    run = (эпоха, первый ли это замер учёта вообще).
    """
    epoch, first_run = run
    if st is None:
        base = None if first_run else 0  # пир появился после старта учёта — счётчик весь новый
        return counter_delta(base, peer["rx"], True), counter_delta(base, peer["tx"], True), None
    prev_rx, prev_tx, prev_ts, prev_epoch = st
    elapsed = now - prev_ts
    if elapsed <= 0:  # время пошло назад: замер становится новой точкой отсчёта (§8)
        return 0, 0, None
    same = prev_epoch == epoch
    drx = counter_delta(prev_rx, peer["rx"], same)
    dtx = counter_delta(prev_tx, peer["tx"], same)
    clean = same and peer["rx"] >= prev_rx and peer["tx"] >= prev_tx
    return drx, dtx, minute_rate(drx + dtx, elapsed) if clean else None


def _mark_removed(db, now, present):
    for (key,) in db.execute("SELECT pubkey FROM peers WHERE removed_at IS NULL").fetchall():
        if key not in present:
            db.execute("UPDATE peers SET removed_at=? WHERE pubkey=?", (int(now), key))


def record_host(db, now, host):
    """Учёт одного замера хоста: события, приращения, часовая строка, новое состояние."""
    st = get_state(db)
    _host_events(db, now, st, host)
    deltas = {name: _host_counter_delta(st, name, host["counters"].get(name))
              for name in HOST_COUNTERS}
    _add_host_hour(db, hour_of(now), host, _cpu_pct(st, host), deltas)
    set_state(db, _host_state(now, host))


def _host_events(db, now, st, host):
    old_boot = st.get("boot_id")
    if old_boot and old_boot != host["boot_id"]:
        add_event(db, now, "vps_down", {"from": float(st["ts"]), "to": host["btime"],
                                        "reason": host.get("shutdown_reason")})
    for name, started in host["started"].items():
        old = st.get("started:" + name)
        if old and started and old != started:
            add_event(db, now, "container_start", {"name": name, "started": started})
    was_ok = st.get("awg_ok", "1") == "1"
    if was_ok != host["awg_ok"]:
        add_event(db, now, "awg_ok" if host["awg_ok"] else "awg_unavailable")


def _host_counter_delta(st, name, cur):
    """(прирост rx, прирост tx) счётчика хоста; cur = (эпоха, rx, tx) или None."""
    if cur is None:
        return 0, 0
    epoch, rx, tx = cur
    same = st.get(name + "_epoch") == epoch
    prev_rx, prev_tx = st.get(name + "_rx"), st.get(name + "_tx")
    return (counter_delta(None if prev_rx is None else int(prev_rx), rx, same),
            counter_delta(None if prev_tx is None else int(prev_tx), tx, same))


def _cpu_pct(st, host):
    """Загрузка CPU, % за интервал с прошлого замера; None в первом замере загрузки."""
    if st.get("boot_id") != host["boot_id"] or "cpu_total" not in st:
        return None
    busy = host["cpu"][0] - int(st["cpu_busy"])
    total = host["cpu"][1] - int(st["cpu_total"])
    return 100.0 * busy / total if total > 0 else None


def _add_host_hour(db, hour, host, cpu, deltas):
    values = {
        "cpu_n": 0 if cpu is None else 1, "cpu_sum": cpu or 0.0, "cpu_max": cpu or 0.0,
        "mem_max": host["mem_used"], "mem_total": host["mem_total"], "load_max": host["load1"],
        "disk_pct": host["disk_pct"], "conntrack_max": host["conntrack"] or 0,
        "awg_miss": 0 if host["awg_ok"] else 1,
    }
    for name in HOST_COUNTERS:
        values[name + "_rx"], values[name + "_tx"] = deltas[name]
    db.execute(_HOST_UPSERT, [hour] + [values[col] for col in _HOST_COLS])


def _host_state(now, host):
    st = {"ts": now, "boot_id": host["boot_id"], "cpu_busy": host["cpu"][0],
          "cpu_total": host["cpu"][1], "awg_ok": "1" if host["awg_ok"] else "0"}
    for name, cur in host["counters"].items():
        if cur is not None:
            st[name + "_epoch"], st[name + "_rx"], st[name + "_tx"] = cur
    for name, started in host["started"].items():
        if started:
            st["started:" + name] = started
    return st


def purge_old(db, now, days=RETENTION_DAYS):
    """Удалить часовые строки и события старше `days` суток."""
    edge = int(now) - days * DAY
    db.execute("DELETE FROM peer_hourly WHERE hour_utc < ?", (edge,))
    db.execute("DELETE FROM host_hourly WHERE hour_utc < ?", (edge,))
    db.execute("DELETE FROM events WHERE ts < ?", (edge,))
```

- [ ] **Шаг 4: убедиться, что тесты проходят**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_store.py`
Expected: все тесты PASS

- [ ] **Шаг 5: коммит**

```bash
git add services/vpn_monitor/vpnmon_store.py tests/vpn_monitor/test_store.py
git commit -m "feat(vpnmon): reset-safe hourly accounting in SQLite" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Задача 3: сборщик `collect.py`

**Файлы:**
- Создать: `services/vpn_monitor/collect.py`
- Создать: `tests/vpn_monitor/test_collect.py`

**Интерфейсы:**
- Потребляет: `vpnmon_parse` (задача 1), `vpnmon_store` (задача 2), контракт `host` из задачи 2.
- Производит (`collect`): `WG_READ_SCRIPT`, `INSPECT_FORMAT`, `JOURNAL_PREV_BOOT`, `AWG="amnezia-awg2"`, `XRAY="amnezia-xray"`; `run(cmd) -> str|None`; `make_proc_reader(root) -> callable(rel) -> str` (нет файла → `""`); `disk_pct(path) -> float`; `inspect(runner, name) -> (pid, started, running)|None`; `gather_awg(runner, conf) -> (peers, names)|None`; `gather_host(proc, disk, awg_info, xray_info) -> host`; `snapshot(src) -> (awg|None, awg_info|None, host)`; `collect_once(db, now, src) -> (awg|None, host)`; `print_snapshot(awg, host)`; `main(argv=None) -> int`. `src` — любой объект с атрибутами `runner`, `proc`, `disk` (число, %), `conf` (список из `parse_names_conf`).

- [ ] **Шаг 1: падающие тесты**

`tests/vpn_monitor/test_collect.py`:
```python
"""Сборщик: замер, транзакция, недоступность awg, безопасность исходника (§5, §8)."""
import json
import os
import re
import types

import pytest

import collect
import vpnmon_store as vs

KEY_A = "A" * 43 + "="
KEY_B = "B" * 43 + "="
T0 = 1_759_600_800.0
AWG_STARTED = "2026-10-04T05:27:49.577484916Z"
SRC_PATH = os.path.join(os.path.dirname(collect.__file__), "collect.py")


def wg_output(a_tx=2000, table=None):
    if table is None:
        table = json.dumps([{"clientId": KEY_A, "userData": {"clientName": "Клиент-А"}}])
    return "\n".join([
        KEY_A + "\t10.8.1.2/32", KEY_B + "\t10.8.1.5/32", "@@",
        "%s\t100\t%d" % (KEY_A, a_tx), KEY_B + "\t0\t0", "@@",
        KEY_A + "\t1759560000", KEY_B + "\t0", "@@", table,
    ])


def proc_files(boot="boot-1", busy=150):
    return {
        "stat": "cpu  %d 0 0 %d 0 0 0 0 0 0\nbtime 1759555658\n" % (busy, 1000 - busy),
        "sys/kernel/random/boot_id": boot + "\n",
        "net/route": "Iface\tDestination\tGateway\nenp0s3\t00000000\t0102A8C0\t0003\n",
        "net/dev": "Inter-|\n face |\nenp0s3: 5000 1 0 0 0 0 0 0 7000 1 0 0 0 0 0 0\n",
        "meminfo": "MemTotal: 2000000 kB\nMemAvailable: 1500000 kB\n",
        "loadavg": "0.10 0.05 0.01 1/100 123\n",
        "sys/net/netfilter/nf_conntrack_count": "473\n",
        "1764/net/dev": "  awg0: 1000 5 0 0 0 0 0 0 5000 9 0 0 0 0 0 0\n",
        "1800/net/dev": "  eth0: 300 3 0 0 0 0 0 0 400 4 0 0 0 0 0 0\n",
    }


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[:2] == ["docker", "inspect"]:
            return self.outputs.get(("inspect", cmd[-1]))
        if cmd[:2] == ["docker", "exec"]:
            return self.outputs.get("exec")
        if cmd[0] == "journalctl":
            return self.outputs.get("journal")
        return None


def sources(files, exec_out="default", running="true", journal=None):
    outputs = {
        ("inspect", "amnezia-awg2"): "1764|%s|%s\n" % (AWG_STARTED, running),
        ("inspect", "amnezia-xray"): "1800|2026-10-04T05:27:49.6Z|true\n",
        "exec": wg_output() if exec_out == "default" else exec_out,
        "journal": journal,
    }
    return types.SimpleNamespace(runner=FakeRunner(outputs), proc=lambda rel: files.get(rel, ""),
                                 disk=27.0, conf=[])


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def count(db, table):
    return db.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]


def kinds(db):
    return [row[0] for row in db.execute("SELECT kind FROM events ORDER BY rowid")]


def test_snapshot_parses_everything():
    awg, info, host = collect.snapshot(sources(proc_files()))
    peers, names = awg
    assert peers[KEY_A]["tx"] == 2000 and names[KEY_B] == "ключ BBBBBBBB"
    assert info == (1764, AWG_STARTED, True)
    assert host["counters"]["awg"] == ("boot-1|" + AWG_STARTED, 1000, 5000)
    assert host["counters"]["wan"] == ("boot-1|enp0s3", 5000, 7000)
    assert host["counters"]["xray"][1:] == (300, 400)
    assert (host["conntrack"], host["awg_ok"], host["disk_pct"]) == (473, True, 27.0)


def test_collect_once_records_host_and_peers(db):
    collect.collect_once(db, T0, sources(proc_files()))
    assert dict(db.execute("SELECT pubkey, name FROM peers")) == {KEY_A: "Клиент-А",
                                                                   KEY_B: "ключ BBBBBBBB"}
    assert count(db, "host_hourly") == 1
    assert vs.get_meta(db, "monitoring_start") == str(int(T0))


def test_second_sample_counts_increments(db):
    collect.collect_once(db, T0, sources(proc_files()))
    collect.collect_once(db, T0 + 60, sources(proc_files(busy=250), exec_out=wg_output(a_tx=62000)))
    assert db.execute("SELECT tx, peak_bps FROM peer_hourly WHERE pubkey=?", (KEY_A,)).fetchone() == (60000, 8000.0)


def test_awg_unavailable_records_host_only(db):
    collect.collect_once(db, T0, sources(proc_files(), exec_out=None))
    assert count(db, "peers") == 0 and count(db, "host_hourly") == 1
    assert kinds(db) == ["awg_unavailable"]


def test_zero_peers_is_unavailable_not_mass_removal(db):
    collect.collect_once(db, T0, sources(proc_files()))
    collect.collect_once(db, T0 + 60, sources(proc_files(), exec_out="@@\n@@\n@@\n[]"))
    assert db.execute("SELECT COUNT(*) FROM peers WHERE removed_at IS NULL").fetchone()[0] == 2
    assert kinds(db) == ["awg_unavailable"]


def test_container_not_running_skips_exec(db):
    src = sources(proc_files(), running="false")
    collect.collect_once(db, T0, src)
    assert not any(cmd[:2] == ["docker", "exec"] for cmd in src.runner.calls)
    assert kinds(db) == ["awg_unavailable"]


def test_broken_clients_table_keeps_names(db):
    collect.collect_once(db, T0, sources(proc_files()))
    collect.collect_once(db, T0 + 60, sources(proc_files(), exec_out=wg_output(table="не json")))
    assert db.execute("SELECT name FROM peers WHERE pubkey=?", (KEY_A,)).fetchone() == ("Клиент-А",)


def test_journal_read_only_on_boot_change(db):
    first = sources(proc_files())
    collect.collect_once(db, T0, first)
    assert not any(cmd[0] == "journalctl" for cmd in first.runner.calls)
    journal = "System is powering down (hypervisor initiated shutdown).\n"
    second = sources(proc_files(boot="boot-2"), journal=journal)
    collect.collect_once(db, T0 + 1900, second)
    assert sum(cmd[0] == "journalctl" for cmd in second.runner.calls) == 1
    detail = json.loads(db.execute("SELECT detail FROM events WHERE kind='vps_down'").fetchone()[0])
    assert detail["reason"] == "hypervisor initiated shutdown"


def test_failure_inside_transaction_writes_nothing(db, monkeypatch):
    def boom(*_args):
        raise RuntimeError("сбой записи")
    monkeypatch.setattr(collect.vs, "record_peers", boom)
    with pytest.raises(RuntimeError):
        collect.collect_once(db, T0, sources(proc_files()))
    assert count(db, "host_hourly") == 0 and count(db, "host_state") == 0


def test_source_never_reads_secrets():
    src = open(SRC_PATH, encoding="utf-8").read()
    for word in ("dump", "showconf", "private"):
        assert word not in src.lower(), word


def test_docker_only_exec_and_inspect():
    src = open(SRC_PATH, encoding="utf-8").read()
    verbs = set(re.findall(r'"docker",\s*"(\w+)"', src))
    assert verbs == {"exec", "inspect"}


def test_read_script_is_constant_and_fails_closed():
    assert "%" not in collect.WG_READ_SCRIPT and "{" not in collect.WG_READ_SCRIPT
    assert collect.WG_READ_SCRIPT.startswith("set -e;")
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_collect.py`
Expected: FAIL с `ModuleNotFoundError: No module named 'collect'`

- [ ] **Шаг 3: реализация**

`services/vpn_monitor/collect.py`:
```python
#!/usr/bin/env python3
"""Учёт VPN и нагрузки VPS: один замер, только чтение (спецификация 2026-10-04 §5, §8).

В контейнере выполняется только WG_READ_SCRIPT; docker вызывается только с exec и inspect.
"""
import argparse
import os
import subprocess
import sys
import time
import types

import vpnmon_parse as vp
import vpnmon_store as vs

AWG = "amnezia-awg2"
XRAY = "amnezia-xray"
# set -e: сбой wg — это «awg2 недоступен», а не «ноль пиров» (иначе все пиры стали бы удалёнными).
WG_READ_SCRIPT = (
    "set -e; wg show awg0 allowed-ips; echo @@; wg show awg0 transfer; echo @@; "
    "wg show awg0 latest-handshakes; echo @@; cat /opt/amnezia/awg/clientsTable 2>/dev/null || true"
)
INSPECT_FORMAT = "{{.State.Pid}}|{{.State.StartedAt}}|{{.State.Running}}"
JOURNAL_PREV_BOOT = ["journalctl", "-b", "-1", "-n", "200", "-o", "cat", "-q", "--no-pager"]
DB_PATH = "/var/lib/nasa-vpnmon/vpnmon.db"
NAMES_PATH = "/etc/nasa-vpnmon/names.conf"
EXEC_TIMEOUT = 10


def run(cmd):
    """stdout команды или None (ошибка, код ≠ 0, таймаут): один источник не роняет замер."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=EXEC_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout if res.returncode == 0 else None


def make_proc_reader(root):
    """Функция чтения файла относительно root (обычно /proc); нет файла — пустая строка."""
    def read(rel):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""
    return read


def disk_pct(path):
    """Заполнение файловой системы, % — как Use% у df."""
    st = os.statvfs(path)
    used = st.f_blocks - st.f_bfree
    return 100.0 * used / (used + st.f_bavail) if used + st.f_bavail else 0.0


def inspect(runner, name):
    """(pid, StartedAt, запущен) контейнера; None, если docker не ответил."""
    out = runner(["docker", "inspect", "-f", INSPECT_FORMAT, name])
    try:
        return vp.parse_inspect(out) if out else None
    except ValueError:
        return None


def gather_awg(runner, conf):
    """(пиры, имена) из amnezia-awg2; None, если контейнер не ответил или пиров ноль."""
    out = runner(["docker", "exec", AWG, "sh", "-c", WG_READ_SCRIPT])
    if out is None:
        return None
    try:
        allowed, transfer, handshakes, table_text = vp.split_sections(out, 4)
        peers = vp.parse_peers(allowed, transfer, handshakes)
    except ValueError:
        return None
    if not peers:
        return None
    try:
        table = vp.parse_clients_table(table_text)
    except ValueError:
        table = None
    return peers, vp.resolve_names(peers, table, conf)


def container_counters(proc, info, iface, boot_id):
    """(эпоха, rx, tx) интерфейса в namespace запущенного контейнера; иначе None."""
    if not info or not info[2]:
        return None
    pair = vp.parse_net_dev(proc("%d/net/dev" % info[0]), iface)
    return None if pair is None else ("%s|%s" % (boot_id, info[1]),) + pair


def gather_host(proc, disk, awg_info, xray_info):
    """Метрики хоста по контракту vpnmon_store.record_host."""
    stat = proc("stat")
    boot_id = proc("sys/kernel/random/boot_id").strip()
    iface = vp.parse_default_iface(proc("net/route"))
    wan = vp.parse_net_dev(proc("net/dev"), iface) if iface else None
    mem_used, mem_total = vp.parse_mem(proc("meminfo"))
    conntrack = proc("sys/net/netfilter/nf_conntrack_count").strip()
    return {
        "boot_id": boot_id, "btime": vp.parse_btime(stat), "cpu": vp.parse_cpu(stat),
        "mem_used": mem_used, "mem_total": mem_total, "load1": vp.parse_load1(proc("loadavg")),
        "disk_pct": disk, "conntrack": int(conntrack) if conntrack.isdigit() else None,
        "counters": {
            "wan": None if wan is None else ("%s|%s" % (boot_id, iface),) + wan,
            "awg": container_counters(proc, awg_info, "awg0", boot_id),
            "xray": container_counters(proc, xray_info, "eth0", boot_id),
        },
        "started": {AWG: awg_info[1] if awg_info else None,
                    XRAY: xray_info[1] if xray_info else None},
    }


def snapshot(src):
    """Один замер без записи: (awg или None, сведения о контейнере awg, хост)."""
    awg_info, xray_info = inspect(src.runner, AWG), inspect(src.runner, XRAY)
    awg = gather_awg(src.runner, src.conf) if awg_info and awg_info[2] else None
    host = gather_host(src.proc, src.disk, awg_info, xray_info)
    host["awg_ok"] = awg is not None
    return awg, awg_info, host


def collect_once(db, now, src):
    """Замер и запись одной транзакцией (§6: при ошибке не пишется ничего)."""
    awg, awg_info, host = snapshot(src)
    old_boot = vs.get_state(db).get("boot_id")
    if old_boot and old_boot != host["boot_id"]:
        host["shutdown_reason"] = vp.shutdown_reason(src.runner(JOURNAL_PREV_BOOT) or "")
    with db:
        vs.record_host(db, now, host)
        if awg is not None:
            vs.record_peers(db, now, awg[0], awg[1], "%s|%s" % (host["boot_id"], awg_info[1]))
    return awg, host


def print_snapshot(awg, host):
    """--dry-run: разобранный замер для сверки с `wg show awg0 transfer`."""
    print("boot_id=%s cpu=%s mem=%d/%d load1=%.2f disk=%.1f%% conntrack=%s" % (
        host["boot_id"], host["cpu"], host["mem_used"], host["mem_total"], host["load1"],
        host["disk_pct"], host["conntrack"]))
    for name, cur in sorted(host["counters"].items()):
        print("%s: %s" % (name, "нет" if cur is None else "rx=%d tx=%d" % cur[1:]))
    if awg is None:
        print("awg: недоступен")
        return
    peers, names = awg
    for key, p in sorted(peers.items(), key=lambda kv: -kv[1]["tx"]):
        print("%s  %-24s %-12s rx=%d tx=%d hs=%d" % (
            key[:8], names.get(key, "?"), p["vpn_ip"], p["rx"], p["tx"], p["handshake"]))
    print("peers=%d" % len(peers))


def default_sources(names_path):
    try:
        with open(names_path, encoding="utf-8") as fh:
            conf = vp.parse_names_conf(fh.read())
    except OSError:
        conf = []
    return types.SimpleNamespace(runner=run, proc=make_proc_reader("/proc"),
                                 disk=disk_pct("/"), conf=conf)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Учёт VPN и нагрузки VPS: один замер (только чтение)")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--names", default=NAMES_PATH)
    ap.add_argument("--dry-run", action="store_true", help="напечатать замер, ничего не записывать")
    args = ap.parse_args(argv)
    os.umask(0o077)
    src = default_sources(args.names)
    if args.dry_run:
        awg, _, host = snapshot(src)
        print_snapshot(awg, host)
        return 0
    db = vs.open_db(args.db)
    try:
        collect_once(db, time.time(), src)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Шаг 4: убедиться, что тесты проходят**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: все тесты PASS (задачи 1–3)

- [ ] **Шаг 5: коммит**

```bash
git add services/vpn_monitor/collect.py tests/vpn_monitor/test_collect.py
git commit -m "feat(vpnmon): read-only one-minute collector" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Задача 4: выборки и текст отчёта

**Файлы:**
- Создать: `services/vpn_monitor/vpnmon_query.py`, `services/vpn_monitor/vpnmon_render.py`
- Создать: `tests/vpn_monitor/test_report_text.py`

**Интерфейсы:**
- Потребляет: `vpnmon_store` (`DAY`, `HOUR`, `get_meta`, `set_meta`, `add_event`, схема таблиц).
- Производит (`vpnmon_query`): `MSK`, `DAY`, `ONLINE_WINDOW=180`; `report_day(now) -> date`; `day_bounds(day) -> (start, end)`; `peer_totals(db, start, end) -> {key: (rx, tx, peak)}`; `host_summary(db, start, end) -> dict`; `events_between(db, start, end) -> [(ts, kind, dict)]`; `peers_list(db) -> [dict]`; `build_report(db, day, now) -> dict` с ключами `day, now, start, end, host, events, peers, day_totals, week_totals, month_totals, monitoring_start, failed_day`.
- Производит (`vpnmon_render`): `TG_LIMIT=4096`; `fmt_bytes`, `fmt_short`, `fmt_rate`, `fmt_time(ts, day)`, `docker_time(started) -> float|None`, `silence_counts(peers, now) -> {7|30|90: [имена]}`, `render(data) -> str` (без HTML), `to_messages(text, limit=TG_LIMIT) -> [str]` (каждое `<pre>…</pre>`, экранировано, ≤ limit).

- [ ] **Шаг 1: падающие тесты**

`tests/vpn_monitor/test_report_text.py`:
```python
"""Окна МСК, выборки и текст суточного отчёта (§7). Ключи и имена фиктивные."""
from datetime import date, datetime, timezone

import pytest

import vpnmon_query as vq
import vpnmon_render as vr
import vpnmon_store as vs

KEY_A, KEY_B = "A" * 43 + "=", "B" * 43 + "="
KEY_C, KEY_D = "C" * 43 + "=", "D" * 43 + "="
MB, GB, HOUR, DAY = 1024 ** 2, 1024 ** 3, 3600, 86400
DAY_UNDER_TEST = date(2026, 10, 4)
START = int(datetime(2026, 10, 3, 21, 0, tzinfo=timezone.utc).timestamp())
NOW = START + DAY + 10 * HOUR  # 05.10 10:00 МСК


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def seed(db):
    db.executemany("INSERT INTO peers (pubkey, name, vpn_ip, first_seen, last_handshake, removed_at) "
                   "VALUES (?, ?, ?, ?, ?, ?)", [
                       (KEY_A, "Клиент-А", "10.8.1.2", START - 40 * DAY, NOW - 30, None),
                       (KEY_B, "<b>&Клиент-Б-очень-длинное", "10.8.1.3", START - 40 * DAY, NOW - 10 * DAY, None),
                       (KEY_C, "Клиент-В", "10.8.1.4", START - 40 * DAY, 0, None),
                       (KEY_D, "Удалённый", "10.8.1.5", START - 40 * DAY, NOW - 100 * DAY, START),
                   ])
    db.executemany("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, ?, ?, ?)", [
        (KEY_A, START, 100 * MB, 3 * GB, 48e6),
        (KEY_A, START - 3 * DAY, 0, 2 * GB, 10e6),
        (KEY_A, START - HOUR, 0, 7 * GB, 99e6),  # 23:00 МСК 03.10 — не в сутках 04.10
        (KEY_B, START + 5 * HOUR, 10 * MB, 500 * MB, 2e6),
    ])
    db.execute("INSERT INTO host_hourly (hour_utc, samples, cpu_n, cpu_sum, cpu_max, mem_max, "
               "mem_total, load_max, disk_pct, wan_rx, wan_tx, xray_rx, xray_tx, conntrack_max) "
               "VALUES (?, 60, 60, 180.0, 41.0, ?, ?, 0.5, 27.0, ?, ?, ?, ?, 900)",
               (START, 610 * MB, 1967 * MB, 24 * GB, 25 * GB, 9 * MB, 9 * MB))
    vs.set_meta(db, "monitoring_start", START - 40 * DAY)
    db.commit()


def text_of(db):
    return vr.render(vq.build_report(db, DAY_UNDER_TEST, NOW))


def test_report_day_and_bounds():
    assert vq.report_day(datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc).timestamp()) == date(2026, 10, 4)
    assert vq.report_day(datetime(2026, 10, 4, 20, 59, tzinfo=timezone.utc).timestamp()) == date(2026, 10, 3)
    assert vq.day_bounds(DAY_UNDER_TEST) == (START, START + DAY)


def test_day_window_excludes_previous_msk_evening(db):
    seed(db)
    totals = vq.peer_totals(db, START, START + DAY)
    assert totals[KEY_A] == (100 * MB, 3 * GB, 48e6)


def test_render_main_blocks(db):
    seed(db)
    text = text_of(db)
    assert text.splitlines()[0] == "📡 VPN и VPS — 04.10 (МСК)"
    assert "VPS ✅  CPU ср 3 % · пик 41 %  ·  RAM пик 610 / 1967 МБ  ·  диск 27 %" in text
    assert "Сеть VPS: ↓ 24.0 ГБ  ↑ 25.0 ГБ  ·  conntrack пик 900" in text
    assert "AmneziaWG: 3 клиентов · с трафиком за сутки 2 · сейчас в сети 1" in text
    assert "Через туннель за сутки: ↓ 3.5 ГБ ↑ 110 МБ · контейнер xray: 18 МБ" in text
    assert "Сбор: 60 из 1440 мин" in text


def test_render_table_order_and_windows(db):
    seed(db)
    rows = [line for line in text_of(db).splitlines() if line.startswith(("Клиент-А", "<b>&"))]
    assert rows[0].split()[:4] == ["Клиент-А", "3.1G", "12.1G", "12.1G"]
    assert rows[0].endswith("48 Мбит/с")
    assert rows[1].startswith("<b>&Клиент-Б-о ") and "510M" in rows[1]


def test_render_silence_and_never(db):
    seed(db)
    text = text_of(db)
    assert "Молчат: >7 дн — 1 · >30 дн — 0 · >90 дн — 0" in text
    assert "  >7 дн: <b>&Клиент-Б-очень-длинное" in text
    assert "Не подключались с 25.08: 1 — Клиент-В" in text
    assert "Удалённый" not in text


def test_render_downtime_and_restart(db):
    seed(db)
    down_from = START + 7 * HOUR + 55 * 60
    down_to = down_from + 32 * 60
    started = datetime.fromtimestamp(down_to + 11, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".577Z"
    vs.add_event(db, down_to + 60, "vps_down", {"from": down_from, "to": down_to,
                                                "reason": "hypervisor initiated shutdown"})
    vs.add_event(db, down_to + 60, "container_start", {"name": "amnezia-awg2", "started": started})
    db.commit()
    text = text_of(db)
    assert "VPS ⚠️" in text
    assert "⚠️ Простой 07:55–08:27 (32 мин): hypervisor initiated shutdown" in text
    assert "↻ amnezia-awg2 — старт 08:27 (вместе с VPS)" in text


def test_render_previous_failure_first(db):
    seed(db)
    vs.set_meta(db, "last_report_failed", "2026-10-03")
    db.commit()
    assert text_of(db).splitlines()[0] == "⚠️ отчёт за 03.10 не был доставлен"


def test_render_empty_day(db):
    text = vr.render(vq.build_report(db, DAY_UNDER_TEST, NOW))
    assert "VPS: за сутки нет ни одного замера" in text
    assert "Трафика через туннель за сутки не было" in text


def test_render_escapes_and_truncates_names(db):
    seed(db)
    messages = vr.to_messages(text_of(db))
    body = messages[0][len("<pre>"):-len("</pre>")]
    assert "&lt;b&gt;&amp;Клиент-Б-о " in body
    assert "<b>" not in body
    assert all(len(m) <= vr.TG_LIMIT for m in messages)


def test_to_messages_splits_long_text_by_lines():
    text = "\n".join("строка %03d " % i + "x" * 30 for i in range(300))
    messages = vr.to_messages(text, limit=1000)
    assert len(messages) > 1
    assert all(m.startswith("<pre>") and m.endswith("</pre>") and len(m) <= 1000 for m in messages)
    joined = "\n".join(m[len("<pre>"):-len("</pre>")] for m in messages)
    assert joined == text


def test_formatters():
    assert (vr.fmt_bytes(18 * MB), vr.fmt_bytes(int(3.5 * GB))) == ("18 МБ", "3.5 ГБ")
    assert (vr.fmt_short(510 * MB), vr.fmt_short(int(12.1 * GB))) == ("510M", "12.1G")
    assert (vr.fmt_rate(0), vr.fmt_rate(48e6), vr.fmt_rate(2e5)) == ("—", "48 Мбит/с", "200 кбит/с")
    assert vr.docker_time("мусор") is None
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_report_text.py`
Expected: FAIL с `ModuleNotFoundError: No module named 'vpnmon_query'`

- [ ] **Шаг 3: реализация выборок**

`services/vpn_monitor/vpnmon_query.py`:
```python
"""Учёт VPN и нагрузки VPS: выборки для суточного отчёта (спецификация 2026-10-04 §7)."""
import json
from datetime import datetime, timedelta, timezone

import vpnmon_store as vs

MSK = timezone(timedelta(hours=3), "MSK")  # летнего времени в Москве нет с 2014 г.
DAY = vs.DAY
ONLINE_WINDOW = 180  # сек.: рукопожатие моложе — клиент «в сети»

_HOST_SUMS = ("samples", "cpu_n", "cpu_sum", "wan_rx", "wan_tx", "awg_rx", "awg_tx",
              "xray_rx", "xray_tx", "awg_miss")
_HOST_MAXES = ("cpu_max", "mem_max", "mem_total", "load_max", "conntrack_max")
_PEER_COLS = ("pubkey", "name", "vpn_ip", "first_seen", "last_handshake", "removed_at")


def report_day(now):
    """Сутки МСК, за которые отчитываемся: вчерашние относительно now."""
    return datetime.fromtimestamp(now, MSK).date() - timedelta(days=1)


def day_bounds(day):
    """[начало, конец) суток МСК в секундах эпохи."""
    start = int(datetime(day.year, day.month, day.day, tzinfo=MSK).timestamp())
    return start, start + DAY


def peer_totals(db, start, end):
    """{ключ: (rx, tx, пик бит/с)} за [start, end)."""
    rows = db.execute("SELECT pubkey, SUM(rx), SUM(tx), MAX(peak_bps) FROM peer_hourly "
                      "WHERE hour_utc >= ? AND hour_utc < ? GROUP BY pubkey", (start, end))
    return {key: (rx, tx, peak) for key, rx, tx, peak in rows}


def host_summary(db, start, end):
    """Сводка хоста за [start, end): суммы, пики, средний CPU, последнее заполнение диска."""
    cols = ["SUM(%s)" % c for c in _HOST_SUMS] + ["MAX(%s)" % c for c in _HOST_MAXES]
    row = db.execute("SELECT %s FROM host_hourly WHERE hour_utc >= ? AND hour_utc < ?"
                     % ", ".join(cols), (start, end)).fetchone()
    out = {key: (value or 0) for key, value in zip(_HOST_SUMS + _HOST_MAXES, row)}
    out["cpu_avg"] = out["cpu_sum"] / out["cpu_n"] if out["cpu_n"] else None
    last = db.execute("SELECT disk_pct FROM host_hourly WHERE hour_utc >= ? AND hour_utc < ? "
                      "ORDER BY hour_utc DESC LIMIT 1", (start, end)).fetchone()
    out["disk_pct"] = last[0] if last else None
    return out


def events_between(db, start, end):
    """[(ts, вид, подробности)] за [start, end) по времени."""
    rows = db.execute("SELECT ts, kind, detail FROM events WHERE ts >= ? AND ts < ? "
                      "ORDER BY ts, rowid", (start, end))
    return [(ts, kind, json.loads(detail or "{}")) for ts, kind, detail in rows]


def peers_list(db):
    rows = db.execute("SELECT %s FROM peers" % ", ".join(_PEER_COLS))
    return [dict(zip(_PEER_COLS, row)) for row in rows]


def build_report(db, day, now):
    """Все данные суточного отчёта; окна 7 и 30 дней заканчиваются этими сутками."""
    start, end = day_bounds(day)
    return {
        "day": day, "now": now, "start": start, "end": end,
        "host": host_summary(db, start, end),
        "events": events_between(db, start, end),
        "peers": peers_list(db),
        "day_totals": peer_totals(db, start, end),
        "week_totals": peer_totals(db, start - 6 * DAY, end),
        "month_totals": peer_totals(db, start - 29 * DAY, end),
        "monitoring_start": int(vs.get_meta(db, "monitoring_start", 0)),
        "failed_day": vs.get_meta(db, "last_report_failed", ""),
    }
```

- [ ] **Шаг 4: реализация текста**

`services/vpn_monitor/vpnmon_render.py`:
```python
"""Учёт VPN и нагрузки VPS: текст суточного отчёта (спецификация 2026-10-04 §7)."""
import html
from datetime import datetime, timezone

from vpnmon_query import DAY, MSK, ONLINE_WINDOW

MB = 1024 ** 2
GB = 1024 ** 3
TG_LIMIT = 4096
NAME_WIDTH = 14
SILENCE_DAYS = (7, 30, 90)
ROW = "%-*s %7s %7s %7s  %s"


def fmt_bytes(n):
    return "%.1f ГБ" % (n / GB) if n >= GB else "%d МБ" % round(n / MB)


def fmt_short(n):
    """Компактно для таблицы: 15.3G / 850M."""
    return "%.1fG" % (n / GB) if n >= GB else "%dM" % round(n / MB)


def fmt_rate(bps):
    if not bps:
        return "—"
    return "%.0f Мбит/с" % (bps / 1e6) if bps >= 1e6 else "%.0f кбит/с" % (bps / 1e3)


def fmt_time(ts, day):
    """ЧЧ:ММ по МСК; с датой, если момент вне отчётных суток."""
    moment = datetime.fromtimestamp(ts, MSK)
    return moment.strftime("%H:%M") if moment.date() == day else moment.strftime("%d.%m %H:%M")


def docker_time(started):
    """StartedAt докера (…Z, наносекунды) → секунды эпохи; None, если не разобрать."""
    try:
        moment = datetime.strptime(started[:19], "%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError):
        return None
    return moment.replace(tzinfo=timezone.utc).timestamp()


def silence_counts(peers, now):
    """{7|30|90: [имена]} — действующие пиры, молчащие дольше N дней (накопительно)."""
    out = {days: [] for days in SILENCE_DAYS}
    for peer in peers:
        if peer["removed_at"] or not peer["last_handshake"]:
            continue
        for days in SILENCE_DAYS:
            if now - peer["last_handshake"] > days * DAY:
                out[days].append(peer["name"])
    return out


def render(data):
    """Текст отчёта (без HTML): шапка, VPS, VPN, таблица клиентов, молчащие, полнота сбора."""
    lines = _head(data) + [""] + _host_lines(data) + [""] + _vpn_lines(data)
    lines += [""] + _table(data) + _silence_lines(data) + [_coverage(data)]
    return "\n".join(lines)


def _head(data):
    lines = []
    if data["failed_day"]:
        iso = data["failed_day"]
        lines.append("⚠️ отчёт за %s.%s не был доставлен" % (iso[8:10], iso[5:7]))
    lines.append("📡 VPN и VPS — %s (МСК)" % data["day"].strftime("%d.%m"))
    return lines


def _pct(value):
    return "—" if value is None else "%.0f %%" % value


def _alarm(host, down):
    mem_ratio = host["mem_max"] / host["mem_total"] if host["mem_total"] else 0.0
    return bool(down or host["awg_miss"] or host["cpu_max"] > 90 or mem_ratio > 0.9
                or (host["disk_pct"] or 0) > 85)


def _host_lines(data):
    host, day = data["host"], data["day"]
    if not host["samples"]:
        return ["VPS: за сутки нет ни одного замера"]
    down = [e for e in data["events"] if e[1] == "vps_down"]
    lines = [
        "VPS %s  CPU ср %s · пик %.0f %%  ·  RAM пик %d / %d МБ  ·  диск %s" % (
            "⚠️" if _alarm(host, down) else "✅", _pct(host["cpu_avg"]), host["cpu_max"],
            host["mem_max"] // MB, host["mem_total"] // MB, _pct(host["disk_pct"])),
        "Сеть VPS: ↓ %s  ↑ %s  ·  conntrack пик %d" % (
            fmt_bytes(host["wan_rx"]), fmt_bytes(host["wan_tx"]), host["conntrack_max"]),
    ]
    lines += [_down_line(event, day) for event in down]
    lines += _restart_lines(data["events"], down, day)
    if host["awg_miss"]:
        lines.append("⚠️ amnezia-awg2 не отвечал: %d мин" % host["awg_miss"])
    return lines


def _down_line(event, day):
    detail = event[2]
    minutes = max(0, round((detail["to"] - detail["from"]) / 60))
    return "⚠️ Простой %s–%s (%d мин): %s" % (
        fmt_time(detail["from"], day), fmt_time(detail["to"], day), minutes,
        detail.get("reason") or "причина в журнале не найдена")


def _restart_lines(events, down, day):
    lines = []
    for _ts, kind, detail in events:
        if kind != "container_start":
            continue
        started = docker_time(detail.get("started"))
        when = fmt_time(started, day) if started else "?"
        with_vps = started and any(abs(started - e[2]["to"]) < 600 for e in down)
        lines.append("↻ %s — старт %s%s" % (detail.get("name", "?"), when,
                                             " (вместе с VPS)" if with_vps else ""))
    return lines


def _vpn_lines(data):
    active = [p for p in data["peers"] if not p["removed_at"]]
    online = sum(1 for p in active
                 if p["last_handshake"] and data["now"] - p["last_handshake"] < ONLINE_WINDOW)
    totals = list(data["day_totals"].values())
    with_traffic = sum(1 for rx, tx, _ in totals if rx + tx > 0)
    up, down = sum(t[0] for t in totals), sum(t[1] for t in totals)
    xray = data["host"]["xray_rx"] + data["host"]["xray_tx"]
    return [
        "AmneziaWG: %d клиентов · с трафиком за сутки %d · сейчас в сети %d"
        % (len(active), with_traffic, online),
        "Через туннель за сутки: ↓ %s ↑ %s · контейнер xray: %s"
        % (fmt_bytes(down), fmt_bytes(up), fmt_bytes(xray)),
    ]


def _window_total(totals, key):
    rx, tx, _ = totals.get(key, (0, 0, 0))
    return rx + tx


def _table(data):
    names = {p["pubkey"]: p["name"] for p in data["peers"]}
    rows = sorted(((rx + tx, key) for key, (rx, tx, _) in data["day_totals"].items()
                   if rx + tx > 0), reverse=True)
    if not rows:
        return ["Трафика через туннель за сутки не было"]
    lines = [ROW % (NAME_WIDTH, "Клиент", "сутки", "7 дн", "30 дн", "пик")]
    for total, key in rows:
        lines.append(ROW % (
            NAME_WIDTH, names.get(key, "ключ " + key[:8])[:NAME_WIDTH], fmt_short(total),
            fmt_short(_window_total(data["week_totals"], key)),
            fmt_short(_window_total(data["month_totals"], key)),
            fmt_rate(data["day_totals"][key][2])))
    return lines


def _silence_lines(data):
    peers = data["peers"]
    silent = silence_counts(peers, data["now"])
    lines = ["Молчат: " + " · ".join(">%d дн — %d" % (d, len(silent[d])) for d in SILENCE_DAYS)]
    if silent[7]:
        lines.append("  >7 дн: " + ", ".join(sorted(silent[7])))
    never = sorted(p["name"] for p in peers if not p["removed_at"] and not p["last_handshake"])
    if never:
        since = datetime.fromtimestamp(data["monitoring_start"], MSK).strftime("%d.%m")
        lines.append("Не подключались с %s: %d — %s" % (since, len(never), ", ".join(never)))
    return lines


def _coverage(data):
    begin = max(data["start"], data["monitoring_start"])
    expected = max(0, (data["end"] - begin) // 60)
    return "Сбор: %d из %d мин" % (data["host"]["samples"], expected)


def to_messages(text, limit=TG_LIMIT):
    """Текст → сообщения Telegram (HTML) не длиннее limit; режет по строкам, не посреди."""
    room = limit - len("<pre></pre>")
    pieces = []
    for line in html.escape(text, quote=False).split("\n"):
        pieces.extend(line[i:i + room] for i in range(0, max(len(line), 1), room))
    chunks, current = [], []
    for piece in pieces:
        if current and len("\n".join(current + [piece])) > room:
            chunks.append(current)
            current = []
        current.append(piece)
    chunks.append(current)
    return ["<pre>" + "\n".join(chunk) + "</pre>" for chunk in chunks]
```

Примечание к `test_to_messages_splits_long_text_by_lines`: текст теста не содержит `<`, `>`, `&`, поэтому после снятия `<pre>` склеенный текст совпадает с исходным.

- [ ] **Шаг 5: убедиться, что тесты проходят**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: все тесты PASS (задачи 1–4)

- [ ] **Шаг 6: коммит**

```bash
git add services/vpn_monitor/vpnmon_query.py services/vpn_monitor/vpnmon_render.py tests/vpn_monitor/test_report_text.py
git commit -m "feat(vpnmon): daily report windows and text" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Задача 5: `report.py` — отправка в Telegram, повторы, однократность

**Файлы:**
- Создать: `services/vpn_monitor/report.py`
- Создать: `tests/vpn_monitor/test_report_send.py`

**Интерфейсы:**
- Потребляет: `vpnmon_query.build_report`, `vpnmon_query.report_day`, `vpnmon_render.render`, `vpnmon_render.to_messages`, `vpnmon_store.open_db/get_meta/set_meta/add_event/purge_old`.
- Производит (`report`): `HTTP_TIMEOUT=10`, `RETRY_PAUSES=(30, 60)`, `TEST_TEXT`; `read_env(path) -> dict`; `send_message(token, chat_id, text, opener=urlopen)`; `with_retries(action, sleep=time.sleep, pauses=RETRY_PAUSES) -> (bool, str|None)`; `deliver(messages, send, sleep=time.sleep) -> (bool, str|None)`; `run_send(db, now, day, send, force=False, sleep=time.sleep) -> int`; `main(argv=None) -> int`.

- [ ] **Шаг 1: падающие тесты**

`tests/vpn_monitor/test_report_send.py`:
```python
"""Отправка отчёта: HTML, повторы, однократность, отметка о сбое (§7–8)."""
import json
import urllib.error
from datetime import date

import pytest

import report
import vpnmon_store as vs

DAY_UNDER_TEST = date(2026, 10, 4)
NOW = 1_759_647_600.0  # 05.10 10:00 МСК
TOKEN = "123456:SECRET-TOKEN-VALUE"


class FakeResp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return json.dumps(self.body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


def test_read_env_strips_quotes(tmp_path):
    path = tmp_path / "telegram.env"
    path.write_text('# c\nTELEGRAM_BOT_TOKEN="abc"\nTELEGRAM_CHAT_ID=42\n', encoding="utf-8")
    assert report.read_env(str(path)) == {"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_CHAT_ID": "42"}


def test_send_message_posts_html():
    seen = {}

    def opener(req, timeout):
        seen.update(url=req.full_url, data=req.data.decode("utf-8"), timeout=timeout)
        return FakeResp({"ok": True, "result": {"message_id": 1}})
    report.send_message(TOKEN, "42", "<pre>x</pre>", opener)
    assert seen["url"] == "https://api.telegram.org/bot%s/sendMessage" % TOKEN
    assert "parse_mode=HTML" in seen["data"] and "chat_id=42" in seen["data"]
    assert seen["timeout"] == report.HTTP_TIMEOUT


def test_send_message_not_ok_raises():
    def opener(req, timeout):
        return FakeResp({"ok": False, "description": "Bad Request: can't parse entities"})
    with pytest.raises(RuntimeError):
        report.send_message(TOKEN, "42", "x", opener)


def test_with_retries_pauses_then_succeeds():
    attempts, pauses = [], []

    def action():
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("сеть")
    ok, error = report.with_retries(action, sleep=pauses.append)
    assert (ok, error, pauses) == (True, None, [30, 60])


def test_with_retries_error_text_has_no_token():
    def action():
        raise urllib.error.HTTPError("https://api.telegram.org/bot%s/sendMessage" % TOKEN,
                                     401, "Unauthorized", None, None)
    ok, error = report.with_retries(action, sleep=lambda _s: None)
    assert ok is False and "401" in error and TOKEN not in error


def test_run_send_success_marks_day(db):
    sent = []
    assert report.run_send(db, NOW, DAY_UNDER_TEST, sent.append, sleep=lambda _s: None) == 0
    assert len(sent) == 1 and sent[0].startswith("<pre>📡 VPN и VPS — 04.10")
    assert vs.get_meta(db, "last_report_day") == "2026-10-04"


def test_second_send_same_day_is_skipped(db):
    sent = []
    report.run_send(db, NOW, DAY_UNDER_TEST, sent.append, sleep=lambda _s: None)
    assert report.run_send(db, NOW + 60, DAY_UNDER_TEST, sent.append, sleep=lambda _s: None) == 0
    assert len(sent) == 1
    report.run_send(db, NOW + 120, DAY_UNDER_TEST, sent.append, force=True, sleep=lambda _s: None)
    assert len(sent) == 2


def test_failure_is_recorded_and_announced_next_time(db):
    def broken(_text):
        raise OSError("нет сети")
    assert report.run_send(db, NOW, DAY_UNDER_TEST, broken, sleep=lambda _s: None) == 1
    assert vs.get_meta(db, "last_report_failed") == "2026-10-04"
    assert db.execute("SELECT kind FROM events").fetchall() == [("report_failed",)]
    sent = []
    report.run_send(db, NOW + 86400, date(2026, 10, 5), sent.append, sleep=lambda _s: None)
    assert sent[0].startswith("<pre>⚠️ отчёт за 04.10 не был доставлен")
    assert vs.get_meta(db, "last_report_failed") == ""
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_report_send.py`
Expected: FAIL с `ModuleNotFoundError: No module named 'report'`

- [ ] **Шаг 3: реализация**

`services/vpn_monitor/report.py`:
```python
#!/usr/bin/env python3
"""Учёт VPN и нагрузки VPS: суточный отчёт в Telegram (спецификация 2026-10-04 §7–9)."""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

import vpnmon_query as vq
import vpnmon_render as vr
import vpnmon_store as vs

DB_PATH = "/var/lib/nasa-vpnmon/vpnmon.db"
ENV_PATH = "/etc/nasa-vpnmon/telegram.env"
HTTP_TIMEOUT = 10
RETRY_PAUSES = (30, 60)  # юнит: TimeoutStartSec=300 > 2 сообщения × (3 × 10 с + 90 с)
TEST_TEXT = "<pre>🧪 nasa-vpnmon: проверка канала. Отчёт приходит в 10:00 МСК.</pre>"


def read_env(path):
    """KEY=VALUE построчно, кавычки вокруг значения снимаются. Значения не печатаются."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def send_message(token, chat_id, text, opener=urllib.request.urlopen):
    """Одно сообщение (HTML). Ошибка — исключение; текст исключения без токена."""
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode("utf-8")
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token, data=data)
    with opener(req, timeout=HTTP_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError("Telegram: ok=false, %s" % body.get("description", "?"))


def with_retries(action, sleep=time.sleep, pauses=RETRY_PAUSES):
    """Три попытки: сразу, через 30 с, через 60 с. Возвращает (успех, последняя ошибка)."""
    error = None
    for pause in (0,) + tuple(pauses):
        if pause:
            sleep(pause)
        try:
            action()
            return True, None
        except (OSError, ValueError, RuntimeError) as exc:
            error = "%s: %s" % (type(exc).__name__, exc)
    return False, error


def deliver(messages, send, sleep=time.sleep):
    """Сообщения по порядку; на первом недоставленном — стоп. (успех, ошибка)."""
    for text in messages:
        ok, error = with_retries(lambda t=text: send(t), sleep)
        if not ok:
            return False, error
    return True, None


def run_send(db, now, day, send, force=False, sleep=time.sleep):
    """Отчёт за сутки: собрать, отправить, отметить. Код возврата — для systemd."""
    if not force and vs.get_meta(db, "last_report_day") == day.isoformat():
        print("отчёт за %s уже отправлен" % day.isoformat())
        return 0
    messages = vr.to_messages(vr.render(vq.build_report(db, day, now)))
    ok, error = deliver(messages, send, sleep)
    with db:
        if ok:
            vs.set_meta(db, "last_report_day", day.isoformat())
            vs.set_meta(db, "last_report_failed", "")
            vs.purge_old(db, now)
        else:
            vs.set_meta(db, "last_report_failed", day.isoformat())
            vs.add_event(db, now, "report_failed", {"day": day.isoformat(), "error": error})
    if not ok:
        print("не доставлено: %s" % error, file=sys.stderr)
        return 1
    print("отправлено сообщений: %d" % len(messages))
    return 0


def _parse_args(argv):
    ap = argparse.ArgumentParser(description="Суточный отчёт VPN/VPS в Telegram")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stdout", action="store_true", help="напечатать отчёт, не отправлять")
    mode.add_argument("--send", action="store_true", help="отправить отчёт за сутки")
    mode.add_argument("--test", action="store_true", help="одно проверочное сообщение")
    ap.add_argument("--day", type=date.fromisoformat, help="ГГГГ-ММ-ДД, сутки МСК; по умолчанию вчера")
    ap.add_argument("--force", action="store_true", help="отправить, даже если уже отправлено")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--env", default=ENV_PATH)
    return ap.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    os.umask(0o077)
    now = time.time()
    day = args.day or vq.report_day(now)
    db = vs.open_db(args.db)
    try:
        if args.stdout:
            print(vr.render(vq.build_report(db, day, now)))
            return 0
        env = read_env(args.env)

        def send(text):
            send_message(env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"], text)
        if args.test:
            ok, error = with_retries(lambda: send(TEST_TEXT))
            print("проверка: доставлено" if ok else "проверка: не доставлено — %s" % error)
            return 0 if ok else 1
        return run_send(db, now, day, send, args.force)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Шаг 4: убедиться, что тесты проходят**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: все тесты PASS (задачи 1–5)

- [ ] **Шаг 5: коммит**

```bash
git add services/vpn_monitor/report.py tests/vpn_monitor/test_report_send.py
git commit -m "feat(vpnmon): Telegram delivery with retries and once-per-day guard" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Задача 6: юниты, установщик, примеры и снимок правила №13

**Файлы:**
- Создать: `services/vpn_monitor/systemd/nasa-vpnmon-collect.service`, `…-collect.timer`, `…-report.service`, `…-report.timer`
- Создать: `services/vpn_monitor/install_vps.sh`, `services/vpn_monitor/rule13_snapshot.sh`
- Создать: `services/vpn_monitor/names.conf.example`, `services/vpn_monitor/telegram.env.example`
- Создать: `tests/vpn_monitor/test_deploy.py`

**Интерфейсы:**
- Потребляет: `report.HTTP_TIMEOUT`, `report.RETRY_PAUSES` (задача 5); список модулей `services/vpn_monitor/*.py`.
- Производит: файлы для задачи 8.

- [ ] **Шаг 1: падающие тесты**

`tests/vpn_monitor/test_deploy.py`:
```python
"""Установочные файлы: лимиты юнитов, бюджет таймаутов, установщик ничего лишнего не трогает."""
import os
import re

import report

SVC = os.path.join(os.path.dirname(report.__file__))


def text(*parts):
    return open(os.path.join(SVC, *parts), encoding="utf-8").read()


def test_collect_unit_limits():
    s = text("systemd", "nasa-vpnmon-collect.service")
    for line in ("Type=oneshot", "CPUQuota=20%", "MemoryMax=64M", "Nice=10", "TimeoutStartSec=30",
                 "ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/collect.py"):
        assert line in s, line


def test_collect_timer_every_minute():
    s = text("systemd", "nasa-vpnmon-collect.timer")
    assert "OnUnitActiveSec=60" in s and "OnBootSec=60" in s and "WantedBy=timers.target" in s


def test_report_timer_10_msk_persistent():
    s = text("systemd", "nasa-vpnmon-report.timer")
    assert "OnCalendar=*-*-* 10:00:00 Europe/Moscow" in s and "Persistent=true" in s


def test_report_timeout_exceeds_retry_budget():
    s = text("systemd", "nasa-vpnmon-report.service")
    assert "ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/report.py --send" in s
    timeout = int(re.search(r"TimeoutStartSec=(\d+)", s).group(1))
    per_message = 3 * report.HTTP_TIMEOUT + sum(report.RETRY_PAUSES)
    assert timeout > 2 * per_message


def test_installer_touches_nothing_else():
    s = text("install_vps.sh")
    for word in ("amnezia", "ufw", "iptables", "nginx", "sshd", "apt", "pip", "docker", "restart"):
        assert not re.search(r"\b%s\b" % word, s, re.IGNORECASE), word
    assert "telegram.env\n" not in s.replace("[ -f /etc/nasa-vpnmon/telegram.env ]", "")


def test_installer_installs_every_module():
    s = text("install_vps.sh")
    for name in sorted(f for f in os.listdir(SVC) if f.endswith(".py")):
        assert name in s, name


def test_telegram_example_has_no_values():
    for line in text("telegram.env.example").splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.split("=", 1)[1] == "", line


def test_rule13_snapshot_only_reads():
    s = text("rule13_snapshot.sh")
    assert set(re.findall(r"docker\s+(\w+)", s)) <= {"inspect", "exec"}
    assert "wg show awg0 peers" in s and "ss -tlnuH" in s
```

- [ ] **Шаг 2: убедиться, что тесты падают**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_deploy.py`
Expected: FAIL с `FileNotFoundError` на `systemd/nasa-vpnmon-collect.service`

- [ ] **Шаг 3: юниты**

`services/vpn_monitor/systemd/nasa-vpnmon-collect.service`:
```ini
[Unit]
Description=NAS VPN monitor: one read-only sample (spec 2026-10-04)
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/collect.py
Nice=10
CPUQuota=20%
MemoryMax=64M
TimeoutStartSec=30
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
```

`services/vpn_monitor/systemd/nasa-vpnmon-collect.timer`:
```ini
[Unit]
Description=NAS VPN monitor: sample every minute

[Timer]
OnBootSec=60
OnUnitActiveSec=60
AccuracySec=5s

[Install]
WantedBy=timers.target
```

`services/vpn_monitor/systemd/nasa-vpnmon-report.service`:
```ini
[Unit]
Description=NAS VPN monitor: daily Telegram report (spec 2026-10-04)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/report.py --send
Nice=10
CPUQuota=20%
MemoryMax=96M
TimeoutStartSec=300
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
```

`services/vpn_monitor/systemd/nasa-vpnmon-report.timer`:
```ini
[Unit]
Description=NAS VPN monitor: daily report at 10:00 MSK

[Timer]
OnCalendar=*-*-* 10:00:00 Europe/Moscow
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Шаг 4: установщик, снимок, примеры**

`services/vpn_monitor/install_vps.sh`:
```bash
#!/usr/bin/env bash
# Учёт VPN и нагрузки VPS: установка на VPS. Только по команде «деплой»,
# runbook — docs/plans/DEPLOY_VPNMON_2026-10.ru.md, спецификация 2026-10-04 §11.
#   bash install_vps.sh
# Код — /usr/local/lib/nasa-vpnmon, юниты — /etc/systemd/system, таймер сбора включается.
# Таймер отчёта включается, только если уже лежит /etc/nasa-vpnmon/telegram.env.
# Новых портов, пакетов и пользователей нет; VPN и сетевые правила не меняются.
set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
LIB=/usr/local/lib/nasa-vpnmon

install -d -m 0755 -o root -g root "$LIB"
install -d -m 0700 -o root -g root /etc/nasa-vpnmon /var/lib/nasa-vpnmon
for f in collect.py report.py vpnmon_parse.py vpnmon_store.py vpnmon_query.py vpnmon_render.py; do
  install -m 0644 -o root -g root "$HERE/$f" "$LIB/$f"
done
python3 -m py_compile "$LIB"/*.py

for u in nasa-vpnmon-collect.service nasa-vpnmon-collect.timer \
         nasa-vpnmon-report.service nasa-vpnmon-report.timer; do
  install -m 0644 -o root -g root "$HERE/systemd/$u" "/etc/systemd/system/$u"
done
if [ ! -f /etc/nasa-vpnmon/names.conf ]; then
  install -m 0600 -o root -g root "$HERE/names.conf.example" /etc/nasa-vpnmon/names.conf
fi

systemctl daemon-reload
systemctl enable --now nasa-vpnmon-collect.timer
if [ -f /etc/nasa-vpnmon/telegram.env ]; then
  systemctl enable --now nasa-vpnmon-report.timer
else
  echo "нет файла с токеном — таймер отчёта НЕ включён (см. runbook, шаг токена)" >&2
fi
systemctl list-timers --all 'nasa-vpnmon-*' --no-pager
```

`services/vpn_monitor/rule13_snapshot.sh`:
```bash
#!/usr/bin/env bash
# Правило №13: то, что обязано совпасть до и после установки или отката учёта VPN.
#   bash rule13_snapshot.sh > /root/vpnmon-rule13-before.txt
#   ... установка ...
#   bash rule13_snapshot.sh | diff /root/vpnmon-rule13-before.txt -   # пусто = норма
set -euo pipefail
for c in amnezia-awg2 amnezia-xray; do
  docker inspect -f "$c started={{.State.StartedAt}} restarts={{.RestartCount}} running={{.State.Running}}" "$c"
done
echo "awg0 peers=$(docker exec amnezia-awg2 wg show awg0 peers | wc -l)"
ss -tlnuH | awk '{print $1, $5}' | sort -u
```

`services/vpn_monitor/names.conf.example`:
```
# Имена пиров, которых нет в clientsTable Amnezia. На VPS: /etc/nasa-vpnmon/names.conf (0600).
# Формат: первые 8 символов публичного ключа = имя. Настоящий файл в git не кладётся.
# Префикс брать из первого столбца `python3 /usr/local/lib/nasa-vpnmon/collect.py --dry-run`.
# AbCdEfGh = Vostro
# IjKlMnOp = запасной-1
```

`services/vpn_monitor/telegram.env.example`:
```
# /etc/nasa-vpnmon/telegram.env (root, 0600): тот же бот и чат, что у ежедневного отчёта Jetson.
# Значения сюда не пишутся; на VPS файл переносится по runbook'у без вывода на экран.
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

- [ ] **Шаг 5: убедиться, что тесты и ворота проходят**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: все тесты PASS
Run: `bash scripts/quality/preflight.sh` (Git Bash, `.venv/Scripts` в PATH)
Expected: `ВОРОТА ПРОЙДЕНЫ`; раздел 1 видит два новых `.sh`; раздел 10 (храповик) без нарушений

- [ ] **Шаг 6: коммит**

```bash
git add services/vpn_monitor/systemd services/vpn_monitor/install_vps.sh services/vpn_monitor/rule13_snapshot.sh services/vpn_monitor/names.conf.example services/vpn_monitor/telegram.env.example tests/vpn_monitor/test_deploy.py
git commit -m "feat(vpnmon): systemd units, installer and rule-13 snapshot" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Задача 7: runbook, CHANGELOG, английские пары (исполнитель DeepSeek)

**Файлы:**
- Создать: `docs/plans/DEPLOY_VPNMON_2026-10.ru.md` и пару `docs/plans/DEPLOY_VPNMON_2026-10.md`. Содержание — шаги задачи 8 этого плана дословно, команды без изменений, плюс раздел «Откат».
- Создать: `docs/superpowers/plans/2026-10-04-vps-vpn-monitor.en.md`. Это не формат проекта `X.md`/`X.ru.md`: русский план уже лежит как `X.md`, и переименование сломало бы ссылки. Поэтому английская пара получает суффикс `.en.md`. Перевод полный.
- Изменить: `CHANGELOG.md` — запись в «Unreleased»: «VPS/VPN monitor: one-minute read-only collector and daily 10:00 MSK Telegram report (spec 2026-10-04)».

Карточка `ds-worker`, `needs_edit: true`, `base` — последний коммит задачи 6. В карточку не кладутся ключи пиров, имена и токены. Ведущий принимает работу сверкой: число разделов совпадает, все команды из задачи 8 присутствуют дословно, в EN-файлах нет кириллицы.

- [ ] **Шаг 1:** написать и запустить карточку (`ds-worker new` → `ds-worker run`)
- [ ] **Шаг 2:** принять по сверке выше (`ds-worker review --accept`) и влить коммит исполнителя в ветку (`git merge --ff-only deepseek/<task_id>`)

---

### Задача 8: выкат на VPS (только ведущий, после слова владельца «деплой»)

Зона критическая (правило №16): ни субагент, ни DeepSeek эту задачу не выполняют. Команды запускаются с рабочей станции. `VPS` ниже — `root@95.163.176.103` с ключом `~/.ssh/borovskoy_new_ed25519`.

- [ ] **Шаг 1: код на VPS во временный каталог**

```bash
cd "e:/Linux mint/virtual_VM/shared/NAS_Jetson_Nano"
tar -C services --exclude=__pycache__ -czf - vpn_monitor | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'rm -rf /root/vpnmon-src && mkdir -p /root/vpnmon-src && tar -C /root/vpnmon-src -xzf - && ls /root/vpnmon-src/vpn_monitor'
```

- [ ] **Шаг 2: снимок правила №13 «до»**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | tee /root/vpnmon-rule13-before.txt'
```
Ожидание: `amnezia-awg2`/`amnezia-xray` running, `awg0 peers=21`; среди слушающих наружу (`0.0.0.0`/`[::]`) только 22, 443, 40568/udp и прежние сервисные порты.

- [ ] **Шаг 3: пробный замер без записи и сверка с `wg`**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'cd /root/vpnmon-src/vpn_monitor && python3 collect.py --dry-run --names /nonexistent; echo ---; docker exec amnezia-awg2 wg show awg0 transfer | sort -k3 -n | tail -3 | cut -c1-8,44-'
```
Ожидание: `peers=21`; у трёх верхних по `tx` значения совпадают с `wg show` (с поправкой на секунды между командами); `awg: rx=… tx=…`, `wan`, `xray` не «нет».

- [ ] **Шаг 4: установка**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/install_vps.sh'
```
Ожидание: в списке таймеров есть `nasa-vpnmon-collect.timer`; сообщение «таймер отчёта НЕ включён» (токена ещё нет).

- [ ] **Шаг 5: `names.conf` — шесть безымянных пиров**

По выводу шага 3 взять префиксы ключей для `10.8.1.17` (Vostro) и `10.8.1.18`–`.22` («запасной-1»…«запасной-5» по возрастанию адреса) и записать на VPS. Значения в git не попадают.
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'umask 077; cat > /etc/nasa-vpnmon/names.conf' <<'EOF'
<префикс .17> = Vostro
<префикс .18> = запасной-1
<префикс .19> = запасной-2
<префикс .20> = запасной-3
<префикс .21> = запасной-4
<префикс .22> = запасной-5
EOF
```
Заглушки `<префикс …>` ведущий заменяет реальными префиксами из шага 3 в момент выполнения.

- [ ] **Шаг 6: токен с Jetson на VPS без вывода на экран**

С рабочей станции из домашней сети (правило №17). Сначала проверить, что файл на Jetson на месте:
```bash
ssh admin@192.168.0.50 'ls -l /etc/nasa-monitor/telegram.env'
```
Затем перенести две строки конвейером: значение идёт из stdout Jetson в stdin VPS и нигде не печатается.
```bash
ssh admin@192.168.0.50 'P=$(grep -E "^NEXTCLOUD_ADMIN_PASSWORD=" "$HOME/nasa/config/.env" | cut -d= -f2- | tr -d "\r"); echo "$P" | sudo -S -p "" grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /etc/nasa-monitor/telegram.env' \
  | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'umask 077; cat > /etc/nasa-vpnmon/telegram.env; chmod 600 /etc/nasa-vpnmon/telegram.env; grep -c "^TELEGRAM_" /etc/nasa-vpnmon/telegram.env'
```
Ожидание: `2`.

- [ ] **Шаг 7: проверочное сообщение и включение отчёта**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 /usr/local/lib/nasa-vpnmon/report.py --test && systemctl enable --now nasa-vpnmon-report.timer && systemctl list-timers --all "nasa-vpnmon-*" --no-pager'
```
Ожидание: `проверка: доставлено`; владелец видит сообщение 🧪; следующий запуск отчёта — 10:00 МСК.

- [ ] **Шаг 8: через 5 минут — данные в БД и расход ресурсов**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 -c "import sqlite3; d=sqlite3.connect(\"/var/lib/nasa-vpnmon/vpnmon.db\"); print(\"host\", d.execute(\"select count(*), sum(samples) from host_hourly\").fetchone(), \"peers\", d.execute(\"select count(*) from peers\").fetchone())"; systemctl show nasa-vpnmon-collect.service -p CPUUsageNSec -p MemoryPeak -p Result; journalctl -u nasa-vpnmon-collect -n 5 --no-pager; ls -l /var/lib/nasa-vpnmon /etc/nasa-vpnmon'
```
Ожидание: `peers (21,)`, `samples` ≥ 4; `Result=success`; `MemoryPeak` < 64 МБ; файлы 0600, каталоги 0700.

- [ ] **Шаг 9: отчёт за текущие сутки на экран**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 /usr/local/lib/nasa-vpnmon/report.py --stdout --day $(TZ=Europe/Moscow date +%F)'
```
Ожидание: все блоки макета §7; шесть пиров названы по `names.conf`; «Не подключались с ДД.ММ» — дата сегодняшняя.

- [ ] **Шаг 10: снимок правила №13 «после»**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | diff /root/vpnmon-rule13-before.txt - && echo "правило 13: без изменений"; rm -rf /root/vpnmon-src'
```
Ожидание: `правило 13: без изменений`. Любая разница — стоп, откат (ниже) и разбор.

- [ ] **Шаг 11: документация и публикация**

- Влить ветку `feat/vpn-monitor-2026-10` в `main` (`git merge --ff-only`) и выложить по процедуре правила №15.
- `CLAUDE.md` + `CLAUDE.en.md`: строка таблицы «VPN-учёт» (юниты, время отчёта); пиров **21** (замер 04.10); простой VPS 04.10 04:55–05:27 UTC; новая контрольная точка.
- Семье объявление **не нужно**: отчёт видит только владелец (правило №18 касается видимого семье).

- [ ] **Шаг 12: на следующий день в 10:00 МСК**

Пришёл настоящий отчёт; владелец подтверждает. При желании владельца — сверка объёма: скачать 100 МБ через VPN на известном устройстве, затем `report.py --stdout --day <сегодня>` показывает прирост около 100 МБ (±5 %) у этого клиента.

**Откат** (VPN не задет, проверка — снимок правила №13 до и после):
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'systemctl disable --now nasa-vpnmon-collect.timer nasa-vpnmon-report.timer; rm -f /etc/systemd/system/nasa-vpnmon-*; systemctl daemon-reload; rm -rf /usr/local/lib/nasa-vpnmon /etc/nasa-vpnmon /var/lib/nasa-vpnmon'
```
