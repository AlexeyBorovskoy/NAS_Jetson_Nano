"""Read-only evidence assembly for the OBS-1 why CLI."""
import datetime
import json
import os
import sqlite3
import subprocess
import time
from urllib.parse import quote

from blackbox.collector_events import serialized_size
from blackbox.why.rules import Evidence
from .archive_read import extract_day
from .journal_read import normalize_line, read_container_log, read_journal

MAX_SNAPSHOTS = 16
MAX_DAYS = 366
MAX_QUERY_ROWS = 20000
MAX_QUERY_BYTES = 4 << 20
MAX_QUERY_ROW_BYTES = 16 << 10
MAX_EVIDENCE_ROWS = 50000
MAX_EVIDENCE_BYTES = 24 << 20
MAX_EVIDENCE_ROW_BYTES = 16 << 10


def _ro(path):
    if not os.path.isfile(path) or os.path.islink(path):
        return None
    uri = "file:%s?mode=ro" % quote(os.path.abspath(path), safe="/:\\")
    try:
        return sqlite3.connect(uri, uri=True, timeout=1)
    except sqlite3.Error:
        return None


def _tables(conn):
    try:
        return set(row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"))
    except sqlite3.Error:
        return set()


def _query(conn, sql, params=()):
    if conn is None:
        return None
    try:
        return _bounded_fetch(conn.execute(sql, params))
    except sqlite3.Error:
        return None


def _bounded_fetch(cursor):
    rows = []
    total = 0
    truncated = False
    while len(rows) < MAX_QUERY_ROWS:
        batch = cursor.fetchmany(64)
        if not batch:
            break
        total, truncated = _append_query_batch(rows, batch, total)
        if truncated or len(batch) < 64:
            break
    else:
        truncated = False
    if len(rows) == MAX_QUERY_ROWS and not truncated:
        truncated = cursor.fetchone() is not None
    return _CappedRows(rows, truncated)


def _append_query_batch(rows, batch, total):
    for row in batch:
        size = _row_size(row)
        if len(rows) >= MAX_QUERY_ROWS or size > MAX_QUERY_ROW_BYTES:
            return total, True
        if total + size > MAX_QUERY_BYTES:
            return total, True
        rows.append(row)
        total += size
    return total, False


def _row_size(row):
    size = 0
    for value in row:
        if isinstance(value, str):
            size += len(value.encode("utf-8", "replace"))
        elif isinstance(value, bytes):
            size += len(value)
        else:
            size += len(str(value))
    return size


class _CappedRows(list):
    def __init__(self, rows, truncated):
        super(_CappedRows, self).__init__(rows)
        self.truncated = truncated


def _dict_rows(rows, names):
    return [dict(zip(names, row)) for row in rows or ()]


def _append_rows(data, key, rows):
    remaining_rows = MAX_EVIDENCE_ROWS - _row_count(data)
    remaining_bytes = MAX_EVIDENCE_BYTES - data["_bytes"]
    iterator = iter(rows)
    count = 0
    while count < max(0, remaining_rows) and remaining_bytes > 0:
        try:
            value = next(iterator)
        except StopIteration:
            return
        size = serialized_size(value, min(MAX_EVIDENCE_ROW_BYTES, remaining_bytes))
        if size > MAX_EVIDENCE_ROW_BYTES or size > remaining_bytes:
            data["reasons"].append("evidence byte budget exceeded")
            break
        data[key].append(value)
        data["_bytes"] += size
        remaining_bytes -= size
        count += 1
    if remaining_bytes <= 0:
        data["reasons"].append("evidence byte budget reached")
        return
    if remaining_rows <= 0:
        data["reasons"].append("evidence row budget reached")
        return
    try:
        next(iterator)
    except StopIteration:
        return
    else:
        data["reasons"].append("evidence row budget exceeded")


def _row_count(data):
    fields = ("samples", "disk_samples", "procs", "events", "journal", "snapshots")
    return sum(len(data[name]) for name in fields)


def _evidence_full(data):
    return (_row_count(data) >= MAX_EVIDENCE_ROWS or
            data["_bytes"] >= MAX_EVIDENCE_BYTES)


def _day_names(start, end):
    first = datetime.datetime.utcfromtimestamp(start).date()
    last = datetime.datetime.utcfromtimestamp(end).date()
    count = 0
    while first <= last and count < MAX_DAYS:
        yield first.isoformat()
        first += datetime.timedelta(days=1)
        count += 1


def _read_metrics(path, since, until):
    conn = _ro(path)
    if conn is None:
        return [], [], False, False
    try:
        tables = _tables(conn)
        samples = _query(conn, "SELECT ts,vin_mv,vin_ma,cpu_mw,gpu_mw,t_cpu,t_gpu,t_pmic,t_ao,cpu_pct,freq_mhz,mem_avail_mb,swap_mb,zram_mb,load1x100,net_rx,net_tx FROM sample WHERE ts BETWEEN ? AND ? ORDER BY ts", (since, until)) if "sample" in tables else None
        disks = _query(conn, "SELECT ts,disk_id,rios,wios,rsect,wsect,busy_ms FROM disk_sample WHERE ts BETWEEN ? AND ? ORDER BY ts", (since, until)) if "disk_sample" in tables else None
        return (_decode_samples(samples),
                _dict_rows(disks, ("ts", "disk_id", "rios", "wios", "rsect", "wsect", "busy_ms")),
                samples is not None and disks is not None,
                bool(getattr(samples, "truncated", False) or
                     getattr(disks, "truncated", False)))
    finally:
        conn.close()


def _decode_samples(rows):
    names = ("ts", "vin_mv", "vin_ma", "cpu_mw", "gpu_mw", "t_cpu", "t_gpu", "t_pmic", "t_ao", "cpu_pct", "freq_mhz", "mem_avail_mb", "swap_mb", "zram_mb", "load1x100", "net_rx", "net_tx")
    result = _dict_rows(rows, names)
    for row in result:
        value = row.pop("load1x100")
        row["load1"] = None if value is None else value / 100.0
    return result


def _read_procs(path, since, until):
    conn = _ro(path)
    if conn is None:
        return [], False, False
    try:
        if "proc_snapshot" not in _tables(conn):
            return [], False, False
        cols = "ts,pid,substr(comm,1,16385),substr(owner,1,16385),substr(cmd,1,16385),state,substr(wchan,1,16385),cpu_pct,rss_mb"
        names = ("ts", "pid", "comm", "owner", "cmd", "state", "wchan",
                 "cpu_pct", "rss_mb")
        rows = _query(conn, "SELECT %s FROM proc_snapshot WHERE ts BETWEEN ? AND ? ORDER BY ts" % cols, (since, until))
        return (_dict_rows(rows, names), rows is not None,
                bool(getattr(rows, "truncated", False)))
    finally:
        conn.close()


def _catalog(cfg, ssd_available=None):
    roots = (cfg.fallback_root,) if ssd_available is False else (cfg.ssd_root, cfg.fallback_root)
    found = []
    for root in roots:
        path = os.path.join(root, "catalog.db")
        conn = _ro(path)
        if conn is not None:
            found.append((path, conn))
    return roots, found


def _catalog_rows(conn, since, until, container):
    return (_read_events(conn, since, until, container),
            _read_minutes(conn, since, until), _read_archives(conn, since, until))


def _read_events(conn, since, until, container):
    if "event" not in _tables(conn):
        return []
    sql = "SELECT ts,substr(source,1,16385),substr(kind,1,16385),substr(subject,1,16385),substr(severity,1,16385),substr(detail,1,16385) FROM event WHERE ts BETWEEN ? AND ?"
    args = [since, until]
    if container:
        sql += " AND source='docker' AND subject=?"
        args.append(container)
    rows = _query(conn, sql + " ORDER BY ts", args)
    result = []
    for row in rows or ():
        result.append(_decode_event(row))
    return _CappedRows(result, bool(getattr(rows, "truncated", False)))


def _decode_event(row):
    ts, source, kind, subject, severity, detail = row
    try:
        detail = json.loads(detail or "{}")
    except ValueError:
        detail = {}
    return {"ts": ts, "source": source, "kind": kind, "subject": subject,
            "severity": severity, "detail": detail}


def _read_minutes(conn, since, until):
    if "minute" not in _tables(conn):
        return []
    result = []
    rows = _query(conn, "SELECT ts,substr(data,1,16385) FROM minute WHERE ts BETWEEN ? AND ? ORDER BY ts", (since, until))
    for ts, data in rows or ():
        try:
            row = json.loads(data)
        except ValueError:
            return _CappedRows(result, True)
        row["ts"] = ts
        result.append(row)
    return _CappedRows(result, bool(getattr(rows, "truncated", False)))


def _read_archives(conn, since, until):
    if "archive" not in _tables(conn):
        return []
    sql = "SELECT week,substr(path,1,4096),substr(sha256,1,128),first_day,last_day,created,verified FROM archive WHERE first_day<=? AND last_day>=? LIMIT 366"
    rows = _query(conn, sql, (_utc_day(until), _utc_day(since)))
    return rows or []


def _utc_day(ts):
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")


def _archive_row(rows, day):
    for row in rows:
        if row[4] >= day and row[3] <= day:
            return dict(zip(("week", "path", "sha256", "first_day", "last_day", "created", "verified"), row))
    return None


def _read_day(cfg, day, since, until, archives, data, container=None,
              ssd_available=None):
    if ssd_available is True and not os.path.ismount(cfg.ssd_mount):
        data["reasons"].append("SSD mount disappeared; storage evidence skipped")
        return
    hot, temp = _resolve_day(cfg, day, archives, data, ssd_available)
    if hot is None:
        return
    metrics = os.path.join(hot, "metrics.db")
    procs = os.path.join(hot, "procs.db")
    try:
        _append_day_data(metrics, procs, since, until, data)
        _read_day_journals(hot, "", since, until, data, container)
        if temp:
            _read_day_journals(temp, "", since, until, data, container)
    except (OSError, ValueError, sqlite3.Error):
        data["reasons"].append("day evidence unavailable")
    finally:
        if temp:
            import shutil
            shutil.rmtree(temp, ignore_errors=True)


def _resolve_day(cfg, day, archives, data, ssd_available=None):
    hot = os.path.join(cfg.ssd_root, "hot", day)
    metrics, procs = os.path.join(hot, "metrics.db"), os.path.join(hot, "procs.db")
    if os.path.isfile(metrics) or os.path.isfile(procs) or os.path.isdir(hot):
        return hot, None
    row = _archive_row(archives, day)
    if row is None:
        return None, None
    temp, reason = extract_day(cfg, row, day, ssd_available)
    if reason:
        data["reasons"].append(reason)
    return (temp, temp)


def _append_day_data(metrics, procs, since, until, data):
    samples, disks, ok, metric_truncated = _read_metrics(metrics, since, until)
    proc_rows, proc_ok, proc_truncated = _read_procs(procs, since, until)
    _append_rows(data, "samples", samples)
    _append_rows(data, "disk_samples", disks)
    _append_rows(data, "procs", proc_rows)
    if not ok or not proc_ok:
        data["reasons"].append("partial day evidence")
    if metric_truncated or proc_truncated:
        data["reasons"].append("day query truncated")


def _read_day_journals(root, day, since, until, data, container=None):
    base = os.path.join(root, day) if day else root
    _append_journal_file(base, since, until, data, container)
    _append_container_logs(base, since, until, data, container)


def _append_journal_file(base, since, until, data, container):
    for name in ("journal.log", "journal.log.xz"):
        path = os.path.join(base, name)
        if not os.path.isfile(path) or os.path.islink(path):
            continue
        rows = read_journal(path)
        if rows is None:
            data["reasons"].append("journal unreadable")
            continue
        _append_rows(data, "journal", ((ts, line) for ts, line in rows
                       if ts is not None and since <= ts <= until
                       and (container is None or container in line)))
        break


def _append_container_logs(base, since, until, data, container):
    log_root = os.path.join(base, "containers")
    if not os.path.isdir(log_root) or os.path.islink(log_root):
        return
    for name in _container_names(log_root, container):
        _append_one_container_log(log_root, name, since, until, data)


def _container_names(root, container):
    names = [container + ".log.gz"] if container else sorted(os.listdir(root))[:64]
    return [name for name in names if os.path.basename(name) == name and
            name.endswith(".log.gz")]


def _append_one_container_log(root, name, since, until, data):
    path = os.path.join(root, name)
    if os.path.islink(path) or not os.path.isfile(path):
        return
    subject = name[:-7]
    rows = read_container_log(path, subject)
    if rows is None:
        data["reasons"].append("container log unreadable")
        return
    _append_rows(data, "journal", ((ts, "%s: %s" % (subject, line))
                   for ts, line in rows if ts is not None and since <= ts <= until))


def _snapshot_rows(cfg, since, until, ssd_available=None):
    roots = [cfg.fallback_root] if ssd_available is False else [cfg.ssd_root, cfg.fallback_root]
    found = []
    for parent in roots:
        found.extend(_snapshots_at(parent, since, until, MAX_SNAPSHOTS - len(found)))
    return _dedupe_snapshots(found)[:MAX_SNAPSHOTS]


def _snapshots_at(parent, since, until, limit):
    root = os.path.join(parent, "boots")
    if limit <= 0 or not os.path.isdir(root) or os.path.islink(root):
        return []
    found = []
    for name in sorted(os.listdir(root))[:256]:
        row = _read_snapshot_row(root, name)
        stamp = row.get("ts", row.get("start")) if row else None
        if isinstance(stamp, int) and since <= stamp <= until:
            found.append(row)
        if len(found) >= limit:
            break
    return found


def _read_snapshot_row(root, name):
    path = os.path.join(root, name, "summary.json")
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as stream:
            row = json.loads(stream.read(65537))
        return row if isinstance(row, dict) else None
    except (OSError, ValueError):
        return None


def _dedupe_snapshots(rows):
    seen = set()
    result = []
    for row in rows:
        key = row.get("boot_id")
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def collect(cfg, since, until, container=None, live=False, ssd_available=None):
    """Assemble available evidence without creating SQLite files or schema."""
    data = dict(samples=[], disk_samples=[], procs=[], events=[], journal=[],
                snapshots=[], reasons=[], _bytes=0)
    archives = _read_catalogs(cfg, since, until, container, data, ssd_available)
    _read_window_days(cfg, since, until, container, data, archives, ssd_available)
    if live and _window_has_now(since, until):
        _append_live_journal(since, until, data, container)
    _append_rows(data, "snapshots",
                 _snapshot_rows(cfg, since, until, ssd_available))
    evidence = Evidence(window=(since, until), samples=data["samples"],
                        disk_samples=data["disk_samples"], procs=data["procs"],
                        events=data["events"], journal=data["journal"],
                        snapshots=data["snapshots"])
    evidence.reasons = list(dict.fromkeys(data["reasons"]))
    return evidence


def _read_catalogs(cfg, since, until, container, data, ssd_available):
    _roots, catalogs = _catalog(cfg, ssd_available)
    archives = []
    try:
        for _path, conn in catalogs:
            events, minutes, rows = _catalog_rows(conn, since, until, container)
            _append_rows(data, "events", events)
            _append_rows(data, "samples", minutes)
            archives.extend(rows)
            if (getattr(events, "truncated", False) or
                    getattr(minutes, "truncated", False) or
                    getattr(rows, "truncated", False)):
                data["reasons"].append("catalog query truncated")
            if _evidence_full(data):
                data["reasons"].append("evidence budget reached")
                break
    finally:
        for _path, conn in catalogs:
            conn.close()
    if not catalogs:
        data["reasons"].append("catalog unavailable")
    data["events"] = _dedupe_events(data["events"])
    return archives


def _read_window_days(cfg, since, until, container, data, archives, ssd_available):
    if ssd_available is False:
        data["reasons"].append("SSD unavailable; hot and HDD evidence skipped")
    elif _window_days(since, until) > MAX_DAYS:
        data["reasons"].append("evidence window exceeds 366 days")
    else:
        for day in _day_names(since, until):
            if _evidence_full(data):
                data["reasons"].append("evidence budget reached")
                break
            _read_day(cfg, day, since, until, archives, data, container,
                      ssd_available)
            if _evidence_full(data):
                data["reasons"].append("evidence budget reached")
                break


def _window_days(since, until):
    first = datetime.datetime.utcfromtimestamp(since).date()
    last = datetime.datetime.utcfromtimestamp(until).date()
    return (last - first).days + 1


def _window_has_now(since, until):
    now = int(time.time())
    return since <= now and until >= now - now % 86400


def _dedupe_events(events):
    seen = set()
    result = []
    for event in sorted(events, key=lambda row: row.get("ts", 0)):
        key = (event.get("ts"), event.get("source"), event.get("kind"),
               event.get("subject"), event.get("detail"))
        marker = repr(key)
        if marker not in seen:
            seen.add(marker)
            result.append(event)
    return result


def _append_live_journal(since, until, data, container):
    now = int(time.time())
    since = max(since, now - now % 86400)
    until = min(until, now)
    argv = ["journalctl", "--no-pager", "--output=short-iso-precise",
            "--lines=301", "--since=@%d" % since, "--until=@%d" % until]
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=6,
                                universal_newlines=False)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        data["reasons"].append("current journal unavailable")
        return
    if result.returncode != 0:
        data["reasons"].append("current journal unavailable")
        return
    clipped = len(result.stdout) > (1 << 20)
    text = result.stdout[:1 << 20].decode("utf-8", "replace")
    lines = text.splitlines()
    if clipped or len(lines) > 300:
        data["reasons"].append("current journal truncated")
    rows = [normalize_line(line) for line in lines[:300]]
    _append_rows(data, "journal", ((ts, line) for ts, line in rows
                   if ts is not None and
                   (container is None or container in line)))


