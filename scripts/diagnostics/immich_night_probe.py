#!/usr/bin/env python3
"""Read-only Immich night probe: one JSON report, never raw command output.
Journal coverage proves only a retained current-boot kernel record at/before since, not the absence of internal journal gaps."""
import argparse, calendar, json, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
BACKUP_UNITS = ("nasa-backup.service", "nas_jetson_nano-config-backup.service", "nas_jetson_nano-immich-hdd-copy.service")
PSQL_SH = 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$1"'; SQL = "SELECT value->'nightlyTasks'->'missingThumbnails' FROM system_metadata WHERE key='system-config';"
INSPECT_FMT = "{{.RestartCount}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.State.StartedAt}}"
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})$")
BACKUP_TIME_RE = re.compile(r"^(?:[A-Za-z]{3} )?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC$"); HEALTH = ("healthy", "unhealthy", "starting", "none"); STAMP = "%Y-%m-%dT%H:%M:%SZ"
def parse_since(text):
    value = text.strip().replace(",", ".")
    if not ISO_RE.match(value): raise ValueError("since_utc must be timezone-aware ISO8601")
    value = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", value.replace("Z", "+0000"))
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try: return datetime.strptime(value, fmt).astimezone(timezone.utc)
        except ValueError: pass
    raise ValueError("since_utc must be timezone-aware ISO8601")
