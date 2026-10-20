#!/usr/bin/env python3
"""Synthetic unit tests for scripts/diagnostics/immich_night_probe.py."""
import contextlib, importlib.util, io, json, os, unittest
from unittest import mock
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "scripts", "diagnostics", "immich_night_probe.py")
spec = importlib.util.spec_from_file_location("immich_night_probe", SCRIPT)
night = importlib.util.module_from_spec(spec)
spec.loader.exec_module(night)
OK_BACKUPS = "\n\n".join(
    "Id=%s\nResult=success\nExecMainExitTimestamp=2026-10-20 03:00:00 UTC" % unit
    for unit in night.BACKUP_UNITS)
OK_COVERAGE = '{"__REALTIME_TIMESTAMP": "1792454400000000"}'
def answer(stdout="", code=0):
    return mock.Mock(returncode=code, stdout=stdout, stderr="")
def commands(inspect="0|healthy|2026-10-19T20:00:00.123456789Z", journal="", psql="false",
             systemctl=OK_BACKUPS, coverage=OK_COVERAGE, fail=None):
    outputs = list(inspect) if isinstance(inspect, (list, tuple)) else [inspect]
    def runner(args, **kwargs):
        assert kwargs.get("timeout"), "subprocess timeout must be bounded"
        assert kwargs["env"]["TZ"] == "UTC" and kwargs["env"]["LC_ALL"] == "C"
        kind = args[1] if args[0] == "docker" else args[0]
        if args[0] == "systemctl":
            assert args[2:8] == ["-p", "Id", "-p", "Result", "-p", "ExecMainExitTimestamp"]
        if kind == fail: return answer(code=1)
        if kind == "inspect": return answer(stdout=outputs.pop(0) if len(outputs) > 1 else outputs[0])
        if kind == "journalctl":
            assert args[1:4] == ["-b", "0", "-k"], "only the current boot may establish coverage"
            return answer(stdout=coverage if "--until" in args else journal)
        return answer({"exec": psql, "systemctl": systemctl}[kind])
    return runner
