"""Stage 22: synthetic hosts only; no disks, copy operations or credentials."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / ".agent-work/tmp"
TMP.mkdir(parents=True, exist_ok=True)
BASH = shutil.which("bash")


def clean_env(**extra):
    """A git hook exports GIT_DIR/GIT_INDEX_FILE; a child git must not inherit them."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(extra)
    return env


@unittest.skipUnless(BASH, "bash unavailable")
class CriticalShell(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TMP)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "copy.calls"
        self.env = clean_env(PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
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

    def secrets(self, content, tracked=True, filename="settings.conf"):
        subprocess.run(["git", "init", "-q"], cwd=self.root, env=self.env, check=True, capture_output=True)
        file = self.root / filename
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        if tracked:
            subprocess.run(["git", "add", filename], cwd=self.root, env=self.env, check=True)
        return self.run_shell(ROOT / "scripts/security/check_no_secrets.sh")

    def test_hook_git_variables_do_not_reach_real_repo(self):
        # 2026-10-07: under the pre-commit hook GIT_DIR/GIT_INDEX_FILE leaked into
        # `git init`; the real repository got core.bare=true and settings.conf staged.
        decoy = Path(self.tmp.name) / "decoy.git"
        hook_env = {"GIT_DIR": decoy.as_posix(), "GIT_INDEX_FILE": (decoy / "index").as_posix()}
        with mock.patch.dict(os.environ, hook_env):
            self.setUp()
            self.secrets("PLAIN=1\n")
        self.assertFalse(decoy.exists())
        self.assertTrue((self.root / ".git").is_dir())

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

    # 2026-10-09: markdown docs are scanned; placeholders stay safe, while real
    # values must still fail redacted - never skipped by prose words, same-line
    # exceptions or paths with spaces.
    def test_tracked_markdown_secret_is_rejected_and_redacted(self):
        value = "synthetic" + "0123456789abcdef"
        result = self.secrets("SERVICE_TOKEN=" + value + "\n", filename="README.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SERVICE_TOKEN=", result.stdout)
        self.assertNotIn(value, result.stdout)

    def test_markdown_placeholder_change_me_is_allowed(self):
        placeholder = "change" + "_me"
        result = self.secrets("SERVICE_TOKEN=" + placeholder + "\n", filename="README.md")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_markdown_placeholder_example_is_allowed(self):
        placeholder = "exa" + "mple"
        result = self.secrets("SERVICE_TOKEN=" + placeholder + "\n", filename="README.md")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_markdown_secret_file_path_is_allowed(self):
        result = self.secrets("SERVICE_TOKEN_FILE=/run/secrets/service_token\n", filename="README.md")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_markdown_token_url_is_allowed(self):
        url = "https://iam.api.cloud.ru" + "/api/v1/auth/token"
        result = self.secrets("IAM_TOKEN_URL=" + url + "\n", filename="README.md")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_prose_example_does_not_suppress_markdown_secret(self):
        value = "synthetic" + "0123456789abcdef"
        content = "The example below is a mock value, not a real one: SERVICE_TOKEN=" + value + "\n"
        result = self.secrets(content, filename="README.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SERVICE_TOKEN=", result.stdout)

    def test_safe_file_assignment_does_not_hide_same_line_secret(self):
        value = "synthetic" + "0123456789abcdef"
        content = "SERVICE_TOKEN_FILE=/run/secrets/service_token SERVICE_TOKEN=" + value + "\n"
        result = self.secrets(content, filename="README.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SERVICE_TOKEN=", result.stdout)

    def test_placeholder_does_not_mask_second_candidate_on_line(self):
        value = "synthetic" + "0123456789abcdef"
        content = "SERVICE_TOKEN=" + "change" + "_me" + " SERVICE_TOKEN=" + value + "\n"
        result = self.secrets(content, filename="README.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SERVICE_TOKEN=", result.stdout)

    def test_markdown_private_key_marker_is_rejected(self):
        body = "synthetic" + "0123456789abcdef"
        begin = "-----BEGIN RSA PRIVATE " + "KEY-----"
        end = "-----END RSA PRIVATE " + "KEY-----"
        result = self.secrets(begin + "\n" + body + "\n" + end + "\n", filename="README.md")
        self.assertNotEqual(result.returncode, 0)

    def test_markdown_with_spaces_in_path_is_scanned(self):
        value = "synthetic" + "0123456789abcdef"
        result = self.secrets("SERVICE_TOKEN=" + value + "\n", filename="docs with spaces/README.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SERVICE_TOKEN=", result.stdout)

    def test_untracked_markdown_secret_is_excluded(self):
        value = "synthetic" + "0123456789abcdef"
        result = self.secrets("SERVICE_TOKEN=" + value + "\n", tracked=False, filename="README.md")
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
