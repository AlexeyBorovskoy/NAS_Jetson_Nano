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
