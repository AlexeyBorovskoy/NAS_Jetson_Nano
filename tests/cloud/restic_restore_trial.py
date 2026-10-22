#!/usr/bin/env python3
"""Synthetic restic restore harness (Python 3.10+, stdlib only, offline).

Usage: python restic_restore_trial.py OUTDIR RESTIC_BINARY

Creates OUTDIR (must not pre-exist), builds a deterministic synthetic source tree,
initialises a NEW LOCAL restic repository inside OUTDIR with a fresh os.urandom
password file (mode 0600, never printed/copied/hashed/reported), runs
init / backup <abs source> / check --read-data / restore latest / restore latest
--include **/config/app.json with a minimal explicit environment, captured output,
timeout=120s and one log per command under OUTDIR/logs. Then requires the full
restore to match the source map exactly (name, size, SHA256, mode) and requires the
partial restore to be an incomplete strict subset. Writes and prints
OUTDIR/summary.json. Any failure raises, keeps logs local and never claims success.

No network, no deletion/prune/forget, no shell=True, no shell commands, no chmod
outside OUTDIR, no real configuration or host data.
"""

import hashlib
import json
import os
import random
import stat
import subprocess
import sys
import time
from pathlib import Path

DATA_COUNT = 32
DATA_SIZE = 65536
EMPTY_REL = "data/empty.bin"
CONFIG_REL = "config/app.json"
UNICODE_REL = "unicode/данные-Δ-пример.txt"
PRIVATE_REL = "private/mode_0600.bin"
PRIVATE_MODE = 0o600
EXPECTED_FILES = DATA_COUNT + 4
CHUNK = 1 << 20
TIMEOUT = 120.0
BASE_PATH = "/usr/local/bin:/usr/bin:/bin"
SEED_NS = "synthetic-restic-v1"


def payload(seed: str, size: int) -> bytes:
    """Deterministic bytes: version-stable string seeding (no hash()) + MT randbytes."""
    return random.Random(f"{SEED_NS}:{seed}").randbytes(size)


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def fake_config() -> bytes:
    doc = {
        "synthetic": True,
        "note": "clearly fake values, not a real configuration",
        "api_key": "FAKE-DO-NOT-USE-0000",
        "database": {"host": "db.invalid", "name": "fake_synthetic_db",
                     "user": "fake_user", "password": "not-a-real-password"},
        "backup": {"family_manifest": False, "retention_days": 0},
    }
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_source(source: Path) -> None:
    source.mkdir(mode=0o700)
    for index in range(DATA_COUNT):
        write_file(source / "data" / f"file_{index:03d}.bin",
                   payload(f"data-{index}", DATA_SIZE))
    write_file(source / EMPTY_REL, b"")
    write_file(source / CONFIG_REL, fake_config())
    write_file(source / UNICODE_REL, b"synthetic unicode payload\n")
    private_path = source / PRIVATE_REL
    write_file(private_path, payload("private", 1024))
    os.chmod(private_path, PRIVATE_MODE)


def sha256_stream(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), total


