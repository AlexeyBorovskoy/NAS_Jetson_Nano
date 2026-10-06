# VPS Load and VPN User Traffic Accounting — Implementation Plan

> Acceptance 2026-10-06: tasks 1–7 are ready locally; task 8 has not been executed. Commands below require a separately authorized deployment. Reading VPN counters requires explicit owner authorization for strictly read-only collection; the prohibition on changing Amnezia remains. The safety snapshot uses only `docker inspect` and `ss`; the owner verifies peer counts in Amnezia Desktop. Historical examples with 21 peers are dated measurements, not today's guarantee.
>
> Token transfer uses `sudo -n`, never a Nextcloud password. If the operator lacks approved non-interactive sudo access to the source file, stop and arrange access with the owner. An incomplete stream does not replace the existing token on the VPS. Rollback stops only this monitor and preserves its database and configuration.
>
> Delivery persists acknowledged chunks across runs. Lost Telegram acknowledgements can cause duplicates; exactly-once is not guaranteed. The 240-second budget controls admission of attempts; systemd terminates the process after 300 seconds. `Persistent=true` catches up the latest report day, not every missed day.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Russian version — `2026-10-04-vps-vpn-monitor.md` (RU canon; this file is its English pair). Code blocks are preserved verbatim from the Russian original, so Russian human-facing strings and comments inside them remain as in the source.

**Goal:** every minute, take AmneziaWG peer counters and host metrics on the VPS (read-only); once a day at 10:00 MSK send the owner a summary in Telegram.

**Architecture:** four modules on the Python standard library: raw-data parsing, storage and accounting in SQLite, queries for the report, report text. Plus two scripts: `collect.py` under a one-minute timer and `report.py` under a 10:00 MSK timer. They are installed into `/usr/local/lib/nasa-vpnmon/` by an installer with no packages and no ports.

**Stack:** Python 3.12 on the VPS (tests: 3.11 on Windows and Linux), `sqlite3`, `urllib`, systemd; pytest in tests only.

**Spec:** `docs/superpowers/specs/2026-10-04-vps-vpn-monitor-design.md` (EN; Russian pair — `2026-10-04-vps-vpn-monitor-design.ru.md`). The implementer reads it together with the plan.

## General constraints

- Standard library only. **Do not use `zoneinfo`:** on Windows it has no timezone database. MSK = `timezone(timedelta(hours=3), "MSK")`.
- Metrics ratchet (`scripts/quality/code_metrics.py`): **for a new function, cyclomatic complexity ≤ 10 and length ≤ 40 lines**, module ≤ 600 lines, parameters ≤ 5.
- Identifiers in English, comments and human-facing strings in Russian, as elsewhere in the repository.
- In `collect.py`, nowhere — including comments — do the words `dump`, `showconf` and `private` appear. `docker` is called only with `exec` and `inspect`. This is checked by a test.
- Paths on the VPS: code — `/usr/local/lib/nasa-vpnmon/`; DB — `/var/lib/nasa-vpnmon/vpnmon.db` (directory 0700, file 0600); `/etc/nasa-vpnmon/names.conf` and `/etc/nasa-vpnmon/telegram.env` (0600).
- Units: `nasa-vpnmon-collect.{service,timer}` (every 60 s; `CPUQuota=20%`, `MemoryMax=64M`, `Nice=10`, `TimeoutStartSec=50` — more than 4 subprocess calls × `EXEC_TIMEOUT` 10 s) and `nasa-vpnmon-report.{service,timer}` (`OnCalendar=*-*-* 10:00:00 Europe/Moscow`, `Persistent=true`, `TimeoutStartSec=300`).
- No new ports, packages or users. Amnezia, ufw, iptables, sshd and nginx are not touched.
- Real peer keys, people's names and tokens never get into git: tests use fake keys `"A" * 43 + "="` and names such as «Клиент-А».
- Tasks 1–7 are done locally, with no access to the VPS or the Jetson. Task 8 — lead only, and only after the owner says «деплой» (deploy).
- Tests: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor` (Windows) or `python -m pytest -q tests/vpn_monitor`. A commit runs the gate `.githooks/pre-commit`. `--no-verify` is forbidden. The last line of the commit message: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## What to watch for at acceptance

Cases the spec implies but that are easy to miss. Each has a test in the task that owns the code.

1. **`wg` returned empty** (the interface is being recreated, the container is starting). Expected: this is "awg2 unavailable", and peers are **not** marked removed. Test — task 3, `test_zero_peers_is_unavailable_not_mass_removal`.
2. **The report timer fired twice in the same day** (`Persistent=true` after boot, or a manual run). Expected: the second message is not sent. Test — task 5, `test_second_send_same_day_is_skipped`.
3. **A client name with `<`, `&`, or longer than the column.** Expected: the HTML stays valid (Telegram does not reject the message) and the table does not fall apart. Test — task 4, `test_render_escapes_and_truncates_names`.
4. **A peer added after accounting started.** Expected: its counter is counted in full, not as a zero starting point. Test — task 2, `test_new_peer_after_start_counts_whole_counter`.
5. **A collection gap longer than 5 min** (the VPS was busy, the timer was stalled). Expected: the bytes are counted, the peak rate is not inflated. Test — task 2, `test_long_gap_counts_bytes_without_peak`.

---

### Task 1: raw-data parsing and wiring the tests into the gates

**Files:**
- Create: `services/vpn_monitor/vpnmon_parse.py`
- Create: `tests/vpn_monitor/conftest.py`, `tests/vpn_monitor/test_parse.py`
- Change: `scripts/quality/preflight.sh` — the `for SVC_TESTS in …` list in section 9
- Change: `.github/workflows/quality-checks.yml` — the step after "STT tests"

**Interfaces:**
- Produces (`vpnmon_parse`): `split_sections(text, count) -> list[str]`; `parse_key_values(text) -> dict[str, list[str]]`; `parse_peers(allowed, transfer, handshakes) -> dict[key, {"vpn_ip": str|None, "rx": int, "tx": int, "handshake": int}]`; `parse_clients_table(text) -> dict[key, name]` (`ValueError` on error); `parse_names_conf(text) -> list[(prefix, name)]`; `resolve_names(keys, table|None, conf) -> dict[key, name]`; `parse_cpu(stat) -> (busy, total)`; `parse_btime(stat) -> int`; `parse_mem(meminfo) -> (used, total)`; `parse_load1(loadavg) -> float`; `parse_net_dev(text, iface) -> (rx, tx)|None`; `parse_default_iface(route) -> str|None`; `parse_inspect(text) -> (pid, started, running)`; `shutdown_reason(journal) -> str|None`; constant `SECTION_MARK = "@@"`.

- [ ] **Step 1: conftest and failing tests**

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

- [ ] **Step 2: confirm the tests fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_parse.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vpnmon_parse'`