def _read_pstore(root, boot_id, names):
    if not _safe_boot_id(boot_id):
        return []
    base = os.path.join(root, "boots", boot_id, "pstore")
    result = []
    used = 0
    for name in list(names or ())[:32]:
        if not isinstance(name, str) or os.path.basename(name) != name or name in (".", ".."):
            continue
        path = os.path.join(base, name)
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as stream:
                data = stream.read(min(65536, 262144 - used))
                used += len(data)
                result.append(data.decode("utf-8", "replace"))
        except OSError:
            continue
    return result


def collect_boot(cfg, which=-1, ssd_available=None):
    """Read selected boot; -1 is the previous boot, per CLI convention."""
    _roots, catalogs = _catalog(cfg, ssd_available)
    if not catalogs:
        ev = Evidence(boot=None)
        ev.reasons = ["catalog unavailable"]
        return ev
    try:
        # Boot catalog is authoritative in SSD-first order; read each candidate
        # and prefer the first one with a usable boot table.
        rows, active = _boot_catalog_rows(catalogs)
        if not rows:
            ev = Evidence(boot=None)
            ev.reasons = ["boot evidence unavailable"]
            return ev
        boot = _select_boot(rows, which, active)
        if boot is None:
            ev = Evidence(boot=None)
            ev.reasons = ["boot evidence unavailable"]
            return ev
        return _boot_evidence(cfg, catalogs, boot, ssd_available)
    finally:
        for _path, candidate in catalogs:
            candidate.close()


