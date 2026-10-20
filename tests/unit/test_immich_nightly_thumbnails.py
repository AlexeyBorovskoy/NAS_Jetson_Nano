"""Synthetic tests for scripts/immich/nightly_thumbnails.py; no real network."""

import copy
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "..", "scripts", "immich", "nightly_thumbnails.py")
SPEC = importlib.util.spec_from_file_location("nightly_thumbnails", PATH)
nightly = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nightly)

CONFIG = {"nightlyTasks": {"missingThumbnails": True, "databaseCleanup": True},
          "library": {"scan": {"enabled": True, "interval": "daily"}, "import": {"paths": ["/a"]}},
          "user": {"theme": {"dark": False}}}
class NightlyThumbnailsTest(unittest.TestCase):
    def setUp(self):
        self.backup = mock.patch.object(
            nightly, "write_backup", return_value="/tmp/b.json").start()
        self.addCleanup(mock.patch.stopall)
    def run_main(self, argv, configs):
        mock.patch.object(nightly, "fetch_config", side_effect=configs).start()
        put = mock.patch.object(nightly, "put_config").start()
        out = io.StringIO()
        with redirect_stdout(out):
            code = nightly.main(argv)
        return code, out.getvalue(), put
    def test_show_never_puts(self):
        code, out, put = self.run_main([], [copy.deepcopy(CONFIG)])
        self.assertEqual(code, 0)
        self.assertFalse(put.called)
        self.assertEqual(out.splitlines(), [
            "nightlyTasks.missingThumbnails=true", "library.scan.enabled=true"])
    def test_disable_changes_only_leaf(self):
        config = copy.deepcopy(CONFIG)
        before = copy.deepcopy(config)
        expected = nightly.change_flag(config, False)
        code, _, put = self.run_main(["--disable"], [config, copy.deepcopy(config), expected])
        self.assertEqual(code, 0)
        sent = put.call_args[0][1]
        self.assertIs(sent["nightlyTasks"]["missingThumbnails"], False)
        self.assertIs(sent["nightlyTasks"]["databaseCleanup"], True)
        self.assertEqual(sent["library"], config["library"])
        self.assertEqual(sent["user"], config["user"])
        self.assertEqual(config, before)
        self.backup.assert_called_once_with(True)
    def test_change_flag_rejects_bad_shapes(self):
        cases = [([], True), (CONFIG, 1), ({"library": {}}, False),
                 ({"nightlyTasks": {"missingThumbnails": "yes"}}, False)]
        for config, enabled in cases:
            with self.assertRaises(nightly.ConfigError):
                nightly.change_flag(config, enabled)
    def test_disable_idempotent_no_put(self):
        config = copy.deepcopy(CONFIG)
        config["nightlyTasks"]["missingThumbnails"] = False
        code, _, put = self.run_main(["--disable"], [config])
        self.assertEqual(code, 0)
        self.assertFalse(put.called)
        self.backup.assert_not_called()
    def test_concurrency_mismatch_no_put(self):
        first = copy.deepcopy(CONFIG)
        second = copy.deepcopy(CONFIG)
        second["user"]["theme"]["dark"] = True
        code, _, put = self.run_main(["--disable"], [first, second])
        self.assertEqual(code, 1)
        self.assertFalse(put.called)
    def test_restore_only_target_leaf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "backup.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"nightlyTasks": {"missingThumbnails": True},
                           "library": {"scan": {"enabled": False}}}, handle)
            current = copy.deepcopy(CONFIG)
            current["nightlyTasks"]["missingThumbnails"] = False
            current["user"]["theme"]["dark"] = True
            code, _, put = self.run_main(
                ["--restore", path], [current, copy.deepcopy(current),
                                      nightly.change_flag(current, True)])
            self.assertEqual(code, 0)
            sent = put.call_args[0][1]
            self.assertIs(sent["nightlyTasks"]["missingThumbnails"], True)
            self.assertIs(sent["library"]["scan"]["enabled"], True)
            self.assertEqual(sent["library"]["scan"]["interval"], "daily")
            self.assertIs(sent["user"]["theme"]["dark"], True)
            self.backup.assert_called_once_with(False)
    def test_postcheck_mismatch_fails(self):
        first = copy.deepcopy(CONFIG)
        stale = copy.deepcopy(CONFIG)
        code, out, put = self.run_main(
            ["--disable"], [first, copy.deepcopy(first), stale])
        self.assertEqual(code, 1)
        self.assertTrue(put.called)
        self.assertNotIn("verification ok", out)
if __name__ == "__main__":
    unittest.main()
