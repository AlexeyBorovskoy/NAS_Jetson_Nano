"""A giant log line and a failed journal command must remain bounded."""
import io
import subprocess
from types import SimpleNamespace

from blackbox.sources import container_logs, journal


def test_single_giant_log_line_does_not_grow_tail_memory(monkeypatch):
    monkeypatch.setattr(container_logs, 'TAIL_READ_MAX_BYTES', 1024)
    stream = io.BytesIO(b'x' * 100000)
    data = container_logs._read_tail_bytes(stream, 200, 65536)
    assert len(data) == 1024


def test_failed_journal_does_not_advance_cursor_or_keep_stderr():
    def failed(argv, **kwargs):
        assert kwargs['timeout'] == 10
        return SimpleNamespace(returncode=1, stdout='partial\n-- cursor: wrong')
    assert journal.journal_since('previous', failed) == ([], 'previous')


def test_journal_timeout_keeps_previous_cursor():
    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
    assert journal.journal_since('previous', timeout) == ([], 'previous')