- [ ] **Step 3: implementation**

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

- [ ] **Step 4: confirm the tests pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_parse.py`
Expected: all tests PASS

- [ ] **Step 5: wire the directory into the gates and CI**

`scripts/quality/preflight.sh`, section 9: on the line
`for SVC_TESTS in tests/llm_gateway tests/nas_api tests/watchdog tests/backup_api tests/stt; do`
add ` tests/vpn_monitor` at the end.

`.github/workflows/quality-checks.yml`: right after the "STT tests" step (same indentation):
```yaml
      # Учёт VPN и нагрузки VPS (спецификация 2026-10-04): только стандартная библиотека.
      - name: VPN monitor tests
        run: python -m pytest -q tests/vpn_monitor
```

- [ ] **Step 6: commit**

```bash
git add services/vpn_monitor/vpnmon_parse.py tests/vpn_monitor scripts/quality/preflight.sh .github/workflows/quality-checks.yml
git commit -m "feat(vpnmon): parsers for wg, clientsTable and /proc" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: the gates pass, section 9 shows the line `tests/vpn_monitor: N passed`.

---

### Task 2: storage and increment accounting

**Files:**
- Create: `services/vpn_monitor/vpnmon_store.py`
- Create: `tests/vpn_monitor/test_store.py`

**Interfaces:**
- Consumes: nothing from task 1.
- Produces (`vpnmon_store`): constants `HOUR=3600`, `DAY=86400`, `RETENTION_DAYS=400`, `MAX_RATE_INTERVAL=300`, `HOST_COUNTERS=("wan","awg","xray")`; `open_db(path) -> sqlite3.Connection`; `get_meta(db, key, default=None) -> str|default`; `set_meta(db, key, value)`; `get_state(db) -> dict[str,str]`; `set_state(db, mapping)`; `add_event(db, ts, kind, detail=None)` (`detail` is a dict, stored as JSON); `hour_of(ts) -> int`; `counter_delta(prev|None, cur, same_epoch) -> int`; `minute_rate(nbytes, elapsed) -> float|None`; `record_peers(db, now, peers, names, epoch)`; `record_host(db, now, host)`; `purge_old(db, now, days=RETENTION_DAYS)`. The functions `record_*`, `set_*`, `add_event` and `purge_old` **do not commit**: the caller owns the transaction (`with db:`).
- The `host` dict contract for `record_host`:
  `{"boot_id": str, "btime": int, "cpu": (busy, total), "mem_used": int, "mem_total": int, "load1": float, "disk_pct": float, "conntrack": int|None, "counters": {"wan"|"awg"|"xray": (epoch, rx, tx)|None}, "started": {имя_контейнера: StartedAt|None}, "awg_ok": bool, "shutdown_reason": str|None (необязательно)}`.

- [ ] **Step 1: failing tests**

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

- [ ] **Step 2: confirm the tests fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_store.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vpnmon_store'`

- [ ] **Step 3: implementation**

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

- [ ] **Step 4: confirm the tests pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_store.py`
Expected: all tests PASS

- [ ] **Step 5: commit**

```bash
git add services/vpn_monitor/vpnmon_store.py tests/vpn_monitor/test_store.py
git commit -m "feat(vpnmon): reset-safe hourly accounting in SQLite" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: the `collect.py` collector

**Files:**
- Create: `services/vpn_monitor/collect.py`
- Create: `tests/vpn_monitor/test_collect.py`

**Interfaces:**
- Consumes: `vpnmon_parse` (task 1), `vpnmon_store` (task 2), the `host` contract from task 2.
- Produces (`collect`): `WG_READ_SCRIPT`, `INSPECT_FORMAT`, `JOURNAL_PREV_BOOT`, `AWG="amnezia-awg2"`, `XRAY="amnezia-xray"`; `run(cmd) -> str|None`; `make_proc_reader(root) -> callable(rel) -> str` (no file → `""`); `disk_pct(path) -> float`; `inspect(runner, name) -> (pid, started, running)|None`; `gather_awg(runner, conf) -> (peers, names)|None`; `gather_host(proc, disk, awg_info, xray_info) -> host`; `snapshot(src) -> (awg|None, awg_info|None, host)`; `collect_once(db, now, src) -> (awg|None, host)`; `print_snapshot(awg, host)`; `main(argv=None) -> int`. `src` — any object with attributes `runner`, `proc`, `disk` (a number, %), `conf` (a list from `parse_names_conf`).