def _boot_catalog_rows(catalogs):
    sql = 'SELECT boot_id,start,"end",clean,last_heartbeat,reset_source,pstore,verdict,confidence FROM boot ORDER BY COALESCE("end",last_heartbeat,start) DESC LIMIT 50'
    candidates = {}
    active_candidates = []
    for _path, conn in catalogs:
        rows = _query(conn, sql)
        if rows is None:
            continue
        active_id = _cursor_value(conn, "active_boot")
        for row in rows:
            candidates.setdefault(row[0], []).append(row)
            if row[0] == active_id:
                active_candidates.append((row[1] or 0, active_id))
    active = max(active_candidates)[1] if active_candidates else None
    rows = [_merge_boot_rows(boot_id, values, active)
            for boot_id, values in candidates.items()]
    return sorted(rows, key=_boot_sort_key, reverse=True)[:50], active


def _merge_boot_rows(boot_id, rows, active):
    key = (lambda row: (row[1] or 0, _boot_freshness(row))) if boot_id == active else _boot_freshness
    return max(rows, key=key)


def _boot_freshness(row):
    stamp = max(row[2] or 0, row[4] or 0)
    return stamp, row[2] is not None, row[4] is not None, row[1] or 0


def _boot_sort_key(row):
    return row[2] or row[4] or row[1] or 0


