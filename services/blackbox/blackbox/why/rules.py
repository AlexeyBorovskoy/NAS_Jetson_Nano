"""Pure verdict rules for the NAS blackbox evidence contract (Python 3.6)."""


class Evidence(object):
    """Read-only-by-convention evidence bundle with independent list defaults."""
    def __init__(self, window=(0, 0), boot=None, samples=None, disk_samples=None,
                 procs=None, events=None, journal=None, **boot_evidence):
        unknown = set(boot_evidence) - {"pstore", "heartbeat", "snapshots"}
        if unknown:
            raise TypeError("Unknown boot evidence field")
        self.window = window
        self.boot = boot
        self.samples = list(samples or ())
        self.disk_samples = list(disk_samples or ())
        self.procs = list(procs or ())
        self.events = list(events or ())
        self.journal = list(journal or ())
        self.pstore = list(boot_evidence.get("pstore") or ())
        self.heartbeat = boot_evidence.get("heartbeat")
        self.snapshots = list(boot_evidence.get("snapshots") or ())


def _inside(ev, ts):
    return ts is not None and ev.window[0] <= ts <= ev.window[1]


def _rows(ev, rows):
    return [row for row in rows if _inside(ev, row.get("ts"))]


def _journal(ev):
    return [(ts, line) for ts, line in ev.journal if _inside(ev, ts)]


def _v(cls, text, confidence, items):
    evidence = [(int(ts), str(src), str(msg)) for ts, src, msg in items]
    return {"cls": cls, "verdict": text, "confidence": confidence,
            "evidence": evidence}


def _items(rows, source, text):
    return [(row.get("ts"), source, text(row)) for row in rows]


def _snapshot_ts(snapshot):
    return snapshot.get("ts", snapshot.get("start"))


def _boot_context(ev, end):
    boot = ev.boot or {}
    reset = boot.get("reset_source") or "unknown"
    return [(end, "boot", "PMC reset source: %s" % reset)]


def _dstate(rows):
    return [row for row in rows if row.get("state") == "D" and
            ("fuse" in (row.get("wchan") or "") or
             "request_wait_answer" in (row.get("wchan") or ""))]


def _unclean_hang(ev, cfg, end, base, samples):
    procs = _dstate(_rows(ev, ev.procs))
    recent = [row for row in procs if end - row["ts"] <= 60]
    lowmem = [row for row in samples if row.get("mem_avail_mb") is not None
              and row["mem_avail_mb"] < cfg.mem_crit_mb]
    near_mem = [row for row in lowmem if any(abs(row["ts"] - proc["ts"]) <= 60
                                               for proc in recent)]
    if len(set(row.get("pid") for row in recent)) < 2 or not near_mem:
        return None
    items = _items(recent, "proc", lambda row: "pid=%s D %s" %
                   (row.get("pid"), row.get("wchan")))
    items += _items(near_mem, "sample", lambda row: "MemAvailable=%s MB" %
                    row.get("mem_avail_mb"))
    return _v("unclean_boot", "вероятно, зависание, затем сброс", "probable",
              base + items)


def _unclean_power(samples, cfg, base):
    power = [row for row in samples if row.get("vin_mv") is not None]
    low = [row for row in power if row["vin_mv"] < cfg.vin_low_mv]
    if low:
        return _v("unclean_boot", "вероятно, питание", "probable", base +
                  _items(low, "sample", lambda row: "vin_mv=%s" % row["vin_mv"]))
    if len(power) >= 2 and all(row["vin_mv"] == power[0]["vin_mv"] for row in power):
        return _v("unclean_boot", "вероятно, внезапное пропадание питания или "
                  "аппаратный сброс; различить нечем", "probable", base +
                  _items(power, "sample", lambda row: "vin_mv=%s" % row["vin_mv"]))
    return None


def _unclean_evidence(ev, cfg, end, base):
    pstore = ev.pstore or ev.boot.get("pstore") or []
    if pstore:
        return _v("unclean_boot", "паника ядра", "fact", base +
                  [(end, "pstore", "выдержка: %s" % ", ".join(pstore))])
    start = max(ev.window[0], end - 60)
    samples = [row for row in _rows(ev, ev.samples)
               if start <= row["ts"] <= end]
    hang = _unclean_hang(ev, cfg, end, base, samples)
    if hang:
        return hang
    return _unclean_power(samples, cfg, base)