- [ ] **Step 1: failing tests**

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

- [ ] **Step 2: confirm the tests fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_collect.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'collect'`

- [ ] **Step 3: implementation**

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

- [ ] **Step 4: confirm the tests pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: all tests PASS (tasks 1–3)

- [ ] **Step 5: commit**

```bash
git add services/vpn_monitor/collect.py tests/vpn_monitor/test_collect.py
git commit -m "feat(vpnmon): read-only one-minute collector" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: queries and report text

**Files:**
- Create: `services/vpn_monitor/vpnmon_query.py`, `services/vpn_monitor/vpnmon_render.py`
- Create: `tests/vpn_monitor/test_report_text.py`

**Interfaces:**
- Consumes: `vpnmon_store` (`DAY`, `HOUR`, `get_meta`, `set_meta`, `add_event`, the table schema).
- Produces (`vpnmon_query`): `MSK`, `DAY`, `ONLINE_WINDOW=180`; `report_day(now) -> date`; `day_bounds(day) -> (start, end)`; `peer_totals(db, start, end) -> {key: (rx, tx, peak)}`; `host_summary(db, start, end) -> dict`; `events_between(db, start, end) -> [(ts, kind, dict)]`; `peers_list(db) -> [dict]`; `build_report(db, day, now) -> dict` with keys `day, now, start, end, host, events, peers, day_totals, week_totals, month_totals, monitoring_start, failed_day`.
- Produces (`vpnmon_render`): `TG_LIMIT=4096`; `fmt_bytes`, `fmt_short`, `fmt_rate`, `fmt_time(ts, day)`, `docker_time(started) -> float|None`, `silence_counts(peers, now) -> {7|30|90: [names]}`, `render(data) -> str` (no HTML), `to_messages(text, limit=TG_LIMIT) -> [str]` (each `<pre>…</pre>`, escaped, ≤ limit).

- [ ] **Step 1: failing tests**

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