def file_map(base: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    if not base.is_dir():
        return result
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            info = os.lstat(full)
            if not stat.S_ISREG(info.st_mode):
                raise RuntimeError(f"unexpected non-regular entry: {full}")
            digest, size = sha256_stream(full)
            result[full.relative_to(base).as_posix()] = {
                "size": size, "sha256": digest,
                "mode": stat.S_IMODE(info.st_mode),
            }
    return result


def check_synthetic(map_: dict[str, dict[str, object]]) -> None:
    for index in range(DATA_COUNT):
        rel = f"data/file_{index:03d}.bin"
        if map_.get(rel, {}).get("size") != DATA_SIZE:
            raise RuntimeError(f"synthetic data file missing/sized wrongly: {rel}")
    if map_.get(EMPTY_REL, {}).get("size") != 0:
        raise RuntimeError("synthetic empty file missing or not empty")
    if map_.get(CONFIG_REL, {}).get("size", 0) <= 0:
        raise RuntimeError("synthetic fake config missing or empty")
    if UNICODE_REL not in map_:
        raise RuntimeError("synthetic Unicode filename missing")
    if map_.get(PRIVATE_REL, {}).get("mode") != PRIVATE_MODE:
        raise RuntimeError("synthetic private file missing or mode != 0600")
    if len(map_) != EXPECTED_FILES:
        raise RuntimeError(f"unexpected synthetic file count: {len(map_)}")


def snapshot_base(target: Path, source: Path) -> Path:
    return target / source.as_posix().lstrip("/")


def describe_diff(expected: dict, actual: dict, limit: int = 8) -> str:
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    differ = sorted(r for r in set(expected) & set(actual) if expected[r] != actual[r])
    parts = []
    if missing:
        parts.append(f"missing({len(missing)})={missing[:limit]}")
    if extra:
        parts.append(f"unexpected({len(extra)})={extra[:limit]}")
    if differ:
        parts.append(f"differing({len(differ)})={differ[:limit]}")
    return "; ".join(parts) or "no difference"


def run_cmd(name: str, argv: list[str], env: dict[str, str],
            log_dir: Path) -> dict[str, object]:
    log_path = log_dir / f"{name}.log"
    start = time.monotonic()
    try:
        proc = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - start
        log_path.write_text(
            f"argv={argv!r}\ntimeout={TIMEOUT}\nelapsed_seconds={elapsed:.3f}\n",
            encoding="utf-8")
        raise RuntimeError(f"command timed out after {TIMEOUT}s: {name}") from exc
    elapsed = time.monotonic() - start
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    log_path.write_text(
        f"argv={argv!r}\nexit_code={proc.returncode}\n"
        f"elapsed_seconds={elapsed:.3f}\n--- stdout ---\n{out}"
        f"\n--- stderr ---\n{err}\n", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {name}: {err.strip()[:400]}")
    return {"exit_code": proc.returncode, "elapsed": elapsed}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    outdir = Path(argv[1])
    restic = Path(argv[2])
    if not outdir.is_absolute():
        raise SystemExit("OUTDIR must be an absolute path")
    if outdir.exists():
        raise SystemExit(f"OUTDIR already exists, refusing to touch it: {outdir}")
    if not restic.is_file() or not os.access(restic, os.X_OK):
        raise SystemExit(f"RESTIC_BINARY is not an executable file: {restic}")

    os.umask(0o077)
    outdir.mkdir(mode=0o700)
    logs = outdir / "logs"
    logs.mkdir(mode=0o700)
    cache_dir = outdir / "cache"
    cache_dir.mkdir(mode=0o700)
    tmp = outdir / "tmp"
    tmp.mkdir(mode=0o700)
    source = outdir / "source"
    build_source(source)

    source_map = file_map(source)
    check_synthetic(source_map)
    source_bytes = sum(int(info["size"]) for info in source_map.values())

    password_file = outdir / "restic_password"
    with open(password_file, "wb") as handle:
        handle.write(os.urandom(32).hex().encode("ascii") + b"\n")
    os.chmod(password_file, 0o600)  # inside OUTDIR only

    env = {
        "PATH": BASE_PATH,
        "TMPDIR": str(tmp),
        "RESTIC_CACHE_DIR": str(cache_dir),
        "RESTIC_REPOSITORY": str(outdir / "repo"),
        "RESTIC_PASSWORD_FILE": str(password_file),
        "GOMAXPROCS": "2",
        "GOMEMLIMIT": "256MiB",
    }
    binary = str(restic)
    restored = outdir / "restored"
    partial = outdir / "partial"

    commands = [
        ("01-init", [binary, "init"], True),
        ("02-backup", [binary, "backup", str(source)], True),
        ("03-check", [binary, "check", "--read-data"], True),
        ("04-restore-full", [binary, "restore", "latest", "--target", str(restored)], True),
        ("05-restore-partial", [binary, "restore", "latest", "--include",
                               "**/config/app.json", "--target", str(partial)], False),
    ]
    exit_codes: dict[str, int] = {}
    elapsed: dict[str, float] = {}
    try:
        for name, cmd, required in commands:
            result = run_cmd(name, cmd, env, logs)
            exit_codes[name] = int(result["exit_code"])
            elapsed[name] = round(float(result["elapsed"]), 3)
        restored_map = file_map(snapshot_base(restored, source))
        exact = restored_map == source_map
        partial_map = file_map(snapshot_base(partial, source))
        partial_ok = (set(partial_map) == {CONFIG_REL}
                      and all(partial_map[r] == source_map[r] for r in partial_map))
        incomplete = (partial_map != source_map) and partial_ok
        restore_elapsed = elapsed["04-restore-full"]
        summary = {
            "success": bool(exact and incomplete),
            "source_file_count": len(source_map),
            "restored_file_count": len(restored_map),
            "partial_file_count": len(partial_map),
            "source_bytes": source_bytes,
            "exact_hashes_and_modes_match": bool(exact),
            "incomplete_restore_detected": bool(incomplete),
            "command_exit_codes": exit_codes,
            "command_elapsed_seconds": elapsed,
            "restore_elapsed_seconds": restore_elapsed,
            "synthetic_only": True,
            "local_repository_only": True,
        }
    except Exception:
        summary = {
            "success": False,
            "source_file_count": len(source_map),
            "restored_file_count": 0,
            "source_bytes": source_bytes,
            "exact_hashes_and_modes_match": False,
            "incomplete_restore_detected": False,
            "command_exit_codes": exit_codes,
            "command_elapsed_seconds": elapsed,
            "restore_elapsed_seconds": round(
                elapsed.get("04-restore-full", 0.0) + elapsed.get("05-restore-partial", 0.0), 3),
            "synthetic_only": True,
            "local_repository_only": True,
        }
        (outdir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2, sort_keys=True))
        raise

    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))

    if not exact:
        raise RuntimeError("full restore does not match source exactly: "
                           + describe_diff(source_map, restored_map))
    if not incomplete:
        raise RuntimeError("partial restore is not an incomplete subset as expected: "
                           + describe_diff(source_map, partial_map))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
