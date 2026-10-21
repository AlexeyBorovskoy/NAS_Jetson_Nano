"""Window clipping and temporal-correlation regression tests."""
from blackbox.config import Config
from blackbox.why.rules import (Evidence, evaluate, rule_container,
                                rule_disk_hang, rule_memory, rule_thermal,
                                rule_unclean_boot)

START = 1791860000
END = START + 600
CFG = Config()


def test_outside_events_do_not_produce_verdicts_or_count_as_window_data():
    event = {"ts": START - 1, "source": "docker", "kind": "die",
             "subject": "svc", "detail": {"exitCode": 1}}
    ev = Evidence(window=(START, END), events=[event])
    assert rule_container(ev, CFG) == []
    assert evaluate(ev, CFG)[0]["cls"] == "data"


def test_stale_d_state_and_low_memory_do_not_explain_later_reset():
    ev = Evidence(window=(START, END), boot={"clean": False,
        "last_heartbeat": END, "reset_source": "unknown"},
        procs=[{"ts": START + 1, "pid": 9, "state": "D",
                "wchan": "request_wait_answer"}],
        samples=[{"ts": END - 1, "mem_avail_mb": 100}])
    result = rule_unclean_boot(ev, CFG)
    assert result[0]["confidence"] == "unknown"


def test_old_frequency_cannot_correlate_with_hot_sample():
    ev = Evidence(window=(START, END), samples=[
        {"ts": START - 31536000, "t_cpu": 600, "freq_mhz": 1400},
        {"ts": END, "t_cpu": 950, "freq_mhz": 307}])
    assert rule_thermal(ev, CFG) == []


def test_missing_disk_counters_are_not_zero_deltas():
    ev = Evidence(window=(START, END), events=[{"ts": END, "kind": "mount_hung",
        "subject": CFG.hdd_mount, "detail": {"since": END - 100}}],
        procs=[{"ts": END, "pid": pid, "state": "D",
                "wchan": "request_wait_answer"} for pid in (1, 2, 3)],
        disk_samples=[(END - 100, "usb-WD", 1, 1, 1, 1, None),
                      (END, "usb-WD", 1, 1, 1, 1, None)])
    assert rule_disk_hang(ev, CFG) == []


def test_three_d_state_pids_spread_over_minutes_are_not_one_cluster():
    ev = Evidence(window=(START, END), events=[{
        "ts": END, "kind": "mount_hung", "subject": CFG.hdd_mount,
        "detail": {"since": START}}],
        procs=[{"ts": END - offset, "pid": pid, "state": "D",
                "wchan": "request_wait_answer"}
               for pid, offset in ((1, 120), (2, 60), (3, 0))],
        disk_samples=[(START, "usb-WD_HDD-0:0", 1, 1, 1, 1, 1),
                      (END, "usb-WD_HDD-0:0", 1, 1, 1, 1, 1)])
    assert rule_disk_hang(ev, CFG) == []


def test_iso_journal_watchdog_and_kernel_prefixes_are_parsed():
    line = ("2026-10-13T03:14:14.123456+00:00 jetson "
            "nas_jetson_nano-container-watchdog[1234]: watchdog: svc: "
            "running/unhealthy → docker restart OK")
    events = [{"ts": END, "source": "docker", "kind": "die", "subject": "svc",
               "detail": {"exitCode": 143}}]
    result = rule_container(Evidence(window=(START, END), events=events,
                                     journal=[(END - 20, line)]), CFG)
    assert "сторожем ops-1" in result[0]["verdict"].lower()
    kernel = ("2026-10-13T03:14:14.123456+00:00 jetson kernel: "
              "Out of memory: Killed process 4 (worker)")
    memory = rule_memory(Evidence(window=(START, END), journal=[(END, kernel)]), CFG)
    assert "worker" in memory[0]["verdict"].lower()


def test_memory_markers_outside_window_are_ignored():
    ev = Evidence(window=(START, END), journal=[
        (START - 1, "kernel: Out of memory: Killed process 4 (old)")])
    assert rule_memory(ev, CFG) == []


def test_unrelated_non_kernel_killed_process_is_not_oom_fact():
    ev = Evidence(window=(START, END), journal=[
        (END, "app: Killed process 4 (worker) after timeout")])
    assert rule_memory(ev, CFG) == []


def test_oom_for_other_container_does_not_explain_exit_137():
    events = [
        {"ts": END - 1, "source": "docker", "kind": "oom",
         "subject": "other", "detail": {}},
        {"ts": END, "source": "docker", "kind": "die", "subject": "svc",
         "detail": {"exitCode": 137}},
    ]
    result = rule_container(Evidence(window=(START, END), events=events), CFG)
    assert result[0]["confidence"] == "unknown"


def test_snapshot_from_outside_window_does_not_create_usb_verdict():
    ev = Evidence(window=(START, END), snapshots=[
        {"start": START - 86400, "disks": {"sda": "usb-WD"}},
        {"start": START - 10, "disks": {"sdb": "usb-WD"}}])
    from blackbox.why.rules import rule_usb
    assert rule_usb(ev, CFG) == []
