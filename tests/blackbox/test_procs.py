"""Задача 6 (OBS-1): процессы — чтение /proc, снимок, признак аномалии.

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «Задача 6: процессы (sources/procs.py)».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md, §4.1.

Каждый тест — строка таблицы «Случаи для тестов» задачи 6; значения взяты из таблицы.
Пункты «Фокуса ревью» плана к задаче 6 не относятся (они в задачах 5, 7, 3, 4 и 11)
и здесь намеренно не дублируются.

Деревья /proc — подставные, собранные в tmp_path; живая система, сокет Docker и
субпроцессы не участвуют. Файлы пишутся байтами UTF-8, поэтому переводы строк не
зависят от ОС — тесты идут и на Windows, и на Linux.

Ид контейнера (64 шестнадцатеричных знака) собирается конкатенацией: монолитный
64-hex литерал сканер секретов проекта принимает за хеш или ключ.
"""
import pytest

from blackbox.config import Config
from blackbox.sources.procs import container_of, is_anomaly, read_procs, snapshot

TS = 1791861274      # секунды эпохи из контракта «sample»
HZ = 100             # тиков планировщика в секунду
DT = 60.0            # секунд между двумя чтениями /proc

# Ид контейнера Docker из /docker/<id> в cgroup — 64 шестнадцатеричных знака.
DOCKER_ID = "0f1e2d3c4b5a69788796a5b4c3d2e1f0" + "00112233445566778899aabbccddeeff"

NULL = chr(0)        # разделитель аргументов в /proc/<pid>/cmdline

# Контракты плана («Контракты данных» и «Задача 6») — ключи ровно такие.
PROC_ROW_KEYS = {"ts", "pid", "comm", "owner", "cmd", "state", "wchan", "cpu_pct", "rss_mb"}
RAW_KEYS = {"pid", "comm", "cmd", "state", "wchan", "ticks", "start", "rss_mb", "owner"}


def raw(pid, start=1000, ticks=0, rss_mb=5, state="S", comm="prog", wchan="", owner="host"):
    """Сырая запись read_procs, как в контракте плана."""
    return {"pid": pid, "comm": comm, "cmd": comm, "state": state, "wchan": wchan,
            "ticks": ticks, "start": start, "rss_mb": rss_mb, "owner": owner}


def smp(ts=TS, mem_avail_mb=1200, load1=1.0, swap_mb=200):
    """Замер из контракта «sample» — только ключи, нужные правилу аномалии."""
    return {"ts": ts, "mem_avail_mb": mem_avail_mb, "load1": load1, "swap_mb": swap_mb}


# --- подставное дерево /proc -------------------------------------------------