def _cursor_value(conn, name):
    rows = _query(conn, "SELECT value FROM cursor WHERE name=?", (name,))
    return rows[0][0] if rows else None


def _select_boot(rows, which, active=None):
    candidates = [row for row in rows if not (which < 0 and row[0] == active)]
    index = abs(which) - 1 if which < 0 else which
    if index < 0 or index >= len(candidates):
        return None
    names = ("boot_id", "start", "end", "clean", "last_heartbeat", "reset_source", "pstore", "verdict", "confidence")
    boot = dict(zip(names, candidates[index]))
    boot["clean"] = bool(boot["clean"]) if boot["clean"] is not None else None
    try:
        boot["pstore"] = json.loads(boot.get("pstore") or "[]")
    except ValueError:
        boot["pstore"] = []
    return boot


def _boot_evidence(cfg, catalogs, boot, ssd_available=None):
    boot_id = boot.get("boot_id")
    snapshot, pstore, journal = _boot_artifacts(cfg, catalogs, boot_id, boot, ssd_available)
    end = boot.get("last_heartbeat") or boot.get("end") or 0
    start, bounded = _boot_window_start(boot, end)
    window = collect(cfg, start, end, ssd_available=ssd_available) if end else Evidence()
    heartbeat = _heartbeat_cursor(catalogs, boot_id) or _read_boot_heartbeat(
        cfg, boot_id, ssd_available)
    if heartbeat is None and boot.get("last_heartbeat"):
        heartbeat = {"ts": boot["last_heartbeat"]}
    samples = _with_heartbeat_sample(window.samples, heartbeat)
    snapshots = list(window.snapshots)
    if snapshot:
        snapshots.append(snapshot)
    ev = Evidence(window=(start, end), boot=boot, samples=samples,
                  disk_samples=window.disk_samples, procs=window.procs,
                  events=window.events, pstore=pstore, heartbeat=heartbeat,
                  snapshots=_dedupe_snapshots(snapshots),
                  journal=_dedupe_journal(window.journal + journal))
    ev.reasons = _boot_reasons(window.reasons, bounded, end, snapshot)
    return ev


