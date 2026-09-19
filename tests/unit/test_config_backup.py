#!/usr/bin/env python3
"""Регрессионные тесты бэкапа конфигурации и файлов Nextcloud (этап B, задачи B1/B6).

ЗАЧЕМ ОН СУЩЕСТВУЕТ. Аудит 2026-09-19 (NAS-BAK-001): `.env` с секретами, `config.php`
Nextcloud, файлы Nextcloud (260 МБ) и пользователи Samba не копировались НИКУДА —
смерть SD-карты или SSD означала восстановление сервисов по памяти. Дампы БД при
этом копировались, и это создавало иллюзию «бэкап есть».

Свойства, которые фиксирует тест:
  1. план бэкапа содержит всё незаменимое, пути — из раскладки хоста;
  2. нет обязательного источника / не смонтирован диск → отказ ДО вызова restic
     (урок 16 дней «успешных» пустых бэкапов: тишина ≠ успех);
  3. успешный прогон оставляет штамп, неуспешный — нет;
  4. полный круг на настоящем restic: бэкап → проверка восстановления проходит,
     а неполный снапшот проверка восстановления ловит.

Запуск: python3 tests/unit/test_config_backup.py   (без pytest, Python 3.6+)
Настоящий restic: из PATH или RESTIC_REAL=<путь>; нет — круг пропускается.
"""
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
BACKUP = os.path.join(REPO, "scripts", "backup", "config_backup.sh")
DRILL = os.path.join(REPO, "scripts", "backup", "restore_drill.sh")
BASH = shutil.which("bash")
RESTIC_REAL = os.environ.get("RESTIC_REAL") or shutil.which("restic")


def posix(p):
    return p.replace("\\", "/")


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


class Env(object):
    """Фейковый хост: хранилище, HDD, тома docker, заглушки команд."""

    def __init__(self, fake_restic=True):
        # NAS_TEST_TMP: на Windows restic восстанавливает ACL `C:\Users` из снапшота и
        # запирает восстановленную копию — локально запускать вне C:\Users.
        self.root = tempfile.mkdtemp(dir=os.environ.get("NAS_TEST_TMP") or None)
        r = self.root
        self.storage = os.path.join(r, "mnt", "storage")
        self.hdd = os.path.join(r, "mnt", "hdd2tb")
        self.bin = os.path.join(r, "bin")
        self.log = os.path.join(r, "calls.log")
        self.state = os.path.join(r, "state")
        self.targets = os.path.join(r, "targets")
        self.project = os.path.join(r, "project")
        ok = "#!/bin/bash\nexit 0\n"
        # источники
        write(os.path.join(self.project, "config", ".env"), 'NEXTCLOUD_ADMIN_USER="admin"\n')
        write(os.path.join(r, "opt", "config", ".env"), "VPS_HOST=203.0.113.1\n")
        write(os.path.join(r, "etc", "monitor", "telegram.env"), "TELEGRAM_CHAT_ID=1\n")
        write(os.path.join(r, "etc", "nas-layout.env"), "NAS_PREFIX=nasa\n")
        write(os.path.join(self.storage, "nextcloud", "data", "alice", "files", "note.txt"), "hello\n")
        write(os.path.join(r, "vol", "nc_app", "config", "config.php"),
              "<?php\n$CONFIG = array (\n  'instanceid' => 'x',\n);\n")
        write(os.path.join(r, "vol", "samba", "users.db"), "nas\n")
        dumps = os.path.join(self.storage, "backups", "database-dumps")
        os.makedirs(dumps)
        import gzip
        with gzip.open(os.path.join(dumps, "nextcloud_20260919_030155.sql.gz"), "wb") as g:
            g.write(b"-- dump\n")
        os.makedirs(self.hdd)
        # заглушки
        vol = posix(os.path.join(r, "vol"))
        write(os.path.join(self.bin, "docker"),
              '#!/bin/bash\necho "docker $*" >> "%s"\n'
              'case "$*" in\n'
              '  *nextcloud_nextcloud_app*) echo "%s/nc_app" ;;\n'
              '  *samba_samba_data*) echo "%s/samba" ;;\n'
              '  *) exit 1 ;;\nesac\n' % (posix(self.log), vol, vol), 0o755)
        write(os.path.join(self.bin, "mountpoint"), ok, 0o755)
        if fake_restic:
            write(os.path.join(self.bin, "restic"),
                  '#!/bin/bash\necho "restic $*" >> "%s"\nexit ${FAKE_RESTIC_RC:-0}\n' % posix(self.log), 0o755)
        else:
            write(os.path.join(self.bin, "restic"),
                  '#!/bin/bash\nexec "%s" "$@"\n' % posix(RESTIC_REAL), 0o755)
        os.makedirs(self.targets)
        os.makedirs(self.state)

    def add_target(self, name, repo, requires_mount=None):
        pw = os.path.join(self.root, "pw-" + name)
        write(pw, "test-password\n", 0o600)
        # правило №8: значения в кавычках (в путях стенда бывают пробелы)
        text = 'RESTIC_REPOSITORY="%s"\nRESTIC_PASSWORD_FILE="%s"\n' % (posix(repo), posix(pw))
        if requires_mount:
            text += 'REQUIRES_MOUNT="%s"\n' % posix(requires_mount)
        write(os.path.join(self.targets, name + ".env"), text, 0o600)

    def env(self, **extra):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("NAS_", "RESTIC_"))}
        e.update({
            "PATH": posix(self.bin) + os.pathsep + e.get("PATH", ""),
            "NAS_PROJECT_DIR": posix(self.project),
            "NAS_ENV_FILE": posix(os.path.join(self.project, "config", ".env")),
            "NAS_OPT_DIR": posix(os.path.join(self.root, "opt")),
            "NAS_CONF_DIR": posix(os.path.join(self.root, "etc", "monitor")),
            "NAS_STATE_DIR": posix(self.state),
            "NAS_LAYOUT_FILE": posix(os.path.join(self.root, "etc", "nas-layout.env")),
            "NAS_STORAGE_ROOT": posix(self.storage),
            "NAS_HDD_ROOT": posix(self.hdd),
            "NAS_BACKUP_TARGETS_DIR": posix(self.targets),
        })
        e.update(extra)
        return e

    def run(self, script, *args, **extra):
        return subprocess.run([BASH, posix(script)] + list(args), env=self.env(**extra),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True)

    def calls(self):
        if not os.path.exists(self.log):
            return ""
        with open(self.log, encoding="utf-8") as fh:
            return fh.read()

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class Plan(unittest.TestCase):
    def setUp(self):
        self.h = Env()

    def tearDown(self):
        self.h.close()

    def test_plan_lists_everything_irreplaceable(self):
        out = self.h.run(BACKUP, "--plan")
        self.assertEqual(out.returncode, 0, out.stdout)
        for needle in ("config/.env", "opt/config/.env", "etc/monitor", "nas-layout.env",
                       "nextcloud/data", "nc_app/config", "vol/samba", "database-dumps"):
            self.assertIn(needle, out.stdout, needle)
        self.assertNotIn("restic ", self.h.calls())

    def test_missing_required_source_refuses_before_restic(self):
        shutil.rmtree(os.path.join(self.h.storage, "nextcloud"))
        self.h.add_target("hdd", os.path.join(self.h.hdd, "repo"))
        out = self.h.run(BACKUP)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("nextcloud", out.stdout)
        self.assertNotIn("restic ", self.h.calls())

    def test_no_targets_is_an_error(self):
        out = self.h.run(BACKUP)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("target", out.stdout.lower())

    def test_unmounted_target_disk_refuses(self):
        self.h.add_target("hdd", os.path.join(self.h.hdd, "repo"), requires_mount=self.h.hdd)
        write(os.path.join(self.h.bin, "mountpoint"), "#!/bin/bash\nexit 1\n", 0o755)
        out = self.h.run(BACKUP)
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn("restic backup", self.h.calls())


