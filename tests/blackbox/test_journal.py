"""OBS-1, задача 5: sources/journal.py — порция журнала systemd по курсору.

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, задача 5.
journal_since зовёт journalctl через параметр run (сигнатура как subprocess.run) —
в тестах run подменяется, ни один настоящий процесс не запускается.
"""
from blackbox.sources.journal import journal_since

# Как выглядит вывод journalctl --no-pager -o short-iso-precise --show-cursor:
# строки журнала, последней строкой — курсор (-- cursor: s=...;i=...).
JOURNAL_OUT_FIRST = (
    "2026-10-13T03:19:58+0000 jetson systemd[1]: Started session.\n"
    "2026-10-13T03:20:01+0000 jetson kernel: eth0: link up\n"
    "-- cursor: s=abc;i=456\n"
)
JOURNAL_OUT_NEXT = (
    "2026-10-13T03:24:59+0000 jetson systemd[1]: Reloading.\n"
    "-- cursor: s=def;i=789\n"
)


class _FakeCompleted(object):
    """Ответ как у subprocess.CompletedProcess."""

    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class _FakeRun(object):
    """Подставной subprocess.run: помнит команды, отдаёт заданный stdout."""

    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.calls = []

    def __call__(self, args, **kwargs):
        if isinstance(args, str):
            args = args.split()
        self.calls.append([str(a) for a in args])
        return _FakeCompleted(self.stdout, self.returncode)

    def last_cmd(self):
        assert self.calls, "run ни разу не вызван"
        return self.calls[-1]


def test_journal_since_without_cursor_uses_since_window():
    run = _FakeRun(JOURNAL_OUT_FIRST)
    lines, new_cursor = journal_since(None, run)
    cmd = run.last_cmd()
    assert cmd[0].endswith("journalctl")
    assert "--no-pager" in cmd
    assert "--show-cursor" in cmd
    assert any("short-iso-precise" in part for part in cmd)
    assert "--since=-5min" in cmd
    assert not any(part.startswith("--after-cursor") for part in cmd)
    assert lines == [
        "2026-10-13T03:19:58+0000 jetson systemd[1]: Started session.",
        "2026-10-13T03:20:01+0000 jetson kernel: eth0: link up",
    ]
    # курсор взят из последней строки вывода
    assert new_cursor == "s=abc;i=456"


def test_journal_since_with_cursor_uses_after_cursor():
    run = _FakeRun(JOURNAL_OUT_NEXT)
    lines, new_cursor = journal_since("s=abc", run)
    cmd = run.last_cmd()
    assert "--after-cursor=s=abc" in cmd
    assert "--since=-5min" not in cmd
    assert lines == ["2026-10-13T03:24:59+0000 jetson systemd[1]: Reloading."]
    # строки курсора в lines не попадают
    assert not any(line.startswith("-- cursor:") for line in lines)
    assert new_cursor == "s=def;i=789"