def _planned_shutdown(ev, base):
    events = _rows(ev, ev.events)
    shutdown = [row for row in events if row.get("source") == "boot" and
                row.get("kind") == "poweroff_command"]
    if not shutdown:
        return None
    items = _items(shutdown, "event", lambda row: row.get("kind"))
    return _v("unclean_boot", "штатное выключение командой", "fact", base + items)


def _unclean_end(ev, boot):
    end = (ev.heartbeat or {}).get("ts") or boot.get("last_heartbeat") or ev.window[1]
    end = min(end, ev.window[1])
    boot_time = (ev.heartbeat or {}).get("ts") or boot.get("last_heartbeat")
    boot_time = boot_time or boot.get("end") or end
    if not _inside(ev, boot_time):
        return None
    return end


def _unclean_result(ev, cfg, end, base):
    planned = _planned_shutdown(ev, base)
    if planned:
        return planned
    verdict = _unclean_evidence(ev, cfg, end, base)
    if verdict:
        return verdict
    return _v("unclean_boot", "нештатная загрузка; причина неизвестна",
              "unknown", base)


def rule_unclean_boot(ev, cfg):
    boot = ev.boot
    if not boot or boot.get("clean") is not False:
        return []
    end = _unclean_end(ev, boot)
    if end is None:
        return []
    base = _boot_context(ev, end)
    return [_unclean_result(ev, cfg, end, base)]


def _watchdog_lines(ev):
    import re
    unit = "nas_jetson_nano-container-watchdog"
    logger = re.compile(r"(?:^|\s)" + re.escape(unit) + r"(?:\[\d+\])?:")
    lines = []
    for ts, line in _journal(ev):
        lowered = line.lower()
        if logger.search(lowered) and "watchdog:" in lowered and "docker restart" in lowered:
            lines.append((ts, line))
    return lines


def _watchdog_matches(lines, subject, ts):
    marker = "watchdog: %s:" % str(subject).lower()
    return [(when, line) for when, line in lines
            if abs(when - ts) <= 120 and marker in line.lower()]


def _docker_oom(ev, subject, ts):
    return [row for row in _rows(ev, ev.events)
            if row.get("source") == "docker" and row.get("kind") == "oom"
            and row.get("subject") == subject and abs(row["ts"] - ts) <= 120]


def _container_label(code, lines, oom, legacy_oom, subject):
    if lines and code == 143:
        text, confidence = "контейнер %s перезапущен сторожем OPS-1" % subject, "fact"
    elif code == 137 and (legacy_oom or oom):
        text, confidence = "контейнер %s убит по нехватке памяти (137, OOM)" % subject, "fact"
    elif code == 137:
        text, confidence = "контейнер %s завершился с кодом 137; причина неизвестна" % subject, "unknown"
    elif code == 143:
        text, confidence = "контейнер %s остановлен сигналом SIGTERM (143)" % subject, "fact"
    elif code is None:
        text, confidence = "контейнер %s: неизвестная причина завершения" % subject, "unknown"
    else:
        text, confidence = "контейнер %s: ошибка приложения (код %s)" % (subject, code), "probable"
    return text, confidence


def _container_result(ev, row, watchdog):
    detail = row.get("detail") or {}
    code = detail.get("exitCode")
    ts = row["ts"]
    subject = row.get("subject") or "контейнер"
    if code == 0:
        return None
    lines = _watchdog_matches(watchdog, subject, ts)
    oom = _docker_oom(ev, subject, ts)
    text, confidence = _container_label(code, lines, oom, detail.get("oom"), subject)
    items = [(ts, "docker", "die %s exitCode=%s" % (subject, code))]
    items += [(when, "journal", line) for when, line in lines]
    items += _items(oom, "docker", lambda item: "oom %s" % subject)
    items += [(ts, "container_log", str(line).rstrip()) for line in detail.get("tail", [])]
    return _v("container", text, confidence, items)


