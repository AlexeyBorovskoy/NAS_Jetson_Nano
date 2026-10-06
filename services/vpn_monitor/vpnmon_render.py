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
