#!/usr/bin/env python3
"""Хуки aria2 качалки: перенос готового на HDD и уборка отменённого.

ЗАЧЕМ. Готовое должно само оказаться в Downloads (иначе сын не найдёт его в шаре), а
отменённые 100 ГБ не должны остаться на HDD рядом с семейным архивом. Хук работает с
путями из аргументов aria2 — ошибка в разборе пути = rm -rf не того каталога, поэтому
границы проверены тестами.
Запуск: python3 tests/unit/test_aria2_hooks.py   (Python 3.6+, без pytest)
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HOOKS = os.path.join(REPO, "services", "downloads")
BASH = shutil.which("bash") or "bash"


def fwd(p):
    return p.replace("\\", "/")


class Hooks(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.ssd = os.path.join(self.t, "ssd", ".incomplete")
        self.hddi = os.path.join(self.t, "hdd", ".incomplete")
        self.final = os.path.join(self.t, "hdd")
        for d in (self.ssd, self.hddi):
            os.makedirs(d)
        # bash (в т.ч. Git Bash на Windows) сравнивает пути по «/» — отдаём прямые слэши
        self.env = dict(os.environ, DL_SSD_INCOMPLETE=fwd(self.ssd),
                        DL_HDD_INCOMPLETE=fwd(self.hddi), DL_FINAL=fwd(self.final))

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def run_hook(self, name, path):
        p = subprocess.run([BASH, os.path.join(HOOKS, name), "gid1", "1", fwd(path)],
                           env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        return p.returncode

    def touch(self, *parts):
        path = os.path.join(*parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("x")
        return path

    def test_single_file_from_ssd_lands_in_final(self):
        f = self.touch(self.ssd, "debian 12 — образ.iso")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(os.path.join(self.final, "debian 12 — образ.iso")))
        self.assertFalse(os.path.exists(f))

    def test_multi_file_torrent_moves_top_directory(self):
        f = self.touch(self.hddi, "Distro", "disc1", "a.bin")
        self.touch(self.hddi, "Distro", "b.bin")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(os.path.join(self.final, "Distro", "disc1", "a.bin")))
        self.assertTrue(os.path.exists(os.path.join(self.final, "Distro", "b.bin")))
        self.assertFalse(os.path.exists(os.path.join(self.hddi, "Distro")))

    def test_name_taken_gets_suffix_without_overwrite(self):
        self.touch(self.final, "a.iso")
        f = self.touch(self.ssd, "a.iso")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(os.path.join(self.final, "a (2).iso")))
        with open(os.path.join(self.final, "a.iso")) as fh:
            self.assertEqual(fh.read(), "x")

    def test_path_outside_download_roots_is_ignored(self):
        outside = self.touch(self.t, "elsewhere", "keep.txt")
        self.assertEqual(self.run_hook("on_complete.sh", outside), 0)
        self.assertTrue(os.path.exists(outside))

    def test_metadata_without_path_is_ignored(self):
        self.assertEqual(self.run_hook("on_complete.sh", ""), 0)

    def test_final_unavailable_keeps_file_and_fails(self):
        f = self.touch(self.ssd, "a.iso")
        shutil.rmtree(self.final)
        self.assertNotEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(f))

    def test_on_stop_removes_partial_top_item(self):
        f = self.touch(self.hddi, "Big", "part.bin")
        self.touch(self.hddi, "Big.aria2")
        self.assertEqual(self.run_hook("on_stop.sh", f), 0)
        self.assertFalse(os.path.exists(os.path.join(self.hddi, "Big")))
        self.assertFalse(os.path.exists(os.path.join(self.hddi, "Big.aria2")))
        self.assertTrue(os.path.isdir(self.hddi))

    def test_on_stop_never_touches_final_or_outside(self):
        kept = self.touch(self.final, "done.iso")
        outside = self.touch(self.t, "other", "x")
        self.assertEqual(self.run_hook("on_stop.sh", kept), 0)
        self.assertEqual(self.run_hook("on_stop.sh", outside), 0)
        self.assertTrue(os.path.exists(kept) and os.path.exists(outside))

    def test_on_stop_rejects_dot_dot(self):
        victim = self.touch(self.t, "victim.txt")
        self.assertEqual(self.run_hook("on_stop.sh", os.path.join(self.hddi, "..", "..", "victim.txt")), 0)
        self.assertTrue(os.path.exists(victim))


if __name__ == "__main__":
    unittest.main(verbosity=1)
