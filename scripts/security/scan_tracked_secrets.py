"""Heuristic tracked-file scanner with per-value exceptions and redacted findings."""
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

assignment = re.compile(
    r"(?<![A-Z0-9_])(?P<name>[A-Z0-9_]*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD|BEARER)[A-Z0-9_]*)"
    r"\s*[:=]\s*['\"]?(?P<value>[A-Za-z0-9_./+=:@-]{16,})"
)
private_key = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
placeholder = re.compile(
    r"(?:(?:change_me|replace_me|example|mock|REDACTED)(?:[_-][A-Za-z0-9_-]+)?|ВАШ_[A-Za-z0-9_]*|x{8,}|X{8,})\Z"
)

def allowed(name, value):
    if placeholder.fullmatch(value):
        return True
    if name.endswith(("_FILE", "_PATH")) and value.startswith("/"):
        return True
    if name.endswith(("_URL", "_URI", "_ENDPOINT")):
        try:
            parsed = urlsplit(value)
            return (parsed.scheme in ("http", "https") and bool(parsed.netloc)
                    and parsed.username is None and parsed.password is None)
        except ValueError:
            return False
    return False

try:
    probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if probe.returncode == 0 and probe.stdout.strip() == b"true":
        result = subprocess.run(["git", "ls-files", "--stage", "-z"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        files = []
        for item in result.stdout.split(b"\0"):
            if item:
                metadata, filename = item.split(b"\t", 1)
                if metadata.split()[0] != b"160000":  # Gitlinks are not files.
                    files.append(Path(os.fsdecode(filename)))
    else:
        files = [p for p in Path(".").rglob("*") if p.is_file() and ".git" not in p.parts]
except (OSError, subprocess.CalledProcessError):
    print("Cannot enumerate files for secret scan.", file=sys.stderr)
    sys.exit(1)

failed = False
for path in files:
    # Existing exclusions; Markdown is intentionally included.
    if path.name in (".env.example", ".gitignore", "check_no_secrets.sh") or path.suffix == ".zip":
        continue
    try:
        lines = path.read_bytes().decode("utf-8", errors="replace").splitlines()
    except OSError:
        print(f"Cannot read tracked file: {path}", file=sys.stderr)
        failed = True
        continue
    for number, line in enumerate(lines, 1):
        if private_key.search(line):
            print(f"{path}:{number}: private-key marker [REDACTED]")
            failed = True
        for match in assignment.finditer(line):
            name, value = match.group("name", "value")
            if not allowed(name, value):
                print(f"{path}:{number}: {name}=[REDACTED]")
                failed = True
if failed:
    print("Potential secret-like strings found. Review before publishing.", file=sys.stderr)
    sys.exit(1)
print("No obvious secrets found outside allowed files.")
