#!/usr/bin/env python3
"""Vostro tunnel must pick a reachable VPS address on every start.

Defect history: 26.09-05.10 the office ISP dropped new flows to 95.163.176.103
while 193.8.215.130 passed; nas-offsite-tunnel ran autossh with the fixed new
address and retried it 8390 times, so 10222 (backup channel + bastion) was down.
On 02.09 the same office had it the other way round, so no single address is safe.
"""

import io
import os
import shutil
import socket
import subprocess
import sys
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "scripts", "setup", "nas-offsite-tunnel.sh")
DROPIN = os.path.join(ROOT, "systemd", "nas-offsite-tunnel.service.d",
                      "10-pick-address.conf")
BASH = shutil.which("bash") or "bash"


def run(candidates, port):
    env = dict(os.environ,
               NAS_VPS_CANDIDATES=candidates,
               NAS_VPS_PROBE_PORT=str(port),
               NAS_VPS_PROBE_TIMEOUT="4",
               # exec of `echo` prints the ssh argv instead of dialing out
               NAS_TUNNEL_SSH="echo")
    return subprocess.run([BASH, SCRIPT], env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=60)


class PickAddressTest(unittest.TestCase):
    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(8)
        self.port = self.listener.getsockname()[1]

    def tearDown(self):
        self.listener.close()

    def test_invalid_port_is_rejected_without_shell_execution(self):
        for port in ("0", "65536", "22;echo injected", "$(echo injected)"):
            p = run("127.0.0.1", port)
            self.assertEqual(p.returncode, 2)
            self.assertIn("invalid probe port", p.stderr.decode())
            self.assertEqual(p.stdout, b"")

    def test_invalid_probe_timeout_is_rejected(self):
        env = dict(os.environ, NAS_VPS_CANDIDATES="127.0.0.1",
                   NAS_VPS_PROBE_TIMEOUT="0", NAS_TUNNEL_SSH="echo")
        p = subprocess.run([BASH, SCRIPT], env=env, capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 2)
        self.assertIn(b"invalid probe timeout", p.stderr)

    def test_skips_unreachable_address_and_uses_next(self):
        # 127.0.0.2 is loopback too, but nothing listens there: refused.
        p = run("127.0.0.2 127.0.0.1", self.port)
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        self.assertEqual(p.returncode, 0, err)
        self.assertIn("127.0.0.2:%d unreachable" % self.port, err)
        self.assertIn("root@127.0.0.1", out)
        self.assertNotIn("root@127.0.0.2", out)

    def test_ssh_keeps_tunnel_contract(self):
        out = run("127.0.0.1", self.port).stdout.decode("utf-8", "replace")
        for needle in ("-N", "-R 10222:localhost:22", "ExitOnForwardFailure=yes",
                       "ServerAliveInterval=30", "BatchMode=yes",
                       "HostKeyAlias=nas-vps", "StrictHostKeyChecking=yes"):
            self.assertIn(needle, out)
        self.assertNotIn("accept-new", out)

    def test_invalid_candidate_is_skipped(self):
        p = run("bad;addr 127.0.0.1", self.port)
        self.assertEqual(p.returncode, 0)
        self.assertIn("skip invalid VPS address: bad;addr",
                      p.stderr.decode("utf-8", "replace"))

    def test_fails_loudly_when_nothing_reachable(self):
        p = run("127.0.0.2", self.port)
        self.assertEqual(p.returncode, 1)
        self.assertIn("ERROR: no VPS address reachable",
                      p.stderr.decode("utf-8", "replace"))
        self.assertEqual(p.stdout.decode("utf-8", "replace").strip(), "")


class DropInTest(unittest.TestCase):
    def test_dropin_replaces_autossh_and_lets_systemd_restart(self):
        with io.open(DROPIN, encoding="utf-8") as handle:
            lines = [l.strip() for l in handle if l.strip() and not l.startswith("#")]
        self.assertIn("[Service]", lines)
        # the empty ExecStart= must come first, or systemd refuses two ExecStart
        i = lines.index("ExecStart=")
        self.assertEqual(lines[i + 1], "ExecStart=/usr/local/sbin/nas-offsite-tunnel.sh")
        self.assertIn("Restart=always", lines)


if __name__ == "__main__":
    result = unittest.main(exit=False)
    failures = len(result.result.failures) + len(result.result.errors)
    print("[OK] offsite tunnel address pick" if not failures
          else "[FAIL] offsite tunnel address pick")
    sys.exit(1 if failures else 0)