def rule_container(ev, cfg):
    watchdog = _watchdog_lines(ev)
    result = []
    for row in _rows(ev, ev.events):
        if row.get("source") != "docker" or row.get("kind") != "die":
            continue
        verdict = _container_result(ev, row, watchdog)
        if verdict is not None:
            result.append(verdict)
    return result


def _disk_rows(ev):
    result = {}
    for row in ev.disk_samples:
        if isinstance(row, dict):
            values = (row.get("ts"), row.get("disk_id"), row.get("rios"),
                      row.get("wios"), row.get("rsect"), row.get("wsect"),
                      row.get("busy_ms"))
        else:
            values = row
        if _inside(ev, values[0]):
            result.setdefault(values[1], []).append(values)
    return result


def _snapshot_hdd_ids(ev, mountpoint):
    found = set()
    for snapshot in ev.snapshots:
        mounts = snapshot.get("mounts") or {}
        disks = snapshot.get("disks") or {}
        disk_id = mounts.get(mountpoint)
        if disk_id:
            found.add(disk_id)
        for dev, identity in disks.items():
            if isinstance(identity, dict) and identity.get("mountpoint") == mountpoint:
                found.add(identity.get("by_id") or identity.get("disk_id"))
    return set(item for item in found if item)


def _legacy_hdd_ids(grouped):
    return set(disk for disk in grouped
               if "_hdd" in str(disk).lower())


def _stalled_disks(ev, cfg, mountpoint):
    grouped = _disk_rows(ev)
    explicit = _snapshot_hdd_ids(ev, mountpoint)
    candidates = explicit or _legacy_hdd_ids(grouped)
    result = []
    for disk in candidates:
        rows = sorted(grouped.get(disk, []), key=lambda row: row[0])
        if len(rows) < 2 or any(value is None for row in rows for value in row[2:7]):
            continue
        first, last = rows[0], rows[-1]
        if last[0] - first[0] < max(90, cfg.disk_stall_s):
            continue
        if any(row[index] != first[index] for row in rows
               for index in range(2, 7)):
            continue
        result.append((disk, first, last))
    return result


def _clustered_hung_procs(ev, hangs):
    procs = _dstate(_rows(ev, ev.procs))
    if not hangs:
        return []
    intervals = []
    for event in hangs:
        since = (event.get("detail") or {}).get("since")
        start = since if since is not None else event["ts"] - 10
        intervals.append((start, ev.window[1]))
    relevant = [row for row in procs if any(start <= row["ts"] <= end
                                             for start, end in intervals)]
    for anchor in relevant:
        cluster = [row for row in relevant
                   if abs(row["ts"] - anchor["ts"]) <= 10]
        if len(set(row.get("pid") for row in cluster)) >= 3:
            return cluster
    return []


def rule_disk_hang(ev, cfg):
    events = _rows(ev, ev.events)
    mountpoint = cfg.hdd_mount
    hangs = [row for row in events if row.get("kind") == "mount_hung"
             and row.get("subject") == mountpoint]
    procs = _clustered_hung_procs(ev, hangs)
    stalled = _stalled_disks(ev, cfg, mountpoint)
    if not procs or not stalled:
        return []
    items = _items(procs, "proc", lambda row: "pid=%s D %s" %
                   (row.get("pid"), row.get("wchan")))
    items += _items(hangs, "event", lambda row: "mount_hung %s" % mountpoint)
    for disk, first, last in stalled:
        items.append((last[0], "disk", "%s counters unchanged for %ss" %
                      (disk, last[0] - first[0])))
    return [_v("disk_hang", "вероятно, зависание диска", "probable", items)]


def _kernel_message(line):
    import re
    direct = re.match(r"^kernel:\s*(.*)$", line, re.I)
    if direct:
        return direct.group(1)
    dated = re.match(r"^\d{4}-\d{2}-\d{2}T\S+\s+\S+\s+kernel:\s*(.*)$",
                     line, re.I)
    return dated.group(1) if dated else None