class Run(unittest.TestCase):
    def setUp(self):
        self.h = Env()
        self.h.add_target("hdd", os.path.join(self.h.hdd, "repo"))

    def tearDown(self):
        self.h.close()

    def test_success_backs_up_prunes_and_stamps(self):
        out = self.h.run(BACKUP)
        self.assertEqual(out.returncode, 0, out.stdout)
        calls = self.h.calls()
        self.assertIn("restic backup", calls)
        self.assertIn("--keep-daily 7", calls)
        self.assertIn("--keep-monthly 6", calls)
        self.assertTrue(os.path.exists(os.path.join(self.h.state, "config-backup-hdd.stamp")))

    def test_restic_failure_fails_run_and_leaves_no_stamp(self):
        out = self.h.run(BACKUP, FAKE_RESTIC_RC="1")
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.h.state, "config-backup-hdd.stamp")))


@unittest.skipIf(not RESTIC_REAL, "настоящий restic не найден")
class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.h = Env(fake_restic=False)
        self.repo = os.path.join(self.h.hdd, "restic-config")
        self.h.add_target("hdd", self.repo)

    def tearDown(self):
        self.h.close()

    def test_backup_then_drill_passes(self):
        init = self.h.run(BACKUP, "--init")
        self.assertEqual(init.returncode, 0, init.stdout)
        out = self.h.run(BACKUP)
        self.assertEqual(out.returncode, 0, out.stdout)
        drill = self.h.run(DRILL, "hdd")
        self.assertEqual(drill.returncode, 0, drill.stdout)
        self.assertIn("DRILL OK", drill.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.h.state, "restore-drill-hdd.stamp")))

    def test_drill_catches_incomplete_snapshot(self):
        self.assertEqual(self.h.run(BACKUP, "--init").returncode, 0)
        # config.php пропал к моменту бэкапа — снапшот неполный, drill обязан упасть
        os.remove(os.path.join(self.h.root, "vol", "nc_app", "config", "config.php"))
        self.h.run(BACKUP, NAS_BACKUP_ALLOW_PARTIAL="1")
        drill = self.h.run(DRILL, "hdd")
        self.assertNotEqual(drill.returncode, 0, drill.stdout)
        self.assertIn("config.php", drill.stdout)


if __name__ == "__main__":
    if BASH is None:
        print("[SKIP] bash не найден")
        sys.exit(0)
    result = unittest.main(exit=False, verbosity=1).result
    bad = len(result.failures) + len(result.errors)
    if bad:
        print("[FAIL] падений: %d" % bad)
    sys.exit(1 if bad else 0)
