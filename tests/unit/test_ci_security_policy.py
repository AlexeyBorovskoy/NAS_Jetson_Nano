#!/usr/bin/env python3
"""CI-1/SEC-1: security scanners must cover history and use immutable actions."""
import io
import os
import re
import sys
import unittest


REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
WORKFLOW = os.path.join(REPO, ".github", "workflows", "quality-checks.yml")


def read_workflow():
    with io.open(WORKFLOW, encoding="utf-8") as fh:
        return fh.read()


def security_job(text):
    start = text.index("  security:\n")
    end = text.index("  service-tests:\n", start)
    return text[start:end]


class CiSecurityPolicy(unittest.TestCase):
    def test_security_checkout_fetches_full_history(self):
        job = security_job(read_workflow())
        self.assertRegex(job, r"actions/checkout@v4\s+with:\s+fetch-depth:\s*0\b")

    def test_gitleaks_scans_git_history(self):
        job = security_job(read_workflow())
        self.assertNotIn("--no-git", job)
        self.assertIn("gitleaks detect", job)
        self.assertIn("Verify Gitleaks scans deleted history", job)
        self.assertIn('git -C "$probe_repo" commit', job)
        self.assertIn('probe_rc=$?', job)

    def test_trivy_action_is_pinned_to_sha_with_version_comment(self):
        job = security_job(read_workflow())
        refs = re.findall(r"aquasecurity/trivy-action@([^\s#]+)(?:\s+#\s*(v[^\s]+))?", job)
        self.assertEqual(1, len(refs), refs)
        sha, version = refs[0]
        self.assertRegex(sha, r"^[0-9a-f]{40}$")
        self.assertEqual("v0.36.0", version)
        self.assertNotIn("aquasecurity/trivy-action@master", job)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(1 if result.failures or result.errors else 0)