def rule_memory(ev, cfg):
    markers = ("oom-kill:", "out of memory:", "killed process ")
    found = []
    for ts, line in _journal(ev):
        message = _kernel_message(line)
        if message and any(marker in message.lower() for marker in markers):
            found.append((ts, message))
    if not found:
        return []
    import re
    process = None
    for _, line in found:
        match = re.search(r"Killed process\s+\d+\s+\(([^)]+)\)", line, re.I)
        if match:
            process = match.group(1)
    text = "нехватка памяти" + (": убит процесс %s" % process if process else "")
    return [_v("memory", text, "fact", [(ts, "journal", line) for ts, line in found])]


def rule_network(ev, cfg):
    labels = {"dns_down": "недоступен DNS",
              "gateway_down": "недоступна домашняя сеть/роутер",
              "tunnel_down": "недоступен туннель VPS или провайдер/адрес",
              "proxy_down": "недоступен прокси Telegram"}
    return [_v("network", labels[row["kind"]], "probable",
               [(row["ts"], row.get("source", "event"),
                 "%s: %s" % (row["kind"], row.get("subject", "")))])
            for row in _rows(ev, ev.events) if row.get("kind") in labels]


def _thermal_pair(samples):
    hot = [row for row in samples if row.get("t_cpu") is not None
           and row["t_cpu"] >= 950 and row.get("freq_mhz") is not None]
    for current in reversed(hot):
        earlier = [row for row in samples if 0 < current["ts"] - row["ts"] <= 60
                   and row.get("freq_mhz") is not None]
        if earlier and current["freq_mhz"] < earlier[-1]["freq_mhz"]:
            return earlier[-1], current
    return None


def rule_thermal(ev, cfg):
    samples = sorted(_rows(ev, ev.samples), key=lambda row: row["ts"])
    pair = _thermal_pair(samples)
    if not pair:
        return []
    evidence = _items(pair, "sample", lambda row: "t_cpu=%s freq_mhz=%s" %
                       (row.get("t_cpu"), row.get("freq_mhz")))
    return [_v("thermal", "вероятен перегрев CPU со снижением частоты",
               "probable", evidence)]


def rule_usb(ev, cfg):
    snapshots = ev.snapshots
    if len(snapshots) < 2:
        return []
    old, new = snapshots[-2:]
    stamp = _snapshot_ts(new)
    if not _inside(ev, stamp):
        return []
    before = old.get("disks") or {}
    after = new.get("disks") or {}
    changed = []
    for letter, identity in before.items():
        new_letter = next((key for key, value in after.items()
                           if value == identity), None)
        if new_letter and new_letter != letter:
            changed.append((identity, letter, new_letter))
    if not changed:
        return []
    evidence_ts = max(ev.window[0], min(stamp, ev.window[1]))
    items = [(evidence_ts, "snapshot", "%s: %s → %s" % item) for item in changed]
    return [_v("usb", "буквы дисков поменялись", "fact", items)]


def _has_data(ev):
    if any((_rows(ev, ev.samples), _disk_rows(ev), _rows(ev, ev.procs),
            _rows(ev, ev.events), _journal(ev))):
        return True
    if ev.heartbeat and _inside(ev, ev.heartbeat.get("ts")):
        return True
    if ev.boot and _inside(ev, ev.boot.get("last_heartbeat")):
        return True
    if ev.boot and ev.boot.get("pstore") and _inside(
            ev, ev.boot.get("last_heartbeat")):
        return True
    return any(_inside(ev, _snapshot_ts(snapshot)) for snapshot in ev.snapshots)


def evaluate(ev, cfg):
    if not _has_data(ev):
        return [_v("data", "данных нет за %s..%s" % ev.window, "unknown", [])]
    rules = (rule_unclean_boot, rule_container, rule_disk_hang, rule_memory,
             rule_network, rule_thermal, rule_usb)
    verdicts = []
    for rule in rules:
        verdicts.extend(rule(ev, cfg))
    if verdicts:
        return verdicts
    return [_v("data", "данных недостаточно для вердикта за %s..%s" % ev.window,
               "unknown", [])]