def _with_heartbeat_sample(samples, heartbeat):
    result = list(samples)
    if result or not heartbeat:
        return result
    sample = _power_sample(heartbeat)
    if sample:
        result.append(sample)
    return result


def _boot_reasons(reasons, bounded, end, snapshot):
    result = list(reasons)
    if bounded:
        result.append("boot evidence limited to last five minutes")
    if not end:
        result.append("boot last-seen time unavailable")
    if not snapshot:
        result.append("boot snapshot unavailable")
    return result


def _heartbeat_cursor(catalogs, boot_id):
    for _path, conn in catalogs:
        raw = _cursor_value(conn, "boot-heartbeat:" + str(boot_id))
        value = _parse_heartbeat(raw, boot_id)
        if value:
            return value
    return None


def _parse_heartbeat(raw, boot_id):
    if not isinstance(raw, str) or len(raw) > 4096:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(value, dict) or value.get("boot_id") != boot_id:
        return None
    result = {"boot_id": boot_id, "ts": value.get("ts")}
    if not isinstance(result["ts"], int):
        return None
    power = value.get("power")
    if isinstance(power, dict):
        result["power"] = _whitelisted_power(power)
    return result


def _whitelisted_power(power):
    names = ("vin_mv", "vin_ma", "cpu_mw", "gpu_mw")
    return dict((name, power[name]) for name in names
                if isinstance(power.get(name), (int, float)))


