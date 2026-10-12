"""Every tests/unit/test_*.py must execute its tests when run as "python file".

History: preflight.sh runs each file as a script and trusts the exit code. Four
pytest-style files had no __main__ block, so running them executed nothing and
exited 0: test_container_watchdog.py and test_dl_egress_guard.py were counted as
passed by the gate from 2026-09-30 without ever running (found 2026-10-12).
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_RE = re.compile(r'^if __name__ == ["\']__main__["\']:', re.MULTILINE)


def missing_main(paths):
    return [p.name for p in paths if not MAIN_RE.search(p.read_text(encoding="utf-8"))]


class UnitTestsRunnable(unittest.TestCase):
    def test_every_unit_test_file_has_main_block(self):
        files = sorted((ROOT / "tests" / "unit").glob("test_*.py"))
        self.assertTrue(files)
        self.assertEqual(missing_main(files), [],
                         "add a __main__ block that runs the tests (unittest.main() or pytest.main)")

    def test_detects_file_without_main(self):
        tmp = ROOT / ".agent-work" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        sample = tmp / "test_sample_without_main.py"
        sample.write_text("def test_x():\n    assert True\n", encoding="utf-8")
        try:
            self.assertEqual(missing_main([sample]), ["test_sample_without_main.py"])
        finally:
            sample.unlink()


if __name__ == "__main__":
    sys.exit(not unittest.main(exit=False).result.wasSuccessful())