def test_long_line_entities_and_emoji_remain_complete():
    import html
    text = "<&\U0001f600>" * 1500
    messages = vr.to_messages(text, limit=97)
    bodies = [m[5:-6] for m in messages]
    assert "".join(html.unescape(body) for body in bodies) == text
    assert all(len(m.encode("utf-16-le")) // 2 <= 97 for m in messages)
    assert all(not body.endswith(("&", "&l", "&lt", "&a", "&am", "&amp")) for body in bodies)


def test_message_preserves_blank_lines():
    import html
    text = "\n\n<&>\n\n"
    assert html.unescape(vr.to_messages(text)[0][5:-6]) == text


@pytest.mark.parametrize("limit", [0, 11, 12])
def test_message_rejects_limit_that_cannot_fit_character(limit):
    with pytest.raises(ValueError):
        vr.to_messages("&", limit=limit)


def test_removed_peer_traffic_still_in_day_table_not_silence(db):
    seed(db)
    db.execute("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, ?, ?, ?)",
               (KEY_D, START, 0, 20 * MB, 1e6))
    text = text_of(db)
    assert "Удалённый" in text
    assert "с трафиком за сутки 3" in text
    assert "AmneziaWG: 3 клиентов" in text
    assert "Молчат: >7 дн — 1 · >30 дн — 0 · >90 дн — 0" in text


def test_week_and_month_boundaries(db):
    seed(db)
    db.executemany("INSERT INTO peer_hourly (pubkey, hour_utc, rx, tx, peak_bps) VALUES (?, ?, 0, ?, 1)", [
        (KEY_C, START - 6 * DAY, MB),
        (KEY_C, START - 6 * DAY - HOUR, 2 * MB),
        (KEY_C, START - 29 * DAY, 4 * MB),
        (KEY_C, START - 29 * DAY - HOUR, 8 * MB),
        (KEY_C, START + DAY, 16 * MB),
    ])
    data = vq.build_report(db, DAY_UNDER_TEST, NOW)
    assert KEY_C not in data["day_totals"]
    assert data["week_totals"][KEY_C][1] == MB
    assert data["month_totals"][KEY_C][1] == 7 * MB
```

- [ ] **Step 2: confirm the tests fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_report_text.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vpnmon_query'`

- [ ] **Step 3: implementation of the queries**

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

- [ ] **Step 4: implementation of the text**

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
        if peer["removed_at"] is not None or not peer["last_handshake"]:
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
    active = [p for p in data["peers"] if p["removed_at"] is None]
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
    never = sorted(p["name"] for p in peers if p["removed_at"] is None and not p["last_handshake"])
    if never:
        since = datetime.fromtimestamp(data["monitoring_start"], MSK).strftime("%d.%m")
        lines.append("Не подключались с %s: %d — %s" % (since, len(never), ", ".join(never)))
    return lines


def _coverage(data):
    begin = max(data["start"], data["monitoring_start"])
    expected = max(0, (data["end"] - begin) // 60)
    return "Сбор: %d из %d мин" % (data["host"]["samples"], expected)


def _html_size(text):
    """Conservative limit: escaped HTML measured in UTF-16 code units."""
    return len(html.escape(text, quote=False).encode("utf-16-le")) // 2


def _split_line(line, room):
    pieces, current, used = [], [], 0
    for char in line:
        size = _html_size(char)
        if size > room:
            raise ValueError("limit cannot fit an escaped character")
        if used + size > room:
            pieces.append("".join(current))
            current, used = [], 0
        current.append(char)
        used += size
    pieces.append("".join(current))
    return pieces


def to_messages(text, limit=TG_LIMIT):
    """Escape each complete chunk, preserving entities and Unicode characters."""
    room = limit - len("<pre></pre>")
    if room < 1:
        raise ValueError("limit must allow a nonempty pre block")
    chunks, current = [], None
    for line in text.split("\n"):
        pieces = _split_line(line, room)
        for index, piece in enumerate(pieces):
            candidate = current + "\n" + piece if current is not None else piece
            if current is not None and (_html_size(candidate) > room or index):
                chunks.append(current)
                current = piece
            else:
                current = candidate
    chunks.append(current)
    return ["<pre>" + html.escape(chunk or "", quote=False) + "</pre>" for chunk in chunks]
```

Note on `test_to_messages_splits_long_text_by_lines`: the test text contains no `<`, `>`, `&`, so after stripping `<pre>` the joined text matches the original.

- [ ] **Step 5: confirm the tests pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: all tests PASS (tasks 1–4)

- [ ] **Step 6: commit**

```bash
git add services/vpn_monitor/vpnmon_query.py services/vpn_monitor/vpnmon_render.py tests/vpn_monitor/test_report_text.py
git commit -m "feat(vpnmon): daily report windows and text" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `report.py` — Telegram delivery, retries, once-per-day guard

**Files:**
- Create: `services/vpn_monitor/report.py`
- Create: `tests/vpn_monitor/test_report_send.py`

**Interfaces:**
- Consumes: `vpnmon_query.build_report`, `vpnmon_query.report_day`, `vpnmon_render.render`, `vpnmon_render.to_messages`, `vpnmon_store.open_db/get_meta/set_meta/add_event/purge_old`.
- Produces (`report`): `HTTP_TIMEOUT=10`, `RETRY_PAUSES=(30, 60)`, `TEST_TEXT`; `read_env(path) -> dict`; `send_message(token, chat_id, text, opener=urlopen)`; `with_retries(action, sleep=time.sleep, pauses=RETRY_PAUSES) -> (bool, str|None)`; `deliver(messages, send, sleep=time.sleep) -> (bool, str|None)`; `run_send(db, now, day, send, force=False, sleep=time.sleep) -> int`; `main(argv=None) -> int`.

- [ ] **Step 1: failing tests**

`tests/vpn_monitor/test_report_send.py`:
```python
"""Delivery acknowledgement, retries, concurrent claims and private errors."""
from datetime import date
import io
import json
import threading
import urllib.error

import pytest
import report
import vpnmon_store as vs

DAY = date(2026, 10, 4)
NOW = 1_791_183_600.0
TOKEN = "mock-test-token"


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


class Response:
    def __init__(self, body):
        self.body = body

    def read(self):
        return json.dumps(self.body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_local_and_stdin_configuration(tmp_path, monkeypatch):
    text = '# comment\nTELEGRAM_BOT_TOKEN="abc"\nTELEGRAM_CHAT_ID=42\n'
    path = tmp_path / "telegram.env"
    path.write_text(text)
    expected = {"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_CHAT_ID": "42"}
    assert report.read_env(path) == expected
    monkeypatch.setattr(report.sys, "stdin", io.StringIO(text))
    assert report.read_env("-") == expected


def test_http_html_and_timeout():
    seen = {}

    def opener(req, timeout):
        seen.update(url=req.full_url, data=req.data.decode(), timeout=timeout)
        return Response({"ok": True})

    report.send_message(TOKEN, "42", "<pre>x</pre>", opener)
    assert seen["url"] == "https://api.telegram.org/bot%s/sendMessage" % TOKEN
    assert "parse_mode=HTML" in seen["data"] and "chat_id=42" in seen["data"]
    assert seen["timeout"] == 10


@pytest.mark.parametrize("body", [{"ok": False, "description": TOKEN}, [], None])
def test_rejected_response_never_exposes_body(body):
    with pytest.raises(RuntimeError) as caught:
        report.send_message(TOKEN, "42", "x", lambda *a, **k: Response(body))
    assert TOKEN not in str(caught.value)


def test_retry_pauses_and_success():
    attempts, pauses = [], []

    def action():
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("secret")

    assert report.with_retries(action, pauses.append) == (True, None)
    assert pauses == [30, 60]


def test_retry_error_redacts_url_and_arbitrary_secrets():
    def action():
        raise urllib.error.HTTPError("https://api.telegram.org/bot" + TOKEN, 401, TOKEN, None, None)

    ok, error = report.with_retries(action, lambda _: None)
    assert not ok and "401" in error and TOKEN not in error


def test_once_per_day_including_out_of_order_reports(db):
    sent = []
    assert report.run_send(db, NOW, DAY, sent.append) == 0
    assert vs.get_meta(db, "last_report_day") == DAY.isoformat()
    report.run_send(db, NOW, date(2026, 10, 5), sent.append)
    assert report.run_send(db, NOW, DAY, sent.append) == 0
    assert len(sent) == 2
    report.run_send(db, NOW, DAY, sent.append, force=True)
    assert len(sent) == 3


def test_partial_delivery_retries_only_failed_chunk_and_resumes(db, monkeypatch):
    monkeypatch.setattr(report.vr, "to_messages", lambda _: ["one", "two", "three"])
    attempts = []

    def send(text):
        attempts.append(text)
        if text == "two":
            raise OSError(TOKEN)

    assert report.run_send(db, NOW, DAY, send, sleep=lambda _: None) == 1
    assert attempts == ["one", "two", "two", "two"]
    assert vs.get_meta(db, "last_report_failed") == DAY.isoformat()
    assert TOKEN not in db.execute("SELECT detail FROM events").fetchone()[0]
    resumed = []
    assert report.run_send(db, NOW, DAY, resumed.append) == 0
    assert resumed == ["two", "three"]
    assert vs.get_meta(db, "last_report_failed") == ""


def test_new_day_announces_failed_report(db):
    def broken(_):
        raise OSError("offline")

    report.run_send(db, NOW, DAY, broken, sleep=lambda _: None)
    sent = []
    report.run_send(db, NOW + 86400, date(2026, 10, 5), sent.append)
    assert "04.10" in sent[0] and "не был доставлен" in sent[0]


def test_concurrent_sender_cannot_deliver(db):
    path = db.execute("PRAGMA database_list").fetchone()[2]
    result = []

    def competing():
        other = vs.open_db(path)
        try:
            result.append(report.run_send(other, NOW, DAY, lambda _: result.append("duplicate")))
        finally:
            other.close()

    def send(_):
        worker = threading.Thread(target=competing)
        worker.start()
        worker.join(timeout=3)
        assert not worker.is_alive()

    assert report.run_send(db, NOW, DAY, send) == 0
    assert result == [1]


def test_interruption_releases_lock_preserves_confirmed_chunk(db, monkeypatch):
    monkeypatch.setattr(report.vr, "to_messages", lambda _: ["one", "two"])

    def interrupted(text):
        if text == "two":
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        report.run_send(db, NOW, DAY, interrupted)
    sent = []
    assert report.run_send(db, NOW, DAY, sent.append) == 0
    assert sent == ["two"]


def test_stdout_needs_no_credentials_or_network(db, monkeypatch, capsys):
    path = db.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setattr(report, "read_env", lambda _: pytest.fail("credentials read"))
    assert report.main(["--stdout", "--db", path, "--day", DAY.isoformat()]) == 0
    assert "04.10" in capsys.readouterr().out


def test_test_mode_does_not_create_database(tmp_path, monkeypatch):
    path = tmp_path / "unused.db"
    sent = []
    monkeypatch.setattr(report, "_configured_send", lambda _: sent.append)
    assert report.main(["--test", "--db", str(path)]) == 0
    assert sent == [report.TEST_TEXT] and not path.exists()


def test_configuration_errors_are_private(tmp_path, capsys):
    path = tmp_path / TOKEN.replace(":", "_")
    assert report.main(["--test", "--env", str(path)]) == 1
    assert str(path) not in capsys.readouterr().err


def test_budget_defers_remaining_chunks_without_truncation(db, monkeypatch):
    monkeypatch.setattr(report.vr, "to_messages", lambda _: ["one", "two", "three"])
    clock = [100.0]
    monkeypatch.setattr(report.time, "monotonic", lambda: clock[0])
    sent = []

    def slow(text):
        sent.append(text)
        clock[0] += 120

    assert report.run_send(db, NOW, DAY, slow) == 1
    assert sent == ["one", "two"]
    resumed = []
    assert report.run_send(db, NOW, DAY, resumed.append) == 0
    assert resumed == ["three"]


def test_retry_does_not_sleep_past_budget(monkeypatch):
    monkeypatch.setattr(report.time, "monotonic", lambda: 100)
    pauses = []

    def fail():
        raise OSError()

    assert report.with_retries(fail, pauses.append, deadline=125) == (
        False, "delivery budget exhausted")
    assert pauses == []
```

- [ ] **Step 2: confirm the tests fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_report_send.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'report'`

- [ ] **Step 3: implementation**

`services/vpn_monitor/report.py`:
```python
#!/usr/bin/env python3
"""Daily VPN report delivery. Confirmed chunks survive retries and restarts.

Telegram has no idempotency key: a lost acknowledgement can still duplicate a
message. The OS lock prevents concurrent local senders, not that remote ambiguity.
"""
import argparse
from contextlib import contextmanager
from datetime import date
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import vpnmon_query as vq
import vpnmon_render as vr
import vpnmon_store as vs

DB_PATH = "/var/lib/nasa-vpnmon/vpnmon.db"
ENV_PATH = "/etc/nasa-vpnmon/telegram.env"
HTTP_TIMEOUT = 10
RETRY_PAUSES = (30, 60)
SEND_BUDGET = 240  # Leave 60 seconds for systemd shutdown/bookkeeping.
TEST_TEXT = "<pre>🧪 nasa-vpnmon: проверка канала. Отчёт приходит в 10:00 МСК.</pre>"


def read_env(path):
    """Read a local config (or stdin with '-'); never evaluate shell syntax."""
    if path == "-":
        return _env_lines(sys.stdin)
    with open(path, encoding="utf-8") as source:
        return _env_lines(source)


def _env_lines(source):
    out = {}
    for raw in source:
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            out[key.strip()] = value
    return out


def _error(exc):
    # Exception strings may contain the request URL/token, response text or PII.
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTPError: %d" % exc.code
    return type(exc).__name__


def send_message(token, chat_id, text, opener=urllib.request.urlopen):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text,
                                   "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode("utf-8")
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token, data=data)
    try:
        with opener(req, timeout=HTTP_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise RuntimeError("Telegram rejected message")
    except (OSError, ValueError, RuntimeError) as exc:
        raise RuntimeError(_error(exc)) from None


def with_retries(action, sleep=time.sleep, pauses=RETRY_PAUSES, deadline=None):
    error = None
    for pause in (0,) + tuple(pauses):
        if deadline is not None and time.monotonic() + pause + HTTP_TIMEOUT > deadline:
            return False, "delivery budget exhausted"
        if pause:
            sleep(pause)
        try:
            action()
            return True, None
        except (OSError, ValueError, RuntimeError) as exc:
            error = _error(exc)
    return False, error


def deliver(messages, send, sleep=time.sleep):
    for text in messages:
        ok, error = with_retries(lambda t=text: send(t), sleep)
        if not ok:
            return False, error
    return True, None


def _lock_file(db):
    path = db.execute("PRAGMA database_list").fetchone()[2]
    if not path:
        raise ValueError("delivery requires a file-backed database")
    return path + ".report.lock"


def _lock(handle, unlock=False):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        mode = msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK
        msvcrt.locking(handle.fileno(), mode, 1)
    else:
        import fcntl
        mode = fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB
        fcntl.flock(handle.fileno(), mode)


@contextmanager
def _sender_lock(db):
    fd = os.open(_lock_file(db), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        try:
            _lock(handle)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            _lock(handle, unlock=True)


def _pending(db, now, day, force):
    key = "report_progress:" + day.isoformat()
    saved = vs.get_meta(db, key)
    if saved and not force:
        return key, json.loads(saved)
    pending = {"messages": vr.to_messages(vr.render(vq.build_report(db, day, now))), "next": 0}
    with db:
        vs.set_meta(db, key, json.dumps(pending, ensure_ascii=False))
    return key, pending


def _send_pending(db, key, pending, send, sleep, deadline):
    while pending["next"] < len(pending["messages"]):
        text = pending["messages"][pending["next"]]
        ok, error = with_retries(lambda: send(text), sleep, deadline=deadline)
        if not ok:
            return False, error
        pending["next"] += 1
        with db:
            vs.set_meta(db, key, json.dumps(pending, ensure_ascii=False))
    return True, None


def _finish(db, now, day, key, ok, error):
    with db:
        if ok:
            vs.set_meta(db, "last_report_day", day.isoformat())
            vs.set_meta(db, "report_sent:" + day.isoformat(), "1")
            vs.set_meta(db, "last_report_failed", "")
            db.execute("DELETE FROM meta WHERE key=?", (key,))
            vs.purge_old(db, now)
        else:
            vs.set_meta(db, "last_report_failed", day.isoformat())
            vs.add_event(db, now, "report_failed", {"day": day.isoformat(), "error": error})


def _run_locked(db, now, day, send, force, sleep):
    sent = vs.get_meta(db, "report_sent:" + day.isoformat())
    if not force and (sent or vs.get_meta(db, "last_report_day") == day.isoformat()):
        print("отчёт за %s уже отправлен" % day.isoformat())
        return 0
    key, pending = _pending(db, now, day, force)
    deadline = time.monotonic() + SEND_BUDGET
    ok, error = _send_pending(db, key, pending, send, sleep, deadline)
    _finish(db, now, day, key, ok, error)
    print("отправлено" if ok else "не доставлено: %s" % error,
          file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def run_send(db, now, day, send, force=False, sleep=time.sleep):
    """One local sender at a time, durable cursor for acknowledged chunks."""
    with _sender_lock(db) as acquired:
        if not acquired:
            print("отправка уже выполняется", file=sys.stderr)
            return 1
        return _run_locked(db, now, day, send, force, sleep)


def _parse_args(argv):
    ap = argparse.ArgumentParser(description="Суточный отчёт VPN/VPS в Telegram")
    mode = ap.add_mutually_exclusive_group(required=True)
    for option in ("stdout", "send", "test"):
        mode.add_argument("--" + option, action="store_true")
    ap.add_argument("--day", type=date.fromisoformat)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--env", default=ENV_PATH, help="local config path, or '-' for stdin")
    return ap.parse_args(argv)


def _configured_send(path):
    env = read_env(path)
    token, chat_id = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("missing Telegram configuration")
    return lambda text: send_message(token, chat_id, text)


def _main(args):
    if args.test:
        send = _configured_send(args.env)
        ok, error = with_retries(lambda: send(TEST_TEXT))
        print("проверка: доставлено" if ok else "проверка: не доставлено — %s" % error)
        return 0 if ok else 1
    now = time.time()
    day = args.day or vq.report_day(now)
    db = vs.open_db(args.db)
    try:
        if args.stdout:
            print(vr.render(vq.build_report(db, day, now)))
            return 0
        return run_send(db, now, day, _configured_send(args.env), args.force)
    finally:
        db.close()


def main(argv=None):
    args = _parse_args(argv)
    os.umask(0o077)
    try:
        return _main(args)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print("ошибка отчёта: %s" % _error(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: confirm the tests pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: all tests PASS (tasks 1–5)

- [ ] **Step 5: commit**

```bash
git add services/vpn_monitor/report.py tests/vpn_monitor/test_report_send.py
git commit -m "feat(vpnmon): Telegram delivery with retries and once-per-day guard" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: units, installer, examples and the rule-13 snapshot

**Files:**
- Create: `services/vpn_monitor/systemd/nasa-vpnmon-collect.service`, `…-collect.timer`, `…-report.service`, `…-report.timer`
- Create: `services/vpn_monitor/install_vps.sh`, `services/vpn_monitor/rule13_snapshot.sh`
- Create: `services/vpn_monitor/names.conf.example`, `services/vpn_monitor/telegram.env.example`
- Create: `tests/vpn_monitor/test_deploy.py`

**Interfaces:**
- Consumes: `report.HTTP_TIMEOUT`, `report.RETRY_PAUSES` (task 5); the list of modules `services/vpn_monitor/*.py`.
- Produces: the files for task 8.

- [ ] **Step 1: failing tests**

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
    for line in ("Type=oneshot", "CPUQuota=20%", "MemoryMax=64M", "Nice=10", "TimeoutStartSec=50",
                 "ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/collect.py"):
        assert line in s, line


def test_collect_timeout_exceeds_subprocess_budget():
    import collect
    s = text("systemd", "nasa-vpnmon-collect.service")
    timeout = int(re.search(r"TimeoutStartSec=(\d+)", s).group(1))
    assert 4 * collect.EXEC_TIMEOUT < timeout < 60  # inspect×2 + exec + journalctl; меньше интервала


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
    assert set(re.findall(r"docker\s+(\w+)", s)) == {"inspect"}
    assert "ss -tlnuH" in s
    assert "docker exec" not in s and "wg show" not in s
```

- [ ] **Step 2: confirm the tests fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor/test_deploy.py`
Expected: FAIL with `FileNotFoundError` on `systemd/nasa-vpnmon-collect.service`

- [ ] **Step 3: units**

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
TimeoutStartSec=50
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

- [ ] **Step 4: installer, snapshot, examples**

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

[ "$(id -u)" -eq 0 ] || { echo "нужен root" >&2; exit 1; }
for f in collect.py report.py vpnmon_parse.py vpnmon_store.py vpnmon_query.py vpnmon_render.py \
         systemd/nasa-vpnmon-collect.service systemd/nasa-vpnmon-collect.timer \
         systemd/nasa-vpnmon-report.service systemd/nasa-vpnmon-report.timer names.conf.example; do
  [ -f "$HERE/$f" ] || { echo "неполный установочный комплект: $f" >&2; exit 1; }
done

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
# Число клиентов владелец сверяет в Amnezia Desktop; команды внутри VPN не выполняются.
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

- [ ] **Step 5: confirm the tests and the gates pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/vpn_monitor`
Expected: all tests PASS
Run: `bash scripts/quality/preflight.sh` (Git Bash, `.venv/Scripts` in PATH)
Expected: `ВОРОТА ПРОЙДЕНЫ` (gates passed); section 1 sees the two new `.sh` files; section 10 (ratchet) reports no violations

- [ ] **Step 6: commit**

```bash
git add services/vpn_monitor/systemd services/vpn_monitor/install_vps.sh services/vpn_monitor/rule13_snapshot.sh services/vpn_monitor/names.conf.example services/vpn_monitor/telegram.env.example tests/vpn_monitor/test_deploy.py
git commit -m "feat(vpnmon): systemd units, installer and rule-13 snapshot" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: runbook, CHANGELOG, English pairs (DeepSeek executor)

**Files:**
- Create: `docs/plans/DEPLOY_VPNMON_2026-10.ru.md` and the pair `docs/plans/DEPLOY_VPNMON_2026-10.md`. Content — the steps of task 8 of this plan verbatim, commands unchanged, plus a "Rollback" section.
- Create: `docs/superpowers/plans/2026-10-04-vps-vpn-monitor.en.md`. This is not the project's `X.md`/`X.ru.md` format: the Russian plan already lives as `X.md`, and renaming would break links. Therefore the English pair gets the `.en.md` suffix. Full translation.
- Change: `CHANGELOG.md` — an entry under "Unreleased": "VPS/VPN monitor: one-minute read-only collector and daily 10:00 MSK Telegram report (spec 2026-10-04)".

The `ds-worker` card, `needs_edit: true`, `base` — the last commit of task 6. Peer keys, names and tokens are not put into the card. The lead accepts the work by cross-checking: the number of sections matches, all commands from task 8 are present verbatim, and the EN files contain no Cyrillic.

- [ ] **Step 1:** write and run the card (`ds-worker new` → `ds-worker run`)
- [ ] **Step 2:** accept by the check above (`ds-worker review --accept`) and merge the executor's commit into the branch (`git merge --ff-only deepseek/<task_id>`)

---

### Task 8: rollout to the VPS (lead only, after the owner says «деплой»)

A critical zone (rule №16): neither a subagent nor DeepSeek performs this task. The commands are run from the workstation. `VPS` below means `root@95.163.176.103` with the key `~/.ssh/borovskoy_new_ed25519`.

- [ ] **Step 1: the code on the VPS, into a temporary directory**

```bash
cd "e:/Linux mint/virtual_VM/shared/NAS_Jetson_Nano"
tar -C services --exclude=__pycache__ -czf - vpn_monitor | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'umask 077; test ! -e /root/vpnmon-src && mkdir /root/vpnmon-src && tar -C /root/vpnmon-src -xzf - && ls /root/vpnmon-src/vpn_monitor'
```

- [ ] **Step 2: rule 13 snapshot "before"**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | tee /root/vpnmon-rule13-before.txt'
```
Expected: `amnezia-awg2`/`amnezia-xray` running, peer count = owner baseline; among the listeners exposed outward (`0.0.0.0`/`[::]`) only 22, 443, 40568/udp and the previous service ports.

- [ ] **Step 3: trial sample with no write, cross-checked against `wg`**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'cd /root/vpnmon-src/vpn_monitor && python3 collect.py --dry-run --names /nonexistent; echo ---; docker exec amnezia-awg2 wg show awg0 transfer | sort -k3 -n | tail -3 | cut -c1-8,44-'
```
Expected: `peers=21`; for the top three by `tx` the values match `wg show` (allowing for the seconds between the commands); `awg: rx=… tx=…`, `wan`, `xray` are not "нет".

- [ ] **Step 4: installation**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/install_vps.sh'
```
Expected: `nasa-vpnmon-collect.timer` appears in the timer list; the message "таймер отчёта НЕ включён" (no token yet).

- [ ] **Step 5: `names.conf` — six unnamed peers**

From the output of step 3, take the key prefixes for `10.8.1.17` (Vostro) and `10.8.1.18`–`.22` («запасной-1»…«запасной-5» in ascending address order) and write them on the VPS. The values never get into git.
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
The lead replaces the `<префикс …>` placeholders with the real prefixes from step 3 at execution time.

- [ ] **Step 6: the token from the Jetson to the VPS without printing it**

From the workstation, from the home network (rule №17). First check that the file is in place on the Jetson:
```bash
ssh admin@192.168.0.50 'ls -l /etc/nasa-monitor/telegram.env'
```
Then transfer the two lines through a pipeline: the value goes from the Jetson's stdout to the VPS's stdin and is never printed anywhere.
```bash
set -o pipefail
ssh -o BatchMode=yes admin@192.168.0.50 'sudo -n grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /etc/nasa-monitor/telegram.env' \
  | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'set -e; umask 077; tmp=$(mktemp /etc/nasa-vpnmon/telegram.env.XXXXXX); trap '\''rm -f "$tmp"'\'' EXIT; cat > "$tmp"; grep -q "^TELEGRAM_BOT_TOKEN=." "$tmp"; grep -q "^TELEGRAM_CHAT_ID=." "$tmp"; chmod 600 "$tmp"; mv "$tmp" /etc/nasa-vpnmon/telegram.env; echo 2'
```
Expected: `2`.

- [ ] **Step 7: test message and enabling the report**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 /usr/local/lib/nasa-vpnmon/report.py --test && systemctl enable --now nasa-vpnmon-report.timer && systemctl list-timers --all "nasa-vpnmon-*" --no-pager'
```
Expected: `проверка: доставлено`; the owner sees the 🧪 message; the next report run — 10:00 MSK.

- [ ] **Step 8: after 5 minutes — data in the DB and resource usage**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 -c "import sqlite3; d=sqlite3.connect(\"/var/lib/nasa-vpnmon/vpnmon.db\"); print(\"host\", d.execute(\"select count(*), sum(samples) from host_hourly\").fetchone(), \"peers\", d.execute(\"select count(*) from peers\").fetchone())"; systemctl show nasa-vpnmon-collect.service -p CPUUsageNSec -p MemoryPeak -p Result; journalctl -u nasa-vpnmon-collect -n 5 --no-pager; ls -l /var/lib/nasa-vpnmon /etc/nasa-vpnmon'
```
Expected: `peers (21,)`, `samples` ≥ 4; `Result=success`; `MemoryPeak` < 64 MB; files 0600, directories 0700.

- [ ] **Step 9: the report for the current day to screen**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 /usr/local/lib/nasa-vpnmon/report.py --stdout --day $(TZ=Europe/Moscow date +%F)'
```
Expected: all blocks of the §7 layout; the six peers named via `names.conf`; "Не подключались с ДД.ММ" — today's date.

- [ ] **Step 10: rule 13 snapshot "after"**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | diff /root/vpnmon-rule13-before.txt - && echo "правило 13: без изменений"'
```
Expected: `правило 13: без изменений`. Any difference — stop, roll back (below) and investigate.

- [ ] **Step 11: documentation and publication**

- Merge the branch `feat/vpn-monitor-2026-10` into `main` (`git merge --ff-only`) and publish per the rule №15 procedure.
- `CLAUDE.md` + `CLAUDE.en.md`: a table row for VPN accounting (units, report time); peers **21** (measured 04.10); VPS downtime 04.10 04:55–05:27 UTC; a new checkpoint.
- No family announcement is needed: only the owner sees the report (rule №18 concerns what the family can see).

- [ ] **Step 12: the next day at 10:00 MSK**

The real report has arrived; the owner confirms. If the owner wishes — a volume cross-check: download 100 MB through the VPN on a known device, then `report.py --stdout --day <today>` shows a growth of about 100 MB (±5 %) for that client.

**Rollback** (VPN untouched, verified by the rule 13 snapshot before and after):
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'systemctl disable --now nasa-vpnmon-collect.timer nasa-vpnmon-report.timer; systemctl stop nasa-vpnmon-collect.service nasa-vpnmon-report.service'
```
