"""A reboot preserves the final bounded sensor observation for SD-only analysis."""
import json
import os
from blackbox import boot_record
from blackbox.store import write_heartbeat
from test_boot_record import _cfg, _snapshot, _catalog, NOW, CURRENT, PREVIOUS


def test_transition_saves_only_allowlisted_heartbeat_power(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(boot_record.os.path, 'ismount', lambda _path: False)
    snapshot = _snapshot(tmp_path / 'fallback', CURRENT, NOW)
    write_heartbeat(os.path.join(cfg.fallback_root, 'heartbeat'), PREVIOUS, NOW - 10,
                    {'vin_mv': 4610, 'vin_ma': None, 'extra': 'synthetic-private-field'})
    boot_record.record_boot(cfg, CURRENT, snapshot, NOW)
    catalog = _catalog(tmp_path / 'fallback')
    stored = json.loads(catalog.get_cursor('boot-heartbeat:' + PREVIOUS))
    assert stored['power'] == {'vin_mv': 4610, 'vin_ma': None, 'cpu_mw': None, 'gpu_mw': None}
    assert stored['ts'] == NOW - 10 and stored['boot_id'] == PREVIOUS
    assert 'synthetic-private-field' not in json.dumps(stored)
    catalog.close()
