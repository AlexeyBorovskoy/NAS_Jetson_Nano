#!/usr/bin/env python3
"""OBS-1 archive entrypoint: supervisor by default, HDD worker only with flag."""
import os
import sys

INSTALLED_LIB = "/usr/local/lib/nas_jetson_nano/blackbox"


def _candidate_parents():
    here = os.path.dirname(os.path.abspath(__file__))
    parents = [os.path.normpath(os.path.join(
        here, "..", "..", "services", "blackbox"))]
    project = os.environ.get("NAS_PROJECT_DIR")
    if project:
        parents.append(os.path.join(project, "services", "blackbox"))
    parents.extend((INSTALLED_LIB, os.path.dirname(INSTALLED_LIB)))
    return parents


def _load_package():
    try:
        import blackbox
    except ImportError:
        pass
    else:
        return True
    for parent in _candidate_parents():
        if os.path.isfile(os.path.join(parent, "blackbox", "__init__.py")):
            sys.path.insert(0, parent)
            return True
    return False


def main(argv=None):
    if not _load_package():
        sys.stderr.write("archive: package unavailable\n")
        return 1
    args = sys.argv[1:] if argv is None else argv
    if args == ["--worker"]:
        from blackbox.archive import worker_main
        return worker_main()
    if args:
        sys.stderr.write("archive: invalid arguments\n")
        return 2
    from blackbox.archive_supervisor import main as supervisor_main
    return supervisor_main()


if __name__ == "__main__":
    sys.exit(main())
