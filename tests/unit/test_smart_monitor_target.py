#!/usr/bin/env python3
"""Цель SMART-монитора: только стабильные /dev/disk/by-id/, без sd-букв.

Буква /dev/sdX плавает между загрузками, а -part указывает на раздел.
Запуск: python3 tests/unit/test_smart_monitor_target.py
"""
import ast
import io
import os
import re
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ALERT = os.path.join(HERE, "..", "..", "scripts", "monitoring",
                     "nas_jetson_nano-talk-alert.py")
BY_ID = "/dev/disk/by-id/usb-TEST_ARCHIVE_DISK"
PASSED = "SMART overall-health self-assessment test result: PASSED\n"


def load_check():
    """Компилирует только check_hdd_smart из боевого файла (без импорта модуля)."""
    with io.open(ALERT, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in ("stable_hdd_target", "check_hdd_smart")]
    module = ast.Interactive(body=funcs)  # есть во всех Python 3.x
    ast.fix_missing_locations(module)
    return compile(module, ALERT, "single")


class SmartMonitorTarget(unittest.TestCase):
    def run_check(self, target, out=PASSED):
        ns = {"os": os, "re": re, "subprocess": mock.Mock(),
              "HDD_DEV": target,
              "HDD_FATAL_ATTRS": ("Reallocated_Sector_Ct",
                                  "Current_Pending_Sector",
                                  "Offline_Uncorrectable"),
              "HDD_TEMP_MAX": 50}
        exec(load_check(), ns)
        ns["subprocess"].run.return_value.stdout = out
        result = ns["check_hdd_smart"]()
        return result, ns["subprocess"].run

    def test_unset_target_never_runs_smartctl(self):
        result, run = self.run_check("")
        self.assertEqual(result[0], "hdd_smart")
        self.assertIn("не настроена", result[1])
        run.assert_not_called()

    def test_sd_letter_target_never_runs_smartctl(self):
        result, run = self.run_check("/dev/sdb")
        self.assertIn("не настроена", result[1])
        run.assert_not_called()

    def test_partition_target_never_runs_smartctl(self):
        result, run = self.run_check(BY_ID + "-part1")
        self.assertIn("не настроена", result[1])
        run.assert_not_called()

    def test_by_id_target_passed_is_quiet(self):
        result, run = self.run_check(BY_ID)
        self.assertEqual(result, ("hdd_smart", None))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args[0][0][-1], BY_ID)


if __name__ == "__main__":
    unittest.main()
