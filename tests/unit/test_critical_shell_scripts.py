"""Stage 22: synthetic hosts only; no disks, copy operations or credentials."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / ".agent-work/tmp"
TMP.mkdir(parents=True, exist_ok=True)
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "bash unavailable")
class CriticalShell(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TMP)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "copy.calls"
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        startup = self.root / "startup.sh"
        startup.write_text('bin="$TEST_BIN"\nif command -v cygpath >/dev/null; then bin="$(cygpath -u "$bin")"; fi\nexport PATH="$bin:$PATH"\n', encoding="utf-8")
        self.env["TEST_BIN"] = self.bin.as_posix()
        self.env["BASH_ENV"] = startup.as_posix()

    def run_shell(self, script):
        return subprocess.run([BASH, str(script)], cwd=self.root, env=self.env,
                              text=True, capture_output=True, timeout=15)

    def stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/bin/bash\n" + body, encoding="utf-8", newline="\n")
        p.chmod(0o755)

    def backup(self, source=True, hdd=True, free=100, dry=False):
        src, disk, dst = (self.root / x for x in ("source", "hdd", "dest"))
        if source:
            src.mkdir()
        if hdd:
            disk.mkdir()
        text = (ROOT / "scripts/backup/immich_hdd_second_copy.sh").read_text(encoding="utf-8")
        # Relocate the script's fixed HDD path into a synthetic host, preserving logic.
        script = self.root / "copy.sh"
        text = text.replace("[[ ! -d /mnt/hdd2tb ]]", '[[ ! -d "$TEST_HDD" ]]')
        text = text.replace("--output=avail /mnt/hdd2tb", '--output=avail "$TEST_HDD"')
        script.write_text(text, encoding="utf-8")
        self.env["TEST_HDD"] = disk.as_posix()
        self.stub("df", f"printf 'Avail\\n{free}G\\n'\n")
        self.stub("rsync", f'printf "%s\\n" "$*" > "{self.calls.as_posix()}"\n')
        self.env.update(IMMICH_SRC=src.as_posix(), IMMICH_DST=dst.as_posix(), DRY_RUN=str(int(dry)))
        return self.run_shell(script), dst

    def test_missing_source_no_copy(self):
        result, dst = self.backup(source=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())
        self.assertFalse(dst.exists())

    def test_missing_hdd_no_copy(self):
        result, dst = self.backup(hdd=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())
        self.assertFalse(dst.exists())

    def test_low_space_no_copy(self):
        result, dst = self.backup(free=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())
        self.assertFalse(dst.exists())

    def test_success_and_dry_run_never_delete(self):
        result, _ = self.backup(dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.calls.read_text()
        self.assertIn("--dry-run", args)
        self.assertNotIn("--delete", args)
        self.assertNotIn("--remove-source-files", args)

    def secrets(self, content, tracked=True):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        file = self.root / "settings.conf"
        file.write_text(content, encoding="utf-8")
        if tracked:
            subprocess.run(["git", "add", "settings.conf"], cwd=self.root, check=True)
        return self.run_shell(ROOT / "scripts/security/check_no_secrets.sh")

    def test_synthetic_secret_is_rejected(self):
        result = self.secrets("SERVICE_TOKEN=" + "synthetic" + "0123456789abcdef" + "\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SERVICE_TOKEN=", result.stdout)

    def test_secret_file_path_is_allowed(self):
        result = self.secrets("SERVICE_TOKEN_FILE=/run/secrets/service_token\n")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_untracked_secret_is_excluded(self):
        result = self.secrets("SERVICE_TOKEN=" + "synthetic" + "0123456789abcdef" + "\n", tracked=False)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
