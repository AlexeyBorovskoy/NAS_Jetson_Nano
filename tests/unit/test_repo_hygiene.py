"""CLI contract tests for the repository hygiene gate.

All Git inputs are synthetic repositories created beneath .agent-work/tmp. The
fixtures contain only harmless public test strings and exercise Git metadata,
not repository contents or credentials.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "quality" / "repo_hygiene.py"
TEMP_ROOT = ROOT / ".agent-work" / "tmp"


def clean_git_env():
    """Keep hook-provided Git paths from redirecting synthetic repositories."""
    return {key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")}


class RepoHygieneCliTests(unittest.TestCase):
    def setUp(self):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self._temp = tempfile.TemporaryDirectory(dir=str(TEMP_ROOT))
        self.repo = Path(self._temp.name) / "repo"
        self.repo.mkdir()
        self.policy_path = Path(self._temp.name) / "policy.json"
        self.policy = {
            "version": 1,
            "max_blob_bytes": 2097152,
            "root_files": ["README.md", "safe.sh", ".env.example"],
            "exceptions": {},
        }
        self.write_policy()
        self.git("init", "-q")
        self.git("config", "user.name", "Hygiene Test")
        self.git("config", "user.email", "hygiene-test@example.invalid")

    def tearDown(self):
        self._temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=str(self.repo), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=clean_git_env())

    def add(self, path, data=b"test fixture\n", commit=False):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.git("add", "--", path)
        if commit:
            self.git("commit", "-qm", "fixture")

    def write_policy(self):
        self.policy_path.write_text(json.dumps(self.policy), encoding="utf-8")

    def run_gate(self, mode="--staged", policy_path=None, use_default_policy=False):
        mode_args = ["--tree", "HEAD"] if mode == "--tree HEAD" else [mode]
        policy_args = [] if use_default_policy else [
            "--policy", str(policy_path or self.policy_path)
        ]
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *mode_args, *policy_args],
            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, env=clean_git_env(),
        )

    def test_hook_git_variables_do_not_redirect_synthetic_repo(self):
        decoy = Path(self._temp.name) / "decoy.git"
        decoy_index = decoy / "index"
        decoy_worktree = Path(self._temp.name) / "decoy-worktree"
        hook_env = {
            "GIT_DIR": str(decoy),
            "GIT_INDEX_FILE": str(decoy_index),
            "GIT_WORK_TREE": str(decoy_worktree),
        }
        with mock.patch.dict(os.environ, hook_env):
            self.git("init", "-q")
            self.add("README.md")
            result = self.run_gate()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.repo / ".git").is_dir())
        self.assertFalse(decoy.exists())
        self.assertFalse(decoy_index.exists())
        self.assertFalse(decoy_worktree.exists())

    def test_clean_allowed_root_files_pass(self):
        self.add("README.md")
        self.add("safe.sh")
        self.add(".env.example")
        self.assertEqual(self.run_gate().returncode, 0)

    def test_unknown_root_file_is_rejected(self):
        self.add("one-off-report.txt")
        self.assertEqual(self.run_gate().returncode, 1)

    def test_backup_named_files_are_allowed_when_in_approved_subdirectory(self):
        self.add("scripts/maintenance_backup.sh")
        self.add("tests/sample.fixtures")
        self.assertEqual(self.run_gate().returncode, 0)

    def test_archive_suffix_is_rejected_without_exception(self):
        self.add("artifacts/old-snapshot.zip")
        self.assertEqual(self.run_gate().returncode, 1)

    def test_archive_exception_allows_specific_path(self):
        self.policy["exceptions"] = {
            "artifacts/reference.zip": {
                "reason": "retained fixture", "allow": ["archive", "local_artifact"]
            }
        }
        self.write_policy()
        self.add("artifacts/reference.zip", b"synthetic archive placeholder")
        self.assertEqual(self.run_gate().returncode, 0)

    def test_agent_work_and_ds_board_cannot_be_exceptioned(self):
        self.policy["exceptions"] = {
            ".agent-work/tmp/example.txt": {
                "reason": "should remain forbidden", "allow": ["local_artifact"]
            },
            "ds_board/example.txt": {
                "reason": "should remain forbidden", "allow": ["local_artifact"]
            },
        }
        self.write_policy()
        self.add(".agent-work/tmp/example.txt")
        self.add("ds_board/example.txt")
        self.assertEqual(self.run_gate().returncode, 1)

    def test_artifacts_need_an_exact_local_artifact_exception(self):
        self.add("artifacts/scratch.txt")
        self.assertEqual(self.run_gate().returncode, 1)
        self.policy["exceptions"] = {
            "artifacts/scratch.txt": {
                "reason": "owner retained fixture", "allow": ["local_artifact"]
            }
        }
        self.write_policy()
        self.assertEqual(self.run_gate().returncode, 0)

    def test_utf8_and_spaces_in_paths_are_parsed(self):
        self.add("research/naïve notes/данные.txt")
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_staged_blob_size_is_used_instead_of_working_tree_size(self):
        self.policy["max_blob_bytes"] = 20
        self.write_policy()
        self.add("docs/size.txt", b"this staged blob is definitely over twenty bytes")
        (self.repo / "docs" / "size.txt").write_bytes(b"small")
        self.assertEqual(self.run_gate().returncode, 1)

    def test_size_exception_has_a_finite_explicit_path_ceiling(self):
        self.policy["max_blob_bytes"] = 20
        self.policy["exceptions"] = {
            "docs/large.txt": {
                "reason": "bounded retained fixture", "allow": ["oversize"], "max_bytes": 30
            }
        }
        self.write_policy()
        self.add("docs/large.txt", b"a" * 31)
        self.assertEqual(self.run_gate().returncode, 1)

    def test_size_exception_allows_blob_within_explicit_path_ceiling(self):
        self.policy["max_blob_bytes"] = 20
        self.policy["exceptions"] = {
            "docs/large.txt": {
                "reason": "bounded retained fixture", "allow": ["oversize"], "max_bytes": 30
            }
        }
        self.write_policy()
        self.add("docs/large.txt", b"a" * 21)
        self.assertEqual(self.run_gate().returncode, 0)

    def test_default_policy_comes_from_index_not_working_tree(self):
        policy_in_index = json.dumps(self.policy).encode("utf-8")
        self.add("scripts/quality/repo_hygiene_policy.json", policy_in_index)
        self.add("artifacts/blocked.txt")
        working_policy = dict(self.policy)
        working_policy["exceptions"] = {
            "artifacts/blocked.txt": {
                "reason": "working tree must not override staged policy",
                "allow": ["local_artifact"],
            }
        }
        (self.repo / "scripts/quality/repo_hygiene_policy.json").write_text(
            json.dumps(working_policy), encoding="utf-8"
        )
        result = self.run_gate(use_default_policy=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_default_tree_policy_comes_from_commit_not_working_tree(self):
        self.add("scripts/quality/repo_hygiene_policy.json",
                 json.dumps(self.policy).encode("utf-8"))
        self.add("artifacts/blocked.txt")
        self.git("commit", "-qm", "strict policy and blocked fixture")
        working_policy = dict(self.policy)
        working_policy["exceptions"] = {
            "artifacts/blocked.txt": {
                "reason": "working tree must not override committed policy",
                "allow": ["local_artifact"],
            }
        }
        (self.repo / "scripts/quality/repo_hygiene_policy.json").write_text(
            json.dumps(working_policy), encoding="utf-8"
        )
        result = self.run_gate("--tree HEAD", use_default_policy=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_invalid_policy_fields(self):
        invalid_policies = [
            ("boolean version", {"version": True}),
            ("empty root filename", {"root_files": [""]}),
            ("dot root filename", {"root_files": ["."]}),
            ("dotdot root filename", {"root_files": [".."]}),
            ("backslash root filename", {"root_files": [r"bad\name"]}),
            ("malformed allow", {
                "exceptions": {"artifacts/x": {"reason": "fixture", "allow": [{}]}}
            }),
            ("parent exception path", {
                "exceptions": {"../x": {"reason": "fixture", "allow": ["root"]}}
            }),
        ]
        for label, changes in invalid_policies:
            with self.subTest(label=label):
                policy = dict(self.policy)
                policy.update(changes)
                self.policy_path.write_text(json.dumps(policy), encoding="utf-8")
                self.assertEqual(self.run_gate().returncode, 2)

    def test_tree_mode_checks_commit_and_ignores_unstaged_and_index_additions(self):
        self.add("README.md", commit=True)
        self.add("uncommitted-root.txt", b"blocked if indexed")
        (self.repo / "uncommitted-root.txt").write_text("working tree only", encoding="utf-8")
        result = self.run_gate("--tree HEAD", None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exception_requires_nonempty_reason(self):
        self.policy["exceptions"] = {
            "artifacts/kept.txt": {"reason": "  ", "allow": ["local_artifact"]}
        }
        self.write_policy()
        self.add("artifacts/kept.txt")
        self.assertEqual(self.run_gate().returncode, 2)

    def test_generated_directory_is_rejected(self):
        self.add("service/__pycache__/module.pyc")
        self.assertEqual(self.run_gate().returncode, 1)


if __name__ == "__main__":
    unittest.main()