def _power_sample(heartbeat):
    power = heartbeat.get("power")
    if not power:
        return None
    row = {"ts": heartbeat["ts"]}
    row.update(_whitelisted_power(power))
    return row if any(name in row for name in ("vin_mv", "vin_ma")) else None


def _boot_window_start(boot, end):
    boundary = max(0, end - 300)
    original = boot.get("start")
    start = min(end, max(original, boundary)) if isinstance(original, int) else boundary
    return start, isinstance(original, int) and original < boundary


def _read_boot_heartbeat(cfg, boot_id, ssd_available):
    roots = [cfg.fallback_root] if ssd_available is False else [cfg.ssd_root, cfg.fallback_root]
    for root in roots:
        path = os.path.join(root, "heartbeat")
        value = _read_small_json(path)
        if value and value.get("boot_id") == boot_id:
            return value
    return None


def _read_small_json(path):
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as stream:
            text = stream.read(4097)
        value = json.loads(text) if len(text) <= 4096 else None
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _dedupe_journal(rows):
    seen = set()
    result = []
    for row in rows:
        if row not in seen:
            seen.add(row)
            result.append(row)
    return result


def _boot_artifacts(cfg, catalogs, boot_id, boot, ssd_available=None):
    snapshot_id = _snapshot_id(catalogs, boot_id) or boot_id
    snapshot = _find_snapshot(cfg, snapshot_id, ssd_available)
    pstore = list((snapshot or {}).get("pstore") or boot["pstore"])
    return snapshot, pstore, _previous_journal(cfg, snapshot_id, ssd_available)


