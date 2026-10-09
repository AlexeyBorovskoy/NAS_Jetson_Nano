"""DEP-1: direct pins, hashed transitive lock and mandatory Docker enforcement."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/nas_jetson_nano-api"


def lock_blocks(text):
    return [block for block in re.split(r"(?m)(?=^[a-zA-Z0-9_-]+==)", text) if block.strip()]


class DependencyLock(unittest.TestCase):
    def test_all_direct_dependencies_have_exact_versions(self):
        lines = [line for line in (SERVICE / "requirements.txt").read_text().splitlines()
                 if line.strip() and not line.startswith("#")]
        self.assertEqual(len(lines), 5)
        for line in lines:
            self.assertRegex(line, r"^[a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_,.-]+\])?==[0-9][a-zA-Z0-9_.+-]*$")

    def test_every_locked_requirement_has_sha256(self):
        blocks = lock_blocks((SERVICE / "requirements.lock").read_text())
        self.assertGreater(len(blocks), 5)
        for block in blocks:
            with self.subTest(requirement=block.splitlines()[0]):
                self.assertRegex(block, r"--hash=sha256:[0-9a-f]{64}\b")
                self.assertNotIn(">=", block.splitlines()[0].split(";", 1)[0])

    def test_direct_pins_match_lock_versions(self):
        lock = (SERVICE / "requirements.lock").read_text()
        for name, version in re.findall(r"(?m)^([a-zA-Z0-9_-]+)(?:\[[^]]+\])?==([^\s]+)$",
                                       (SERVICE / "requirements.txt").read_text()):
            self.assertRegex(lock, r"(?m)^" + re.escape(name) + "==" + re.escape(version) + r"(?:\s|$)")

    def test_platform_extras_and_removed_unused_password_library(self):
        lock = (SERVICE / "requirements.lock").read_text()
        self.assertRegex(lock, r"(?m)^uvloop==[^\n]+sys_platform != 'win32'")
        self.assertRegex(lock, r"(?m)^colorama==[^\n]+sys_platform == 'win32'")
        self.assertNotRegex(lock, r"(?m)^(?:passlib|bcrypt)==")

    def test_container_install_enforces_hashes_and_binary_packages(self):
        dockerfile = (SERVICE / "Dockerfile").read_text()
        self.assertIn("COPY requirements.txt requirements.lock /app/", dockerfile)
        self.assertIn("--require-hashes --only-binary=:all: -r /app/requirements.lock", dockerfile)


if __name__ == "__main__":
    unittest.main()
