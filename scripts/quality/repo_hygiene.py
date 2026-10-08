#!/usr/bin/env python3
"""Read-only Git metadata gate. Does not scan secrets or delete files."""
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys


POLICY_PATH = "scripts/quality/repo_hygiene_policy.json"
GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
                  ".venv", "venv", "build", "dist", "htmlcov", ".cache"}
GENERATED_SUFFIXES = (".pyc", ".pyo", ".tmp", ".temp", ".bak", ".orig", ".rej", ".log")
ARCHIVES = (".tar", ".tar.gz", ".tar.xz", ".tar.bz2", ".tgz", ".zip", ".7z", ".rar",
            ".iso", ".qcow2", ".vmdk", ".vhd", ".vhdx", ".deb", ".rpm", ".exe", ".msi",
            ".gguf", ".safetensors", ".onnx", ".mp4", ".mov")
RULES = {"local_artifact", "generated", "archive", "root", "oversize"}


def git(repo, *args, **kwargs):
    result = subprocess.run(["git", "-C", str(repo)] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        # Raw errors or file contents can contain private data.
        raise ValueError("Git metadata command failed: " + args[0])
    return result.stdout


def validate_policy(policy):
    if not isinstance(policy, dict) or type(policy.get("version")) is not int or policy["version"] != 1:
        raise ValueError("Unsupported hygiene policy")
    limit = policy.get("max_blob_bytes")
    if type(limit) is not int or limit <= 0:
        raise ValueError("max_blob_bytes must be a positive integer")
    roots = policy.get("root_files")
    if not isinstance(roots, list) or not all(valid_root(x) for x in roots):
        raise ValueError("root_files must contain exact filenames")
    exceptions = policy.get("exceptions")
    if not isinstance(exceptions, dict):
        raise ValueError("exceptions must be an object")
    for path, item in exceptions.items():
        validate_exception(path, item, limit)
    return policy


def valid_root(name):
    return (isinstance(name, str) and name not in {"", ".", ".."}
            and "/" not in name and "\\" not in name)


def valid_relative(path):
    parts = PurePosixPath(path).parts
    return (bool(parts) and ".." not in parts and not path.startswith("/")
            and "\\" not in path and PurePosixPath(path).as_posix() == path)


def valid_allow(allow):
    return isinstance(allow, list) and all(isinstance(x, str) and x in RULES for x in allow)


def validate_exception(path, item, limit):
    if not valid_relative(path):
        raise ValueError("Exception paths must be repository-relative")
    if not isinstance(item, dict) or not isinstance(item.get("reason"), str) or not item["reason"].strip():
        raise ValueError("Every exception needs a nonempty reason")
    allow = item.get("allow")
    if not valid_allow(allow):
        raise ValueError("Exception allow must list known rules")
    if "oversize" in allow:
        ceiling = item.get("max_bytes")
        if type(ceiling) is not int or ceiling < limit:
            raise ValueError("Oversize exceptions need an explicit byte ceiling")


def load_policy(repo, ref, explicit):
    if explicit:
        text = Path(explicit).read_text(encoding="utf-8")
    else:
        target = (ref + ":" if ref else ":") + POLICY_PATH
        text = git(repo, "show", target).decode("utf-8")
    return validate_policy(json.loads(text))


def entries(repo, ref):
    command = ("ls-tree", "-r", "-z", ref) if ref else ("ls-files", "--stage", "-z")
    records = []
    for raw in git(repo, *command).split(b"\0"):
        if not raw:
            continue
        metadata, name = raw.split(b"\t", 1)
        fields = metadata.decode("ascii").split()
        path = name.decode("utf-8")
        if ref:
            mode, kind, oid = fields
        else:
            mode, oid, stage = fields
            if stage != "0":
                raise ValueError("Unmerged index; resolve conflicts before checking hygiene")
            kind = "commit" if mode == "160000" else "blob"
        records.append((path, kind, oid))
    return records


def blob_sizes(repo, records):
    ids = sorted({oid for _, kind, oid in records if kind == "blob"})
    if not ids:
        return {}
    result = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                 input=("\n".join(ids) + "\n").encode("ascii"))
    sizes = {}
    for line in result.decode("ascii").splitlines():
        oid, kind, size = line.split()
        if kind != "blob":
            raise ValueError("Expected a Git blob")
        sizes[oid] = int(size)
    return sizes


def path_rules(path, policy):
    parts = PurePosixPath(path).parts
    if any(part in {".agent-work", "ds_board"} for part in parts):
        return {"agent_workspace"}
    rules = set()
    if parts[0] == "artifacts":
        rules.add("local_artifact")
    if (any(part in GENERATED_DIRS or part.endswith(".egg-info") for part in parts)
            or path.lower().endswith(GENERATED_SUFFIXES)
            or parts[-1] in {".coverage", "coverage.xml"}):
        rules.add("generated")
    if path.lower().endswith(ARCHIVES):
        rules.add("archive")
    if len(parts) == 1 and path not in policy["root_files"]:
        rules.add("root")
    return rules


def violations(records, sizes, policy):
    problems = []
    for path, kind, oid in records:
        rules = path_rules(path, policy)
        exception = policy["exceptions"].get(path, {})
        rules -= set(exception.get("allow", [])) - {"oversize"}
        size = sizes.get(oid, 0)
        ceiling = exception.get("max_bytes", policy["max_blob_bytes"]) if "oversize" in exception.get("allow", []) else policy["max_blob_bytes"]
        if kind == "blob" and size > ceiling:
            rules.add("oversize")
        for rule in sorted(rules):
            problems.append((path, rule, size))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="check the complete index (default)")
    mode.add_argument("--tree", help="check a committed Git tree, e.g. HEAD")
    parser.add_argument("--policy", help="explicit local policy for controlled previews/tests")
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.repo, args.tree, args.policy)
        records = entries(args.repo, args.tree)
        problems = violations(records, blob_sizes(args.repo, records), policy)
    except (ValueError, OSError, UnicodeError) as exc:
        print("Hygiene configuration/metadata error: " + type(exc).__name__, file=sys.stderr)
        return 2
    for path, rule, size in problems:
        print("FAIL %s %s (%d bytes)" % (rule, json.dumps(path, ensure_ascii=True), size))
    print("Hygiene: %d Git entries, %d violations" % (len(records), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
