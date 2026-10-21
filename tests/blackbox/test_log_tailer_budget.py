import json

from blackbox.sources.container_logs import LogTailer


def record(value):
    return json.dumps({"log": value}, separators=(",", ":")).encode() + b"\n"


def drain(tailer, path, name="svc", cap=16, rounds=20):
    result = []
    for _ in range(rounds):
        result.extend(tailer.read_new(name, str(path), max_bytes=cap))
        if tailer._state[name]["offset"] >= path.stat().st_size:
            break
    return result


def test_late_start_skips_backlog_to_record_boundary_and_marks_bytes(tmp_path):
    path = tmp_path / "container.log"
    data = record("old-a") + record("old-b") + record("fresh")
    path.write_bytes(data)
    tailer = LogTailer({}, initial_tail_bytes=len(record("old-b")) + len(record("fresh")))

    got = drain(tailer, path, cap=32)

    assert got[-1] == "fresh"
    marker = got[0]
    assert marker.startswith("[blackbox: initial log backlog omitted: ")
    assert marker.endswith(" bytes]\n")
    assert "old" not in "".join(got)
    assert tailer._state["svc"]["discarded"] > 0


def test_oversized_record_discards_multiple_chunks_and_never_leaks_fragments(tmp_path):
    path = tmp_path / "container.log"
    path.write_bytes(b'{"log":"TOPSECRET' + b"x" * 50 + b'"}' + b"\n" + record("after"))
    state = {}
    first = LogTailer(state).read_new("svc", str(path), max_bytes=24)
    assert first == [LogTailer.OVERSIZED_GAP]

    second = LogTailer(state).read_new("svc", str(path), max_bytes=24)
    assert "TOPSECRET" not in repr(first + second)
    while state["svc"]["discarding"]:
        got = LogTailer(state).read_new("svc", str(path), max_bytes=24)
        assert "TOPSECRET" not in repr(got)
    got = drain(LogTailer(state), path, cap=24)
    assert got == ["after"]
    assert state["svc"]["oversized"] == 1


def test_cursor_reload_preserves_discard_state_and_offset(tmp_path):
    path = tmp_path / "container.log"
    path.write_bytes(b"A" * 40 + b"\n" + record("safe"))
    state = {}
    assert LogTailer(state).read_new("svc", str(path), max_bytes=8) == [
        LogTailer.OVERSIZED_GAP]
    saved = dict(state["svc"])

    got = LogTailer(state).read_new("svc", str(path), max_bytes=8)

    assert state["svc"]["offset"] > saved["offset"]
    assert "A" * 8 not in repr(got)


def test_partial_final_record_is_retained_until_newline(tmp_path):
    path = tmp_path / "container.log"
    path.write_bytes(record("complete") + b'{"log":"half')
    state = {}
    tailer = LogTailer(state)

    assert tailer.read_new("svc", str(path), max_bytes=128) == ["complete"]
    offset = state["svc"]["offset"]
    assert offset == len(record("complete"))
    with path.open("ab") as stream:
        stream.write(b'way"}\n')
    assert tailer.read_new("svc", str(path), max_bytes=128) == ["halfway"]


def test_legacy_short_record_keeps_original_cursor_shape(tmp_path):
    path = tmp_path / "container.log"
    path.write_bytes(record("safe"))
    state = {}

    assert LogTailer(state).read_new("svc", str(path), max_bytes=128) == ["safe"]
    assert set(state["svc"]) == {"inode", "offset"}


def test_rotation_and_truncation_restart_cursor(tmp_path):
    path = tmp_path / "container.log"
    path.write_bytes(record("one") + record("two"))
    state = {}
    tailer = LogTailer(state)
    assert tailer.read_new("svc", str(path), max_bytes=128) == ["one", "two"]

    path.write_bytes(record("x"))
    assert tailer.read_new("svc", str(path), max_bytes=128) == ["x"]
    state["svc"]["inode"] += 1
    path.write_bytes(record("rotated"))
    assert tailer.read_new("svc", str(path), max_bytes=128) == ["rotated"]
