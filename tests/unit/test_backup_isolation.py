#!/usr/bin/env python3
"""Копии на HDD недоступны на запись через семейные шары (этап B, задача B2).

ЗАЧЕМ ОН СУЩЕСТВУЕТ. Аудит 2026-09-19 (NAS-BAK-002): `/mnt/hdd2tb` целиком смонтирован
на запись в Samba (шара `hdd2tb`) и в Nextcloud (`/HDD-2TB`, всем пользователям), а
копия фото Immich и restic-репозиторий лежат в `/mnt/hdd2tb/backups`. Шифровальщик на
любом ПК с подключённой шарой или ошибка члена семьи испортили бы и оригинал, и копию.

Решение — вложенный bind-mount `backups` только на чтение поверх rw-монтирования диска:
люди могут достать файл из копии, но не изменить её. Пишут в `backups/` только
таймеры хоста от root.

Запуск: python3 tests/unit/test_backup_isolation.py
"""
import io
import os
import re
import sys
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
COMPOSE = os.path.join(REPO, "docker", "compose")
VOLUME = re.compile(r'^\s*-\s*"?([^:"\s]+):([^:"\s]+)(?::([a-z,]+))?"?\s*$')


def volumes(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.lstrip().startswith("#"):
                continue
            m = VOLUME.match(line)
            if m and m.group(1).startswith("/"):
                out.append((m.group(1), m.group(2), m.group(3) or "rw"))
    return out


class BackupsReadOnlyForPeople(unittest.TestCase):

    def test_every_rw_hdd_mount_has_readonly_backups_overlay(self):
        checked = 0
        for name in sorted(os.listdir(COMPOSE)):
            if not name.endswith(".yml"):
                continue
            vols = volumes(os.path.join(COMPOSE, name))
            for host, cont, mode in vols:
                if host.rstrip("/") == "/mnt/hdd2tb" and "ro" not in mode.split(","):
                    checked += 1
                    want = (cont.rstrip("/") + "/backups")
                    overlay = [v for v in vols if v[0] == "/mnt/hdd2tb/backups" and v[1] == want]
                    self.assertTrue(overlay, "%s: нет overlay /mnt/hdd2tb/backups:%s:ro" % (name, want))
                    self.assertIn("ro", overlay[0][2].split(","), "%s: overlay backups не ro" % name)
        self.assertGreaterEqual(checked, 2, "ожидались Nextcloud и Samba")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    bad = len(result.failures) + len(result.errors)
    if bad:
        print("[FAIL] падений: %d" % bad)
    sys.exit(1 if bad else 0)
