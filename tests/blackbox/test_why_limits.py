"""Resource and parser boundaries tested without limiting the pytest process."""
import gzip

from blackbox.why.journal_read import read_container_log
from blackbox.why.worker_limits import ADDRESS_SPACE_LIMIT, apply_memory_limit


class FakeResource(object):
    RLIMIT_AS = 9

    def __init__(self, failure=False):
        self.value = None
        self.failure = failure

    def getrlimit(self, key):
        assert key == self.RLIMIT_AS
        return (-1, -1)

    def setrlimit(self, key, value):
        if self.failure:
            raise OSError("synthetic")
        self.value = value


def test_linux_worker_memory_limit_is_applied_only_to_passed_resource():
    resource = FakeResource()
    assert apply_memory_limit(resource, "linux")
    assert resource.value == (ADDRESS_SPACE_LIMIT, -1)


def test_worker_limit_failure_fails_closed_and_nonlinux_is_untouched():
    resource = FakeResource(failure=True)
    assert not apply_memory_limit(resource, "linux")
    assert apply_memory_limit(resource, "win32")
    assert resource.value is None


def test_container_log_uses_filename_as_identity_not_body_text(tmp_path):
    path = tmp_path / "container.log.gz"
    line = "2026-10-12T03:30:01.123456+0000 host app[12]: ordinary log message\n"
    with gzip.open(str(path), "wb") as stream:
        stream.write(line.encode("utf-8"))
    rows = read_container_log(str(path), "known-container")
    assert rows == [(1791775801, "app: ordinary log message")]
