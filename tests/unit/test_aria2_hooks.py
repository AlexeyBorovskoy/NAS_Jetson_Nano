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

    def run_hook_with_env(self, name, path, extra_env):
        env = dict(self.env)
        env.update(extra_env)
        p = subprocess.run([BASH, os.path.join(HOOKS, name), "gid1", "1", fwd(path)],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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

    # --- Раунд 1 ревью: атомарный перенос, umask, UID контейнера --------------

    def test_failed_copy_leaves_no_partial_in_final(self):
        # Подмена mv, которая пишет часть данных по целевому пути и падает — как
        # оборвавшийся кросс-ФС mv (SSD .incomplete -> HDD Downloads).
        stub = os.path.join(self.t, "fake_mv.sh")
        with open(stub, "w", newline="\n") as fh:
            fh.write("#!/usr/bin/env bash\n"
                      'mkdir -p "$(dirname "$3")"\n'
                      'printf part > "$3"\n'
                      "exit 1\n")
        os.chmod(stub, 0o755)
        f = self.touch(self.ssd, "a.iso")
        rc = self.run_hook_with_env("on_complete.sh", f, {"DL_MV": fwd(stub)})
        self.assertNotEqual(rc, 0)
        self.assertTrue(os.path.exists(f))
        self.assertFalse(os.path.exists(os.path.join(self.final, "a.iso")))
        leftovers = [n for n in os.listdir(self.final) if n.startswith(".incoming.")]
        self.assertEqual(leftovers, [])

    def test_success_leaves_no_temp_in_final(self):
        f = self.touch(self.ssd, "a.iso")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        leftovers = [n for n in os.listdir(self.final) if n.startswith(".incoming.")]
        self.assertEqual(leftovers, [])

    def test_entrypoint_resets_umask_for_aria2(self):
        with open(os.path.join(HOOKS, "entrypoint.sh"), encoding="utf-8") as fh:
            text = fh.read()
        lines = text.splitlines()
        self.assertFalse(any(ln.strip() == "umask 077" for ln in lines),
                          "umask 077 должен встречаться только внутри подоболочки")
        self.assertIn("umask 077", text)
        self.assertTrue(any(ln.strip() == "umask 022" for ln in lines),
                         "после подоболочки umask должен вернуться к 022")

    def test_dockerfile_prepares_dirs_for_uid_1000(self):
        with open(os.path.join(HOOKS, "Dockerfile"), encoding="utf-8") as fh:
            text = fh.read()
        user_idx = text.find("USER 1000")
        self.assertGreater(user_idx, -1)
        chown_idx = text.find("chown -R dl:dl /config /downloads")
        self.assertGreater(chown_idx, -1)
        self.assertLess(chown_idx, user_idx)
        self.assertIn("apk add --no-cache aria2 bash busybox-extras unzip", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
