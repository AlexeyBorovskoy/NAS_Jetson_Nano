#!/usr/bin/env python3
"""Regression tests for the DP-1/DEP-2 immutable Compose image gate.

The live services use persistent data and may migrate it during startup. A
mutable registry tag can turn an ordinary pull/recreate into an unreviewed
application and database upgrade. Every external ``image:`` key in the Jetson
and VPS Compose files must carry an exact sha256 manifest digest.

This test is intentionally Python 3.6 compatible and can run without pytest.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

REPO = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")
DIGEST = "sha256:" + ("a" * 64)


def read(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def run_gate(compose_files, vps_files=None):
    """Run ``preflight.sh --images-only`` against a temporary repository."""
    tmp = tempfile.mkdtemp()
    try:
        qdir = os.path.join(tmp, "scripts", "quality")
        os.makedirs(qdir)
        shutil.copy(
            os.path.join(REPO, "scripts", "quality", "preflight.sh"),
            os.path.join(qdir, "preflight.sh"),
        )
        for rel_dir, files in (
            (("docker", "compose"), compose_files),
            (("docker", "vps"), vps_files or {}),
        ):
            target = os.path.join(tmp, *rel_dir)
            os.makedirs(target)
            for name, body in files.items():
                with io.open(
                    os.path.join(target, name), "w", encoding="utf-8", newline="\n"
                ) as fh:
                    fh.write(body)
        git_bash = r"C:\Program Files\Git\bin\bash.exe"
        bash = git_bash if os.path.isfile(git_bash) else (shutil.which("bash") or "bash")
        proc = subprocess.run(
            [bash, os.path.join(qdir, "preflight.sh"), "--images-only"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def compose_with(image):
    return "services:\n  service:\n    image: %s\n" % image


class ComposeImagesPinned(unittest.TestCase):
    def test_every_repository_image_has_sha256_digest(self):
        seen = 0
        offenders = []
        for rel_dir in ("docker/compose", "docker/vps"):
            directory = os.path.join(REPO, *rel_dir.split("/"))
            for name in sorted(os.listdir(directory)):
                if not name.endswith((".yml", ".yaml")):
                    continue
                rel = rel_dir + "/" + name
                for lineno, line in enumerate(read(rel).splitlines(), 1):
                    stripped = line.strip()
                    if not stripped.startswith("image:"):
                        continue
                    seen += 1
                    reference = stripped.split(":", 1)[1].strip()
                    if not DIGEST_RE.search(reference):
                        offenders.append("%s:%d" % (rel, lineno))
        self.assertGreater(seen, 0, "no Compose image keys were checked")
        self.assertEqual([], offenders, "unpinned images: " + ", ".join(offenders))

    def test_gate_accepts_digest_even_when_human_tag_is_latest(self):
        rc, out = run_gate(
            {"docker-compose.yml": compose_with("example/app:latest@" + DIGEST)}
        )
        self.assertEqual(0, rc, out)

    def test_gate_rejects_latest_without_digest(self):
        rc, out = run_gate(
            {"docker-compose.yml": compose_with("example/app:latest")}
        )
        self.assertNotEqual(0, rc, out)
        self.assertIn("not pinned", out)

    def test_gate_rejects_version_tag_without_digest(self):
        rc, out = run_gate(
            {"docker-compose.yml": compose_with("example/app:1.2.3")}
        )
        self.assertNotEqual(0, rc, out)

    def test_gate_rejects_variable_default_without_digest(self):
        rc, out = run_gate(
            {"docker-compose.yml": compose_with("example/app:${VERSION:-1.2.3}")}
        )
        self.assertNotEqual(0, rc, out)

    def test_gate_scans_vps_compose_files(self):
        rc, out = run_gate(
            {"docker-compose.yml": compose_with("example/app:1@" + DIGEST)},
            {"docker-compose.yml": compose_with("example/vps:alpine")},
        )
        self.assertNotEqual(0, rc, out)
        self.assertIn("docker/vps", out)

    def test_gate_reports_empty_fixture(self):
        rc, out = run_gate({})
        self.assertEqual(0, rc, out)
        self.assertIn("docker/compose", out)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    failures = len(result.failures) + len(result.errors)
    if failures:
        print("[FAIL] failures: %d" % failures)
    sys.exit(1 if failures else 0)
