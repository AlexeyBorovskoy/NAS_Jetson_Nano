"""CLI for inspecting collected OBS-1 evidence without touching live sources."""
import argparse
import datetime
import os
import sqlite3
import sys

from blackbox.config import load_config
from blackbox.store import Catalog
from blackbox.collector_events import redact_text
from blackbox.redact import mask_family_text
from blackbox.why.evidence import collect, collect_boot
from blackbox.why.rules import evaluate

OUTPUT_LIMIT = 65536


def _timestamp(value):
    parsed = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M")
    return int(calendar_time(parsed))


def calendar_time(value):
    import calendar
    return calendar.timegm(value.timetuple())


def _parser():
    parser = argparse.ArgumentParser(prog="nas-why")
    parser.add_argument("--boot", type=int)
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--container")
    parser.add_argument("--short", action="store_true")
    parser.add_argument("--record", action="store_true")
    return parser


def record_boot_verdict(cfg, catalog):
    evidence = collect_boot(cfg, -1)
    verdicts = evaluate(evidence, cfg)
    if evidence.boot is None or not verdicts:
        return {}
    chosen = verdicts[0]
    row = dict(evidence.boot)
    row["verdict"] = chosen["cls"]
    row["confidence"] = chosen["confidence"]
    catalog.upsert_boot(row)
    return chosen


def _boot_evidence(cfg, args):
    available = os.path.ismount(cfg.ssd_mount) if args.supervised else None
    evidence = collect_boot(cfg, args.boot if args.boot is not None else -1,
                            ssd_available=available)
    if args.record and evidence.boot:
        root = cfg.ssd_root if available is not False else cfg.fallback_root
        conn = Catalog(os.path.join(root, "catalog.db"))
        try:
            record_boot_verdict(cfg, conn)
        finally:
            conn.close()
    return evidence


def _window_evidence(cfg, args, live, available=None):
    if not args.since or not args.until:
        raise ValueError("both --since and --until are required")
    since, until = _timestamp(args.since), _timestamp(args.until)
    if since > until:
        raise ValueError("--since must not be after --until")
    return collect(cfg, since, until, container=args.container, live=live,
                   ssd_available=available)


def _format_verdict(verdict, cfg):
    confidence = "неизвестно" if verdict["confidence"] == "unknown" else verdict["confidence"]
    detail = redact_text("", verdict["verdict"], cfg)
    return "%s (%s): %s" % (verdict["cls"], confidence, detail)


def _chronology(evidence, cfg):
    rows = [(ts, "journal", line) for ts, line in evidence.journal]
    rows.extend((row.get("ts"), "docker/%s" % row.get("subject"),
                 "%s %s" % (row.get("kind"), row.get("detail")))
                for row in evidence.events)
    rows = [row for row in rows if isinstance(row[0], (int, float))]
    return ["%s %s %s" % (datetime.datetime.utcfromtimestamp(ts).strftime("%H:%M:%S"),
                           source, mask_family_text(redact_text("", text, cfg)))
            for ts, source, text in sorted(rows)]


def _render(evidence, cfg, short):
    verdicts = evaluate(evidence, cfg)
    lines = [_format_verdict(row, cfg) for row in verdicts]
    if evidence.reasons:
        lines.append("неизвестно: %s" % ", ".join(evidence.reasons))
    chronology = _chronology(evidence, cfg)
    if short:
        lines = _short_lines(evidence, lines, chronology)
    else:
        lines.extend(chronology)
    return lines or ["data (unknown): evidence unavailable"]


def _short_lines(evidence, lines, chronology):
    result = list(lines[:2])
    result.append("last seen: " + _time_text(_last_seen(evidence)))
    result.append(_power_text(evidence))
    result.extend(lines[2:4])
    result.extend(chronology[:max(0, 6 - len(result))])
    return result[:6]


def _last_seen(evidence):
    if evidence.heartbeat and evidence.heartbeat.get("ts"):
        return evidence.heartbeat["ts"]
    if evidence.boot and evidence.boot.get("last_heartbeat"):
        return evidence.boot["last_heartbeat"]
    stamps = [row.get("ts") for row in evidence.samples if row.get("ts") is not None]
    return max(stamps) if stamps else None


def _time_text(stamp):
    if stamp is None:
        return "unknown"
    return datetime.datetime.utcfromtimestamp(stamp).strftime("%Y-%m-%d %H:%M:%S UTC")


def _power_text(evidence):
    samples = [row for row in evidence.samples if row.get("ts") is not None]
    if not samples:
        return "power: unknown (no sample)"
    latest = max(samples, key=lambda row: row["ts"])
    parts = ["vin_mv=%s" % latest.get("vin_mv")]
    if latest.get("vin_ma") is not None:
        parts.append("vin_ma=%s" % latest["vin_ma"])
    return "power: " + " ".join(parts)


def main(argv=None, cfg=None, supervised=False):
    try:
        args = _parser().parse_args(argv)
        cfg = cfg or load_config()
        args.supervised = supervised
        available = os.path.ismount(cfg.ssd_mount) if supervised else None
        evidence = (_boot_evidence(cfg, args) if args.boot is not None else
                    _window_evidence(cfg, args, supervised, available))
        _print_bounded(_render(evidence, cfg, args.short), cfg)
        return 0
    except MemoryError:
        print("unknown: evidence memory limit reached", file=sys.stdout)
        return 2
    except (OSError, ValueError, sqlite3.Error):
        print("unknown: evidence unavailable", file=sys.stdout)
        return 0


def _print_bounded(lines, cfg):
    used = 0
    marker = b"[output truncated]\n"
    content_limit = OUTPUT_LIMIT - len(marker)
    for line in lines:
        line = redact_text("", line, cfg)
        output = (line + "\n").encode("utf-8", "replace")
        room = content_limit - used
        if len(output) > room:
            sys.stdout.write(output[:room].decode("utf-8", "ignore"))
            sys.stdout.write(marker.decode("ascii"))
            break
        sys.stdout.write(output.decode("utf-8"))
        used += len(output)
    else:
        return
