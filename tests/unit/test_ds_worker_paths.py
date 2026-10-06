"""Owner 2026-10-06: nested agent artifacts must not enter git or main-copy reads."""
import subprocess
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_DENY = "//e/Linux mint/virtual_VM/shared/NAS_Jetson_Nano/"


class WorkerPathsTest(unittest.TestCase):
    def setUp(self):
        self.config = tomllib.loads((ROOT / "ds_worker.toml").read_text(encoding="utf-8"))

    def test_worktree_root_is_inside_project(self):
        target = (ROOT / self.config["git"]["worktree_root"]).resolve()
        self.assertTrue(target.is_relative_to(ROOT))
        self.assertEqual(target, ROOT / ".agent-work" / "worktrees")

    def test_current_tracked_root_children_have_main_copy_denies(self):
        # NUL paths stay literal even when CI enables quoting for Cyrillic names.
        files = subprocess.check_output(
            ["git", "-c", "core.quotepath=true", "ls-files", "-z"],
            cwd=ROOT, text=True, encoding="utf-8").split("\0")
        roots = {name.split("/", 1)[0] for name in files if name}
        denies = self.config["security"]["deny_read"]
        denied = {name[len(MAIN_DENY):].removesuffix("/**") for name in denies
                  if name.startswith(MAIN_DENY)}
        self.assertEqual(roots - denied, set())
        for mask in ("**/.agent-work/archives/**", "**/.agent-work/tmp/**", "**/.env*",
                     "**/.kilo/**", "**/ds_board/**"):
            self.assertIn(mask, denies)

    def test_local_artifacts_are_ignored(self):
        for name in ("worktrees", "archives", "tmp"):
            result = subprocess.run(["git", "check-ignore", ".agent-work/" + name + "/probe"],
                                    cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
