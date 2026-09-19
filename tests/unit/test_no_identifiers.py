#!/usr/bin/env python3
"""Идентификаторы семьи и сети не возвращаются в публичный репозиторий (этап C, C7).

ЗАЧЕМ ОН СУЩЕСТВУЕТ. Аудит 2026-09-19 (NAS-SEC-008; `audit_new` G05, H14): токены личных
комнат Talk и MAC-адреса домашней сети лежали в `CLAUDE.md`, CHANGELOG, сетевых
документах и даже в значениях по умолчанию кода (`config.py`, compose). Репозиторий
публичный. Значения перенесены в `docs/local/IDENTIFIERS.md` (вне git).

Проверка — по усечённым SHA-256: сами значения в тесте не хранятся, иначе тест
сам стал бы утечкой. Сканируется то, что отслеживает git (HEAD и рабочее дерево).
Запуск: python3 tests/unit/test_no_identifiers.py
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# sha256(value)[:16]: 6 токенов комнат Talk + 5 MAC (нижний регистр).
FORBIDDEN = {
    "162566de3fe03277", "5bc8ae769c250ca0", "ae7e66846bc06ae5", "b48605cdfe25c5e1",
    "45f85c19719ad254", "4aef3d9dafc37980",
    "f0f840995b106fe6", "0f8937607477e237", "16f3d5ad6315eddc", "a3ead650defe47a5",
    "9fba46296658b3e2",
}
TOKEN = re.compile(r"(?<![A-Za-z0-9])[a-z0-9]{8}(?![A-Za-z0-9])")
MAC = re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f:])")
TEXT = (".md", ".py", ".sh", ".yml", ".yaml", ".env", ".example", ".txt", ".json", ".html",
        ".conf", ".toml", ".service", ".timer", ".rules", ".ps1", ".js")


def h(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:16]


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, stdout=subprocess.PIPE)
    return [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


class NoIdentifiers(unittest.TestCase):

    def test_forbidden_hashes_are_well_formed(self):
        self.assertEqual(len(FORBIDDEN), 11)

    def test_tracked_files_are_clean(self):
        hits = []
        for rel in tracked():
            if not rel.lower().endswith(TEXT) and os.path.basename(rel) not in ("CLAUDE.md",):
                continue
            path = os.path.join(REPO, rel)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    for m in TOKEN.findall(line):
                        if h(m) in FORBIDDEN:
                            hits.append("%s:%d (token)" % (rel, n))
                    for m in MAC.findall(line):
                        if h(m.lower()) in FORBIDDEN:
                            hits.append("%s:%d (MAC)" % (rel, n))
        self.assertEqual(hits, [], "\n".join(hits))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    bad = len(result.failures) + len(result.errors)
    if bad:
        print("[FAIL] падений: %d" % bad)
    sys.exit(1 if bad else 0)