def docker_time(text):
    match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z$", text.strip())
    if not match: return None
    fraction = (match.group(2) or "0")[:6].ljust(6, "0")
    try: return datetime.strptime(match.group(1) + "." + fraction, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
    except ValueError: return None
def backup_age(value, now):
    match = BACKUP_TIME_RE.match(value.strip())
    if not match: return None
    try: stamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError: return None
    return round((now - stamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0, 2)
def run(label, args):
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, universal_newlines=True, env=dict(os.environ, TZ="UTC", LC_ALL="C"))
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "%s: %s" % (label, type(exc).__name__)
    return (proc.stdout, None) if proc.returncode == 0 else (None, "%s: exit_%d" % (label, proc.returncode))
def inspect_status(run_cmd, since):
    out, err = run_cmd("docker_inspect", ["docker", "inspect", "--format", INSPECT_FMT, "homecloud_immich_microservices"])
    if err: return None, err
    fields = out.strip().split("|")
    if len(fields) != 3 or not fields[0].isdigit() or fields[1].strip() not in HEALTH: return None, "docker_inspect: malformed"
    started = docker_time(fields[2])
    if started is None: return None, "docker_inspect: malformed"
    if started >= since: return None, "docker_inspect: start_in_window"
    return {"restart_count": int(fields[0]), "health": fields[1].strip(), "started_at": fields[2].strip()}, None
def journal_oom(run_cmd, since):
    stamp = since.strftime("%Y-%m-%d %H:%M:%S UTC")
    out, err = run_cmd("journal_coverage", ["journalctl", "-b", "0", "-k", "--until", stamp, "--lines=1", "--no-pager", "-o", "json"])
    if err: return None, None, "journalctl: coverage_unknown"
    try: micros = int(json.loads(out.strip().splitlines()[-1])["__REALTIME_TIMESTAMP"])
    except (ValueError, KeyError, IndexError, TypeError): return None, None, "journalctl: coverage_unknown"
    if micros <= 0 or micros > calendar.timegm(since.utctimetuple()) * 1000000 + since.microsecond: return None, None, "journalctl: coverage_unknown"
    out, err = run_cmd("journalctl", ["journalctl", "-b", "0", "-k", "--since", stamp, "--lines=20001", "--no-pager", "-o", "cat"])
    if err: return None, None, err
    lines = out.splitlines()
    if len(lines) > 20000: return None, None, "journalctl: coverage_limit"
    cgroup = sum("Memory cgroup out of memory" in line for line in lines)
    return cgroup, sum("Out of memory:" in line and "Memory cgroup out of memory" not in line for line in lines), None
def nightly_flag(run_cmd):
    out, err = run_cmd("immich_db", ["docker", "exec", "homecloud_immich_db", "sh", "-c", PSQL_SH, "psql", SQL])
    if err: return None, err
    value = out.strip().lower(); return (value == "true", None) if value in ("true", "false") else (None, None)
def backups_status(run_cmd, now):
    out, err = run_cmd("systemctl", ["systemctl", "show", "-p", "Id", "-p", "Result", "-p", "ExecMainExitTimestamp"] + list(BACKUP_UNITS))
    if err: return [], err
    backups = []
    for block in out.strip().split("\n\n"):
        fields = {k.strip(): v.strip() for k, _, v in (line.partition("=") for line in block.splitlines()) if k.strip()}
        stamp = fields.get("ExecMainExitTimestamp", "")
        if fields.get("Id"):
            backups.append({"id": fields["Id"], "result": fields.get("Result", ""), "exit_timestamp_present": bool(stamp), "age_hours": backup_age(stamp, now)})
    return backups, None
def backups_ok(backups):
    return len(backups) == len(BACKUP_UNITS) and all(item["result"] == "success" and item["age_hours"] is not None and 0 <= item["age_hours"] <= 26 for item in backups)
def state(container, baseline):
    if container is None: return None, None, None, None
    restarts = container["restart_count"]
    return restarts, restarts - baseline, container["health"], container["started_at"]
def classify(container, baseline, cgroup, global_oom, nightly, backups, errors):
    problems = []
    if errors: problems.append("command")
    if cgroup or global_oom: problems.append("oom")
    if nightly is not False: problems.append("nightly_missing_thumbnails")
    if not backups_ok(backups): problems.append("backups")
    if container is None or container["health"] != "healthy": problems.append("health")
    if (None if container is None else container["restart_count"] - baseline) != 0: problems.append("restart_count")
    return problems
def probe(since, baseline, now=None, run_cmd=run, min_window=6):
    now = now or datetime.now(timezone.utc)
    if now < since + timedelta(hours=min_window):
        return {"status": "not_due", "checked_at": now.strftime(STAMP), "since_utc": since.strftime(STAMP), "errors": []}, 2
    container, err_i = inspect_status(run_cmd, since)
    cgroup, global_oom, err_j = journal_oom(run_cmd, since)
    nightly, err_n = nightly_flag(run_cmd)
    backups, err_b = backups_status(run_cmd, now)
    final, err_f = inspect_status(run_cmd, since)
    if err_f: err_f = err_f.replace("docker_inspect:", "docker_inspect_final:", 1)
    errors = [err for err in (err_i, err_j, err_n, err_b, err_f) if err]
    if container is not None and final is not None and container != final: errors.append("docker_inspect: changed")
    restarts, delta, health, started = state(final, baseline)
    problems = classify(final, baseline, cgroup, global_oom, nightly, backups, errors)
    label, code = ("ok", 0) if not problems else ("failed", 1)
    report = {"status": label, "checked_at": now.strftime(STAMP), "since_utc": since.strftime(STAMP),
              "restart_count": restarts, "delta": delta, "counter_reset": delta is not None and delta < 0,
              "health": health, "started_at": started, "cgroup_oom_count": cgroup, "global_oom_count": global_oom,
              "nightly_missing_thumbnails": nightly, "backups": backups, "errors": errors}
    return report, code
def main(argv=None, now=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-utc", required=True); parser.add_argument("--baseline-restarts", required=True, type=int); parser.add_argument("--min-window-hours", type=float, default=6)
    args = parser.parse_args(argv)
    if args.baseline_restarts < 0 or args.min_window_hours < 0: parser.error("--baseline-restarts and --min-window-hours must be nonnegative")
    try: since = parse_since(args.since_utc)
    except ValueError:
        print(json.dumps({"status": "failed", "errors": ["since_utc: invalid"]}))
        return 2
    report, code = probe(since, args.baseline_restarts, now=now, min_window=args.min_window_hours)
    print(json.dumps(report))
    return code
if __name__ == "__main__":
    sys.exit(main())