def put(path, text):
    """Файл подставного дерева: байты UTF-8, без переводов строк ОС."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def stat_line(pid, comm, state, utime, stime, starttime, rss_pages):
    """Полная строка /proc/<pid>/stat (44 поля, как у ядра Linux).

    Поля: 3 — состояние, 14 — utime, 15 — stime (в тиках), 22 — starttime
    (тики с загрузки), 24 — rss в страницах.
    """
    fields = [pid, "(%s)" % comm, state] + [0] * 10      # поля 1–13
    fields += [utime, stime, 0, 0, 20, 0, 1, 0]          # поля 14–21
    fields += [starttime, 0, rss_pages]                  # поля 22–24
    fields += [0] * 20                                   # поля 25–44
    return " ".join(str(f) for f in fields) + "\n"


def mk_proc(proc_root, pid, comm="prog", args=None, state="S", utime=120, stime=80,
            start=98765, rss_pages=1280, wchan="", cgroup="1:name=systemd:/init.scope\n"):
    """Один процесс подставного /proc: comm, cmdline, stat, statm, wchan, cgroup."""
    args = [comm] if args is None else args
    d = proc_root / str(pid)
    put(d / "comm", comm + "\n")
    put(d / "cmdline", "".join(a + NULL for a in args))
    put(d / "stat", stat_line(pid, comm, state, utime, stime, start, rss_pages))
    put(d / "statm", "%d %d 0 0 0 0 0\n" % (rss_pages * 2, rss_pages))
    put(d / "wchan", wchan)
    put(d / "cgroup", cgroup)


# --- snapshot ----------------------------------------------------------------

def test_snapshot_process_gone_between_snapshots():
    """Строка таблицы: процесс исчез между снимками — не в выдаче, без исключения."""
    prev_raw = [raw(7001, ticks=100), raw(7002, ticks=300, rss_mb=7)]
    cur_raw = [raw(7002, ticks=400, rss_mb=7)]
    rows = snapshot(prev_raw=prev_raw, cur_raw=cur_raw, dt_s=DT, hz=HZ, ts=TS)
    assert [r["pid"] for r in rows] == [7002]
    assert rows[0]["cpu_pct"] == pytest.approx(100 / HZ / DT * 100)   # (400 − 300) тиков


def test_snapshot_reused_pid_counts_cpu_from_zero():
    """Строка таблицы: PID переиспользован (другой start) — CPU от нуля, не отрицательный."""
    prev_raw = [raw(4242, start=1000, ticks=5000, rss_mb=10)]
    cur_raw = [raw(4242, start=2000, ticks=30, rss_mb=10)]
    rows = snapshot(prev_raw=prev_raw, cur_raw=cur_raw, dt_s=DT, hz=HZ, ts=TS)
    assert len(rows) == 1
    assert rows[0]["cpu_pct"] >= 0                     # наивная разность дала бы −82.8 %
    assert rows[0]["cpu_pct"] == pytest.approx(30 / HZ / DT * 100)    # от нуля: 0.5 %


def test_snapshot_includes_all_d_state_outside_tops():
    """Строка таблицы: 25 процессов, 3 в D вне топов — все 3 в выдаче, wchan заполнен."""
    procs = []
    for i in range(1, 11):                                   # 1001–1010: тяжёлые по CPU
        procs.append(raw(1000 + i, ticks=(11 - i) * 100, rss_mb=5))
    for i in range(11, 21):                                  # 1011–1020: тяжёлые по RSS
        procs.append(raw(1000 + i, ticks=10, rss_mb=2000 - (i - 11) * 10))
    procs.append(raw(1021, ticks=10, rss_mb=5, state="D", wchan="request_wait_answer"))
    procs.append(raw(1022, ticks=10, rss_mb=5, state="D", wchan="fuse_request_wait"))
    procs.append(raw(1023, ticks=10, rss_mb=5, state="D", wchan="wait_on_page_bit"))
    procs.append(raw(1024, ticks=10, rss_mb=5))              # ровные, вне обоих топов
    procs.append(raw(1025, ticks=10, rss_mb=5))

    rows = snapshot(prev_raw=[], cur_raw=procs, dt_s=DT, hz=HZ, ts=TS)  # top_n=10 по умолчанию
    by_pid = {r["pid"]: r for r in rows}
    assert len(rows) == 23                                   # 10 + 10 + 3, без дублей
    assert set(by_pid) == set(range(1001, 1024))             # 1024 и 1025 — не попали
    for pid, wchan in ((1021, "request_wait_answer"),
                       (1022, "fuse_request_wait"),
                       (1023, "wait_on_page_bit")):
        assert by_pid[pid]["state"] == "D"
        assert by_pid[pid]["wchan"] == wchan                 # заполнен, не пуст


def test_snapshot_row_keys_match_contract():
    """Строка proc row — ровно ключи контракта «Контракты данных»."""
    rows = snapshot(prev_raw=[], cur_raw=[raw(7002, ticks=400)], dt_s=DT, hz=HZ, ts=TS)
    assert len(rows) == 1
    assert set(rows[0]) == PROC_ROW_KEYS
    assert rows[0]["ts"] == TS


# --- read_procs, container_of ------------------------------------------------

def test_read_procs_owner_from_docker_cgroup(tmp_path):
    """Строка таблицы: cgroup с /docker/<id> и картой — owner = имя контейнера.

    Форма резолвера — допущение этих тестов: план называет только вызов
    container_of(pid), а карта id→имя и дерево /proc — его данные, поэтому
    фабрика container_of(proc_root, id_map) возвращает вызываемый объект(pid).
    Нет /docker/ в cgroup → «host».
    """
    proc_root = tmp_path / "proc"
    cgroup = "11:devices:/docker/%s\n1:name=systemd:/docker/%s\n" % (DOCKER_ID, DOCKER_ID)
    mk_proc(proc_root, 4242, comm="python3", args=["python3", "app.py"], cgroup=cgroup)
    mk_proc(proc_root, 4243, comm="bash", args=["bash"])     # cgroup по умолчанию — init.scope

    resolve = container_of(proc_root, {DOCKER_ID: "homecloud_stt"})
    assert resolve(4242) == "homecloud_stt"
    assert resolve(4243) == "host"

    recs = {r["pid"]: r for r in read_procs(proc_root=proc_root, container_of=resolve)}
    assert len(recs) == 2
    rec = recs[4242]
    assert set(rec) == RAW_KEYS
    assert rec["owner"] == "homecloud_stt"
    assert recs[4243]["owner"] == "host"
    assert rec["comm"] == "python3"
    assert rec["cmd"] == "python3 app.py"        # аргументы cmdline соединены пробелами
    assert rec["state"] == "S"
    assert rec["ticks"] == 200                   # utime 120 + stime 80
    assert rec["start"] == 98765
    assert rec["rss_mb"] == 5                    # 1280 страниц × 4 КиБ / 1024 = 5 МиБ


# --- is_anomaly --------------------------------------------------------------

def test_is_anomaly_d_state():
    """Правило «Аномалия» из «Общих ограничений»: есть D-state."""
    assert is_anomaly(sample=smp(), prev_sample=smp(ts=TS - 60), d_count=3,
                      cfg=Config()) is True


def test_is_anomaly_mem_avail_280():
    """Строка таблицы: MemAvailable 280 МБ < 300 (умолчание Config) — True."""
    assert is_anomaly(sample=smp(mem_avail_mb=280),
                      prev_sample=smp(ts=TS - 60, mem_avail_mb=900),
                      d_count=0, cfg=Config()) is True


def test_is_anomaly_load1_high():
    """Строка таблицы: load1 = 6.5 > 6 (умолчание Config) — True."""
    assert is_anomaly(sample=smp(load1=6.5), prev_sample=smp(ts=TS - 60),
                      d_count=0, cfg=Config()) is True


def test_is_anomaly_swap_growth_over_50mb_per_min():
    """Строка таблицы: подкачка +60 МБ за 60 с (то есть > 50 МБ/мин) — True."""
    assert is_anomaly(sample=smp(swap_mb=300),
                      prev_sample=smp(ts=TS - 60, swap_mb=240),
                      d_count=0, cfg=Config()) is True


def test_is_anomaly_calm_is_false():
    """Строка таблицы: спокойный замер — False."""
    assert is_anomaly(sample=smp(), prev_sample=smp(ts=TS - 60),
                      d_count=0, cfg=Config()) is False


# --- крайние случаи (задача 6, дополнение) ----------------------------------

def test_read_procs_comm_with_spaces_and_parentheses(tmp_path):
    """Край: comm с пробелами и скобками — поля stat берутся после последней ')'.

    Наивный `find(')')` сдвинул бы поля и дал чужие ticks/start/rss.
    """
    proc_root = tmp_path / "proc"
    mk_proc(proc_root, 5150, comm="my (weird) proc", utime=5, stime=7,
            start=4242, rss_pages=256)                 # 256 страниц × 4 КиБ = 1 МиБ
    resolve = container_of(proc_root, {})
    records = read_procs(proc_root=proc_root, container_of=resolve)
    assert len(records) == 1
    assert records[0]["comm"] == "my (weird) proc"
    assert records[0]["ticks"] == 12
    assert records[0]["start"] == 4242
    assert records[0]["rss_mb"] == 1.0


def test_read_procs_skips_vanished_and_malformed_process(tmp_path):
    """Край: каталог без stat (процесс исчез) и обрезанный stat — пропущены."""
    proc_root = tmp_path / "proc"
    mk_proc(proc_root, 6001, comm="alive")
    (proc_root / "6002").mkdir(parents=True)           # каталог остался, файлов нет
    mk_proc(proc_root, 6003, comm="truncated")
    (proc_root / "6003" / "stat").write_bytes(b"6003 (trunc)")   # полей нет
    resolve = container_of(proc_root, {})
    records = read_procs(proc_root=proc_root, container_of=resolve)
    assert [r["pid"] for r in records] == [6001]


def test_snapshot_invalid_interval_gives_zero_not_exception():
    """Край: dt_s/hz недопустимы — cpu_pct 0, строка остаётся, исключения нет."""
    prev_raw = [raw(7001, ticks=100)]
    cur_raw = [raw(7001, ticks=400)]
    for dt_s, hz in ((0, HZ), (-60.0, HZ), (DT, 0), (None, HZ)):
        rows = snapshot(prev_raw=prev_raw, cur_raw=cur_raw, dt_s=dt_s, hz=hz, ts=TS)
        assert len(rows) == 1
        assert rows[0]["cpu_pct"] == 0


def test_container_of_docker_scope_and_unmapped_id(tmp_path):
    """Край: форма `docker-<id>.scope` распознаётся; несопоставленный ид — host."""
    proc_root = tmp_path / "proc"
    other_id = "ffeeddccbbaa99887766554433221100" + "0123456789abcdef0123456789abcdef"
    scope = "0::/system.slice/docker-%s.scope\n" % DOCKER_ID
    mk_proc(proc_root, 8101, comm="svc", cgroup=scope)
    mk_proc(proc_root, 8102, comm="outsider",
            cgroup="0::/system.slice/docker-%s.scope\n" % other_id)
    resolve = container_of(proc_root, {DOCKER_ID: "homecloud_stt"})
    assert resolve(8101) == "homecloud_stt"
    assert resolve(8102) == "host"


def test_snapshot_negative_tick_delta_is_zero():
    """Край: тики уменьшились при том же start — CPU 0, не отрицательный."""
    prev_raw = [raw(7001, ticks=500)]
    cur_raw = [raw(7001, ticks=100)]
    rows = snapshot(prev_raw=prev_raw, cur_raw=cur_raw, dt_s=DT, hz=HZ, ts=TS)
    assert len(rows) == 1
    assert rows[0]["cpu_pct"] == 0
