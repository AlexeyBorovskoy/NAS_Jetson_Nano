"""Регрессия чёрного ящика для blackbox.store.close_day.

Ожидается, что реализация со сжатием LZMA по умолчанию не уложится
в RLIMIT_AS 64 MiB, а реализация с ограниченным потреблением памяти,
сохраняющая формат XZ, пройдёт этот тест.
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BLACKBOX_IMPORT_ROOT = str(REPOSITORY_ROOT / "services" / "blackbox")

DAY = "2026-10-22"
JOURNAL_SIZE = 8 * 1024 * 1024
BLOCK_SIZE = 16 * 1024
_REPEATING_LINE = (
    b"2026-10-22T00:00:00Z synthetic close_day memory-budget record\n"
)

_CHILD_SOURCE = """
import os
import resource
import sys

MEMORY_LIMIT = 64 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
assert soft_limit == MEMORY_LIMIT, (soft_limit, MEMORY_LIMIT)
assert hard_limit == MEMORY_LIMIT, (hard_limit, MEMORY_LIMIT)

import_root = sys.argv[1]
hot_root = sys.argv[2]
day = sys.argv[3]
expected_size = int(sys.argv[4])
expected_sha256 = sys.argv[5]

sys.path.insert(0, import_root)

import blackbox.store

blackbox.store.close_day(hot_root, day)

journal_path = os.path.join(hot_root, day, "journal.log")
xz_path = journal_path + ".xz"
assert not os.path.exists(journal_path), (
    "close_day left the source journal in place: %s" % journal_path
)
assert os.path.isfile(xz_path), (
    "close_day did not create the expected XZ file: %s" % xz_path
)
assert os.path.getsize(xz_path) > 0, (
    "close_day created an empty XZ file: %s" % xz_path
)

import hashlib
import lzma

digest = hashlib.sha256()
total = 0
with lzma.open(xz_path, "rb") as compressed:
    while True:
        chunk = compressed.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)

actual_sha256 = digest.hexdigest()
assert total == expected_size, (total, expected_size)
assert actual_sha256 == expected_sha256, (actual_sha256, expected_sha256)
print("ok: %d bytes sha256=%s" % (total, actual_sha256))
"""


def _journal_block():
    copies = (BLOCK_SIZE + len(_REPEATING_LINE) - 1) // len(_REPEATING_LINE)
    block = (_REPEATING_LINE * copies)[:BLOCK_SIZE]
    if len(block) != BLOCK_SIZE:
        raise AssertionError("synthetic journal block has an unexpected size")
    return block


def _write_synthetic_journal(path, total_size):
    block = _journal_block()
    digest = hashlib.sha256()
    written = 0
    with open(path, "wb") as journal:
        while written < total_size:
            remaining = total_size - written
            chunk = block if remaining >= len(block) else block[:remaining]
            journal.write(chunk)
            digest.update(chunk)
            written += len(chunk)
    return written, digest.hexdigest()


class CloseDayMemoryBudgetTest(unittest.TestCase):
    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "resource.RLIMIT_AS semantics are Linux-specific",
    )
    def test_close_day_compresses_journal_under_64_mib_address_space(self):
        """Сжимает 8 MiB журнала в дочернем процессе с лимитом 64 MiB."""

        temp_parent = os.environ.get("NAS_TEST_TMP") or None
        if temp_parent:
            temp_parent = os.path.abspath(temp_parent)

        with tempfile.TemporaryDirectory(dir=temp_parent) as temp_root:
            temp_root = os.path.abspath(temp_root)
            hot_root = os.path.join(temp_root, "hot")
            day_dir = os.path.join(hot_root, DAY)
            os.makedirs(day_dir)
            journal_path = os.path.join(day_dir, "journal.log")

            expected_size, expected_sha256 = _write_synthetic_journal(
                journal_path, JOURNAL_SIZE
            )
            self.assertEqual(JOURNAL_SIZE, expected_size)

            command = [
                sys.executable,
                "-c",
                _CHILD_SOURCE,
                BLACKBOX_IMPORT_ROOT,
                hot_root,
                DAY,
                str(expected_size),
                expected_sha256,
            ]
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30,
            )
            failure_message = (
                "child process failed\n"
                "command: {!r}\n"
                "stdout:\n{}\n"
                "stderr:\n{}"
            ).format(command, completed.stdout, completed.stderr)
            self.assertEqual(completed.returncode, 0, failure_message)


if __name__ == "__main__":
    unittest.main()
