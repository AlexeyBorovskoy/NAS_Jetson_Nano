"""Saved raw application messages remain visible to nas-why chronologies."""
from blackbox.collector_storage import Storage
from blackbox.config import Config
from blackbox.why.journal_read import read_container_log


def test_plain_log_has_explicit_observation_timestamp(tmp_path):
    now = 1791861274
    cfg = Config(ssd_root=str(tmp_path / 'ssd'), fallback_root=str(tmp_path / 'fb'))
    store = Storage(cfg, now, ismount=lambda _path: True)
    store.persist_logs('test_service', ['plain application message\n'], now + 60)
    path = tmp_path / 'ssd' / 'hot' / '2026-10-13' / 'containers' / 'test_service.log.gz'
    rows = read_container_log(str(path), 'test_service')
    assert rows and rows[0][0] == now + 60
    assert '(observed)' in rows[0][1]
    assert 'plain application message' in rows[0][1]
    store.close()