def _snapshot_id(catalogs, boot_id):
    for _path, conn in catalogs:
        value = _cursor_value(conn, "boot-snapshot:" + str(boot_id))
        if value:
            return value
    return None


def _find_snapshot(cfg, boot_id, ssd_available=None):
    if not isinstance(boot_id, str) or os.path.basename(boot_id) != boot_id:
        return None
    roots = (cfg.fallback_root,) if ssd_available is False else (cfg.ssd_root, cfg.fallback_root)
    for root in roots:
        row = _snapshot_boot(root, boot_id)
        if row is not None:
            return row
    return None


def _snapshot_boot(root, boot_id):
    if not _safe_boot_id(boot_id):
        return None
    base = os.path.join(root, "boots", boot_id)
    path = os.path.join(base, "summary.json")
    if (os.path.islink(root) or os.path.islink(os.path.join(root, "boots")) or
            os.path.islink(base) or os.path.islink(path) or not os.path.isfile(path)):
        return None
    try:
        with open(path, "r", encoding="utf-8") as stream:
            row = json.loads(stream.read(65537))
        return row if isinstance(row, dict) and row.get("boot_id") == boot_id else None
    except (OSError, ValueError):
        return None


def _safe_boot_id(value):
    return (isinstance(value, str) and value not in (".", "..") and
            os.path.basename(value) == value and "/" not in value and "\\" not in value)


def _previous_journal(cfg, boot_id, ssd_available=None):
    if not _safe_boot_id(boot_id):
        return []
    roots = (cfg.fallback_root,) if ssd_available is False else (cfg.ssd_root, cfg.fallback_root)
    for root in roots:
        path = _snapshot_file(root, boot_id, "prev_journal_tail.txt")
        if path is None:
            continue
        try:
            with open(path, "r", encoding="utf-8") as stream:
                lines = stream.read(65537).splitlines()
            if len(lines) > 300:
                lines = lines[-300:]
            return _dated_lines(lines)
        except OSError:
            continue
    return []


def _snapshot_file(root, boot_id, name):
    base = os.path.join(root, "boots", boot_id)
    path = os.path.join(base, name)
    if (os.path.islink(root) or os.path.islink(os.path.join(root, "boots")) or
            os.path.islink(base) or os.path.islink(path) or not os.path.isfile(path)):
        return None
    return path


def _dated_lines(lines):
    return [(ts, text) for ts, text in (normalize_line(line) for line in lines)
            if ts is not None]
