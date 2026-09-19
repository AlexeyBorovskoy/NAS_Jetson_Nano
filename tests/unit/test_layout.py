#!/usr/bin/env python3
"""Регрессионный тест единой раскладки хоста (scripts/lib/layout.sh + nas_layout.py).

ЗАЧЕМ ОН СУЩЕСТВУЕТ. 2026-09-08 на Jetson подтянули 98 коммитов с переименованием
NASA → NAS_Jetson_Nano. Файлы уже знали новые имена, а устройство жило по старым
(`~/nasa`, `/etc/nasa-monitor`, `nasa-*.service`). `ssd_hotplug_recovery.sh` звал
`/home/admin/nas_jetson_nano/.../storage_preflight.sh` — такого каталога нет, код 127,
авто-восстановление SSD молча не работало 11 дней (аудит 2026-09-19, NAS-STO-001).

Раскладка хоста — это конфигурация, а не код. Тест фиксирует три свойства:
  1. раскладка определяется одинаково в bash и в Python;
  2. на устройстве со старыми каталогами выбирается старая раскладка, на чистом
     хосте — целевая, явная настройка всегда сильнее автоопределения;
  3. скрипты, работающие на Jetson, не содержат захардкоженных путей хоста.

Запуск (без pytest, чтобы шло и на Jetson с Python 3.6):
    python3 tests/unit/test_layout.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
LIB_SH = os.path.join(REPO, "scripts", "lib", "layout.sh")
LIB_DIR = os.path.join(REPO, "scripts", "lib")

KEYS = ["NAS_PREFIX", "NAS_PROJECT_DIR", "NAS_ENV_FILE", "NAS_CONF_DIR",
        "NAS_LOG_DIR", "NAS_STATE_DIR", "NAS_SBIN_PREFIX", "NAS_UNIT_PREFIX",
        "NAS_OPT_DIR", "NAS_API_CONTAINER"]

BASH = shutil.which("bash")


def posix(path):
    return path.replace("\\", "/")


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("NAS_")}
    env.update(extra or {})
    return env


def bash_layout(env):
    script = 'source "$1" && for k in %s; do printf "%%s=%%s\\n" "$k" "${!k}"; done' % " ".join(KEYS)
    out = subprocess.run([BASH, "-c", script, "layout-test", posix(LIB_SH)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         universal_newlines=True, env=env)
    if out.returncode != 0:
        raise AssertionError("layout.sh failed: %s" % out.stderr)
    return dict(line.split("=", 1) for line in out.stdout.splitlines() if "=" in line)


def py_layout(env):
    sys.path.insert(0, LIB_DIR)
    try:
        import nas_layout
        return nas_layout.resolve(env)
    finally:
        sys.path.remove(LIB_DIR)


class LayoutResolution(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def env(self, **extra):
        base = {"NAS_LAYOUT_ROOT": posix(self.root)}
        base.update(extra)
        return clean_env(base)

    def mkdirs(self, *paths):
        for p in paths:
            os.makedirs(os.path.join(self.root, p.lstrip("/")), exist_ok=True)

    def both(self, env):
        return bash_layout(env), py_layout(env)

    def test_legacy_device_detected(self):
        # Живой Jetson 2026-09-19: есть только старые каталоги.
        self.mkdirs("/etc/nasa-monitor", "/var/log/nasa-monitor")
        for lay in self.both(self.env()):
            self.assertEqual(lay["NAS_PREFIX"], "nasa")
            self.assertEqual(lay["NAS_CONF_DIR"], "/etc/nasa-monitor")
            self.assertEqual(lay["NAS_LOG_DIR"], "/var/log/nasa-monitor")
            self.assertEqual(lay["NAS_UNIT_PREFIX"], "nasa")
            self.assertEqual(lay["NAS_SBIN_PREFIX"], "/usr/local/sbin/nasa")

    def test_fresh_host_gets_target_layout(self):
        for lay in self.both(self.env()):
            self.assertEqual(lay["NAS_PREFIX"], "nas_jetson_nano")
            self.assertEqual(lay["NAS_CONF_DIR"], "/etc/nas_jetson_nano-monitor")

    def test_migrated_host_is_not_legacy(self):
        # После Part B оба каталога могут временно сосуществовать — новый побеждает.
        self.mkdirs("/etc/nasa-monitor", "/etc/nas_jetson_nano-monitor")
        for lay in self.both(self.env()):
            self.assertEqual(lay["NAS_PREFIX"], "nas_jetson_nano")

    def test_layout_file_overrides_detection(self):
        self.mkdirs("/etc/nasa-monitor", "/etc")
        with open(os.path.join(self.root, "etc", "nas-layout.env"), "w") as fh:
            fh.write('# comment\nNAS_PREFIX="nas_jetson_nano"\nNAS_LOG_DIR=/srv/logs\n')
        for lay in self.both(self.env()):
            self.assertEqual(lay["NAS_PREFIX"], "nas_jetson_nano")
            self.assertEqual(lay["NAS_LOG_DIR"], "/srv/logs")
            self.assertEqual(lay["NAS_CONF_DIR"], "/etc/nas_jetson_nano-monitor")

    def test_explicit_env_beats_layout_file(self):
        self.mkdirs("/etc")
        with open(os.path.join(self.root, "etc", "nas-layout.env"), "w") as fh:
            fh.write("NAS_PREFIX=nas_jetson_nano\n")
        for lay in self.both(self.env(NAS_PREFIX="nasa")):
            self.assertEqual(lay["NAS_PREFIX"], "nasa")

    def test_project_dir_is_repo_by_default(self):
        bash, py = self.both(self.env())
        # Git Bash на Windows отдаёт /e/..., на Linux путь уже POSIX.
        bash_dir = re.sub(r"^/([a-zA-Z])/", r"\1:/", bash["NAS_PROJECT_DIR"]) if os.name == "nt" \
            else bash["NAS_PROJECT_DIR"]
        self.assertEqual(os.path.normcase(os.path.normpath(bash_dir)),
                         os.path.normcase(os.path.normpath(REPO)))
        self.assertEqual(os.path.normcase(os.path.normpath(py["NAS_PROJECT_DIR"])),
                         os.path.normcase(os.path.normpath(REPO)))

    def test_env_file_follows_project_dir(self):
        for lay in self.both(self.env(NAS_PROJECT_DIR="/home/admin/nasa")):
            self.assertEqual(lay["NAS_ENV_FILE"], "/home/admin/nasa/config/.env")

    def test_api_container_is_the_live_name(self):
        # Решение 2026-08-30: контейнер НЕ переименовывается (конфликт порта 8099).
        for lay in self.both(self.env()):
            self.assertEqual(lay["NAS_API_CONTAINER"], "homecloud_nasa_api")

    def test_bash_and_python_agree(self):
        self.mkdirs("/var/log/nasa-monitor")
        bash, py = self.both(self.env())
        for k in KEYS:
            if k == "NAS_PROJECT_DIR" or k == "NAS_ENV_FILE":
                continue  # форма пути различается на Windows (C:/ против /c/)
            self.assertEqual(bash[k], py[k], k)


# Скрипты, которые исполняются на Jetson. Хост-пути в них — только через layout.
DEVICE_SCRIPTS = [
    "scripts/storage/ssd_hotplug_recovery.sh",
    "scripts/monitoring/jms583_health.sh",
    "scripts/monitoring/usb_error_monitor.sh",
    "scripts/monitoring/nas_jetson_nano-daily-report.sh",
    "scripts/monitoring/nas_jetson_nano-send-report-telegram.sh",
    "scripts/monitoring/nas_jetson_nano-talk-alert.py",
    "scripts/diagnostics/smart_check.sh",
    "scripts/diagnostics/sd_wear_check.sh",
]
HOST_PATH = re.compile(
    r"/home/admin/(nasa|nas_jetson_nano)\b"
    r"|/(etc|var/log|var/lib)/(nasa|nas_jetson_nano)-monitor"
    r"|/usr/local/sbin/(nasa|nas_jetson_nano)-"
    r"|/opt/(nasa|nas_jetson_nano)/"
    # имена юнитов: на устройстве nasa-*, в git nas_jetson_nano-* — только через NAS_UNIT_PREFIX
    r"|\b(nasa|nas_jetson_nano)-[a-z0-9-]+\.(service|timer)\b"
    # H10: живой контейнер API называется homecloud_nasa_api (решение 2026-08-30)
    r"|homecloud_nas_jetson_nano_api")


class NoHardcodedHostPaths(unittest.TestCase):

    def test_device_scripts_use_layout(self):
        offenders = []
        for rel in DEVICE_SCRIPTS:
            with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    code = line.split("#", 1)[0] if not rel.endswith(".py") else line
                    if rel.endswith(".py") and line.lstrip().startswith("#"):
                        continue
                    if HOST_PATH.search(code):
                        offenders.append("%s:%d: %s" % (rel, n, line.strip()))
        self.assertEqual(offenders, [], "\n".join(offenders))


if __name__ == "__main__":
    if BASH is None:
        print("[SKIP] bash не найден")
        sys.exit(0)
    result = unittest.main(exit=False, verbosity=1).result
    bad = len(result.failures) + len(result.errors)
    if bad:
        print("[FAIL] падений: %d" % bad)
    sys.exit(1 if bad else 0)