class NightProbeTest(unittest.TestCase):
    def probe(self, runner, since="2026-10-20T00:00:00Z", baseline="0",
              now="2026-10-20T06:00:00Z", window="6"):
        stdout = io.StringIO()
        with mock.patch.object(night.subprocess, "run", side_effect=runner):
            with contextlib.redirect_stdout(stdout):
                code = night.main(["--since-utc", since, "--baseline-restarts", baseline,
                                   "--min-window-hours", window], now=night.parse_since(now))
        return code, json.loads(stdout.getvalue())
    def test_success_is_ok(self):
        code, report = self.probe(commands())
        self.assertEqual((code, report["status"]), (0, "ok"))
        self.assertIs(report["nightly_missing_thumbnails"], False)
        self.assertEqual((report["delta"], report["errors"]), (0, []))
        self.assertEqual(report["started_at"], "2026-10-19T20:00:00.123456789Z")
    def test_not_due_windows_run_nothing(self):
        def forbidden(args, **kwargs): raise AssertionError("no commands in a not-due window")
        for since in ("2026-10-20T09:00:00Z", "2026-10-20T02:00:00Z"):
            code, report = self.probe(forbidden, since=since)
            self.assertNotEqual(code, 0)
            self.assertEqual(report["status"], "not_due")
    def test_restart_increase_and_reset_fail(self):
        code, report = self.probe(commands(inspect="2|healthy|2026-10-19T20:00:00Z"))
        self.assertEqual((code, report["delta"], report["counter_reset"]), (1, 2, False))
        code, report = self.probe(commands(), baseline="5")
        self.assertEqual((code, report["delta"], report["counter_reset"]), (1, -5, True))
    def test_missing_nightly_flag_is_unknown_not_false(self):
        for value in ("", "null"):
            code, report = self.probe(commands(psql=value))
            self.assertEqual(code, 1)
            self.assertIsNone(report["nightly_missing_thumbnails"])
    def test_oom_counts_exclude_cgroup_and_emit_no_raw_lines(self):
        journal = ("Memory cgroup out of memory: Killed process 10 (node)\n"
                   "Out of memory: Killed process 11 (node)\n")
        code, report = self.probe(commands(journal=journal))
        self.assertEqual((code, report["cgroup_oom_count"], report["global_oom_count"]), (1, 1, 1))
        self.assertNotIn("Killed process", json.dumps(report))
    def test_journal_coverage_limit_fails(self):
        code, report = self.probe(commands(journal="\n".join("x" for _ in range(20001))))
        self.assertEqual((code, report["errors"]), (1, ["journalctl: coverage_limit"]))
    def test_journal_coverage_empty_or_malformed_fails(self):
        for value in ("", "{}", '{"__REALTIME_TIMESTAMP": "-1"}'):
            code, report = self.probe(commands(coverage=value))
            self.assertEqual((code, report["errors"]), (1, ["journalctl: coverage_unknown"]))
            self.assertIsNone(report["cgroup_oom_count"])
    def test_backup_age_fresh_stale_and_malformed(self):
        code, report = self.probe(commands())
        self.assertEqual((code, report["backups"][0]["age_hours"]), (0, 3.0))
        stale = OK_BACKUPS.replace("2026-10-20 03:00:00", "2026-10-18 06:00:00")
        code, report = self.probe(commands(systemctl=stale))
        self.assertEqual((code, report["backups"][0]["age_hours"]), (1, 48.0))
        bad = OK_BACKUPS.replace("2026-10-20 03:00:00 UTC", "not-a-time")
        code, report = self.probe(commands(systemctl=bad))
        self.assertEqual(code, 1)
        self.assertIsNone(report["backups"][0]["age_hours"])
    def test_failed_backup_or_empty_timestamp_fails(self):
        failed = OK_BACKUPS.replace("Result=success", "Result=failed", 1)
        code, _ = self.probe(commands(systemctl=failed))
        self.assertEqual(code, 1)
        empty = OK_BACKUPS.replace("2026-10-20 03:00:00 UTC", "", 1)
        code, report = self.probe(commands(systemctl=empty))
        self.assertEqual(code, 1)
        self.assertFalse(report["backups"][0]["exit_timestamp_present"])
    def test_failed_command_and_timeout_are_labeled(self):
        code, report = self.probe(commands(fail="systemctl"))
        self.assertEqual((code, report["errors"]), (1, ["systemctl: exit_1"]))
        def slow(args, **kwargs): raise night.subprocess.TimeoutExpired(cmd=args, timeout=kwargs["timeout"])
        code, report = self.probe(slow)
        self.assertEqual((code, report["errors"][0]), (1, "docker_inspect: TimeoutExpired"))
    def test_inspect_errors_are_labeled(self):
        for value in ("0|weird|2026-10-19T20:00:00Z", "x|healthy|2026-10-19T20:00:00Z"):
            code, report = self.probe(commands(inspect=value))
            self.assertEqual((code, report["errors"]), (1, ["docker_inspect: malformed", "docker_inspect_final: malformed"]))
            self.assertIsNone(report["health"])
        code, report = self.probe(commands(inspect="0|healthy|2026-10-20T01:00:00Z"))
        self.assertEqual((code, report["errors"]), (1, ["docker_inspect: start_in_window", "docker_inspect_final: start_in_window"]))
    def test_inspect_changed_midway_fails(self):
        code, report = self.probe(commands(inspect=("0|healthy|2026-10-19T20:00:00Z", "1|healthy|2026-10-19T20:00:00Z")))
        self.assertEqual((code, report["errors"], report["restart_count"]), (1, ["docker_inspect: changed"], 1))
if __name__ == "__main__":
    unittest.main(verbosity=2)
