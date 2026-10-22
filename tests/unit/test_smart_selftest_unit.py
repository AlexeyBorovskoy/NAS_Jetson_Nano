"""Регрессия юнита недельного SMART-самотеста HDD.

Проверяется только текст юнита; диск и systemd не нужны.
"""
import unittest
from pathlib import Path

UNIT = Path(__file__).resolve().parents[2] / "systemd" / "nas_jetson_nano-hdd2tb-selftest.service"


class SmartSelftestUnitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = [line.strip() for line in UNIT.read_text(encoding="utf-8").splitlines()]
        cls.smartctl = [i for i, l in enumerate(cls.lines) if l.startswith("ExecStart=")]
        cls.guard = [i for i, l in enumerate(cls.lines) if l.startswith("ExecStartPre=")]

    def test_env_file_is_required(self):
        env = [l for l in self.lines if l.startswith("EnvironmentFile=")]
        self.assertEqual(env, ["EnvironmentFile=/etc/nas-smart-hdd.env"],
                         "EnvironmentFile должен быть обязательным (без префикса '-')")

    def test_guard_runs_before_smartctl(self):
        self.assertEqual(len(self.guard), 1, "ожидается ровно один ExecStartPre")
        self.assertEqual(len(self.smartctl), 1, "ожидается ровно один ExecStart")
        self.assertLess(self.guard[0], self.smartctl[0], "проверка должна идти до smartctl")
        self.assertEqual(self.lines[self.guard[0]],
                         "ExecStartPre=/usr/bin/test -b ${NAS_SMART_HDD_DEVICE}")

    def test_target_is_variable_not_sd_letter(self):
        self.assertEqual(self.lines[self.smartctl[0]],
                         "ExecStart=/usr/sbin/smartctl -t short -d sat ${NAS_SMART_HDD_DEVICE}")
        self.assertFalse([l for l in self.lines if "/dev/sd" in l],
                         "запасной путь /dev/sdX недопустим")

    def test_existing_properties_preserved(self):
        for expected in ("Type=oneshot", "Nice=15", "IOSchedulingClass=idle"):
            self.assertIn(expected, self.lines)
        self.assertIn("-t short", self.lines[self.smartctl[0]])
        self.assertIn("-d sat", self.lines[self.smartctl[0]])


if __name__ == "__main__":
    unittest.main()
