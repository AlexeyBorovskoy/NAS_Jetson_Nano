#!/usr/bin/env python3
"""Инфраструктура качалки и Telegram-бота — статические гарантии.

ЗАЧЕМ. SOCKS на 0.0.0.0 открыл бы прокси всей LAN; секрет aria2 в argv виден в `ps`
хоста; контейнер без предела памяти на Jetson 4 ГБ может выдавить Immich; каталоги,
смонтированные в API на запись, дали бы боту удалять файлы семьи.
Запуск: python3 tests/unit/test_downloader_infra.py   (Python 3.6+, без pytest)
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

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def read(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class Infra(unittest.TestCase):
    def test_downloads_compose_limits_and_mounts(self):
        t = read("docker/compose/docker-compose.downloads.yml")
        self.assertIn("mem_limit: 192m", t)
        self.assertIn("/mnt/storage/downloads:/downloads/ssd", t)
        self.assertIn("/mnt/hdd2tb/Downloads:/downloads/hdd", t)
        self.assertIn("ARIA2_RPC_SECRET: ${ARIA2_RPC_SECRET:?", t)
        self.assertIn('"6800:6800"', t)
        self.assertIn('"6880:6880"', t)

    def test_api_sees_download_dirs_read_only(self):
        t = read("docker/compose/docker-compose.nas_jetson_nano-api.yml")
        self.assertIn("/mnt/storage/downloads:/dl/ssd:ro", t)
        self.assertIn("/mnt/hdd2tb/Downloads:/dl/hdd:ro", t)
        for key in ("TELEGRAM_BOT_ENABLED", "TELEGRAM_BOT_TOKEN", "TELEGRAM_USERS",
                    "TELEGRAM_FAMILY_CHAT_ID", "TELEGRAM_PROXY", "ARIA2_RPC_SECRET"):
            self.assertIn(key + ":", t)
        self.assertIn("socks5://172.17.0.1:1080", t)

    def test_socks_unit_binds_docker0_only(self):
        t = read("systemd/nas_jetson_nano-tg-socks.service")
        self.assertIn("-D 172.17.0.1:1080", t)
        self.assertNotRegex(t, r"-D\s+(0\.0\.0\.0:)?1080\b")
        for opt in ("ExitOnForwardFailure=yes", "BatchMode=yes", "ServerAliveInterval="):
            self.assertIn(opt, t)
        self.assertIn("Restart=always", t)

    def test_entrypoint_keeps_secret_out_of_argv(self):
        t = read("services/downloads/entrypoint.sh")
        self.assertNotIn("--rpc-secret", t)
        self.assertIn("rpc-secret=", t)

    def test_env_example_has_empty_keys(self):
        t = read("config/.env.example")
        for key in ("TELEGRAM_BOT_ENABLED=", "TELEGRAM_USERS=", "TELEGRAM_FAMILY_CHAT_ID=",
                    "ARIA2_RPC_SECRET=", "DL_SSD_MIN_FREE_GB=", "DL_HDD_MIN_FREE_GB=",
                    "DL_SSD_MAX_GB=", "DL_DAY_LIMIT="):
            self.assertIn(key, t)
        self.assertRegex(t, r"(?m)^ARIA2_RPC_SECRET=\s*$")
        self.assertRegex(t, r"(?m)^TELEGRAM_USERS=\s*$")

    def test_speed_timers(self):
        self.assertIn("OnCalendar=*-*-* 08:00:00", read("systemd/nas_jetson_nano-dl-speed-day.timer"))
        self.assertIn("OnCalendar=*-*-* 23:00:00", read("systemd/nas_jetson_nano-dl-speed-night.timer"))
        self.assertIn("aria2_speed.sh day", read("systemd/nas_jetson_nano-dl-speed-day.service"))
        self.assertIn("aria2_speed.sh night", read("systemd/nas_jetson_nano-dl-speed-night.service"))

    def test_speed_script_sends_secret_on_stdin_only(self):
        tmp = tempfile.mkdtemp()
        try:
            bindir = os.path.join(tmp, "bin")
            os.makedirs(bindir)
            stub = os.path.join(bindir, "curl")
            with io.open(stub, "w", encoding="utf-8", newline="\n") as fh:
                fh.write('#!/usr/bin/env bash\nprintf "%s\\n" "$*" > "$STUB_ARGS"\ncat > "$STUB_BODY"\n'
                         'printf \'{"result":"OK"}\'\n')
            os.chmod(stub, 0o755)
            env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""),
                       ARIA2_RPC_SECRET="S3CR3T", DL_DAY_LIMIT="6M",
                       STUB_ARGS=os.path.join(tmp, "args"), STUB_BODY=os.path.join(tmp, "body"))
            bash = shutil.which("bash") or "bash"
            for mode, limit in (("day", '"6M"'), ("night", '"0"')):
                p = subprocess.run([bash, os.path.join(REPO, "scripts", "downloads", "aria2_speed.sh"), mode],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                args = io.open(env["STUB_ARGS"], encoding="utf-8").read()
                body = io.open(env["STUB_BODY"], encoding="utf-8").read()
                self.assertNotIn("S3CR3T", args)
                self.assertIn('"token:S3CR3T"', body)
                self.assertIn('"max-overall-download-limit":' + limit, body)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=1)
