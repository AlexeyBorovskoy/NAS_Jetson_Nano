"""Boot snapshots and event ring share the same fallback disk budget."""
from blackbox.collector_storage import Storage
from blackbox.config import Config


def test_ring_counts_snapshot_files_without_removing_them(tmp_path):
    cap = 320 << 10
    cfg = Config(ssd_root=str(tmp_path / 'ssd'), fallback_root=str(tmp_path / 'fallback'),
                 ssd_mount=str(tmp_path / 'mnt'), fallback_cap_bytes=cap)
    store = Storage(cfg, 1791861274, ismount=lambda path: False)
    snapshot = tmp_path / 'fallback' / 'boots' / 'old-boot' / 'pstore'
    snapshot.mkdir(parents=True)
    preserved = snapshot / 'dump'
    preserved.write_bytes(b'p' * cap)
    store.enforce_cap()
    assert not store.ring.writable
    assert store.ring.size() > cap
    assert preserved.read_bytes() == b'p' * cap
    store.close()
