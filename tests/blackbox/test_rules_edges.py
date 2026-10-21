"""Negative confidence and missing-data cases for pure verdict rules."""
from blackbox.config import Config
from blackbox.why.rules import (Evidence, evaluate, rule_container,
                                rule_disk_hang, rule_thermal, rule_unclean_boot,
                                rule_usb)

TS = 1791861274


def evidence(**values):
    values.setdefault("window", (TS - 3600, TS))
    return Evidence(**values)


def test_missing_power_is_not_inferred_as_flat_or_zero():
    ev = evidence(boot={"clean": False, "last_heartbeat": TS})
    result = rule_unclean_boot(ev, Config())
    assert result[0]["confidence"] == "unknown"
    assert "питание" not in result[0]["verdict"].lower()


def test_empty_evidence_has_fresh_independent_defaults():
    first = evidence()
    second = evidence()
    first.events.append({"kind": "sentinel"})
    assert not second.events and not second.samples and not second.snapshots
    assert evaluate(second, Config())[0]["confidence"] == "unknown"


def test_137_without_oom_event_or_flag_has_unknown_cause():
    ev = evidence(events=[{"ts": TS, "source": "docker", "kind": "die",
                           "subject": "svc", "detail": {"exitCode": 137}}])
    result = rule_container(ev, Config())
    assert result[0]["confidence"] == "unknown"
    assert "причина неизвестна" in result[0]["verdict"].lower()


def test_real_docker_oom_kind_correlates_same_container():
    events = [{"ts": TS - 1, "source": "docker", "kind": "oom", "subject": "svc", "detail": {}},
              {"ts": TS, "source": "docker", "kind": "die", "subject": "svc",
               "detail": {"exitCode": 137}}]
    result = rule_container(evidence(events=events), Config())
    assert len(result) == 1 and result[0]["confidence"] == "fact"
    assert "нехватке памяти" in result[0]["verdict"].lower()


def test_zero_exit_is_normal_completion():
    ev = evidence(events=[{"ts": TS, "source": "docker", "kind": "die",
                          "subject": "svc", "detail": {"exitCode": 0}}])
    assert rule_container(ev, Config()) == []


def test_watchdog_must_match_container_identifier_and_unit():
    ev = evidence(events=[{"ts": TS, "source": "docker", "kind": "die",
                          "subject": "service_a", "detail": {"exitCode": 143}}],
                  journal=[(TS, "watchdog: service_a: docker restart OK")])
    assert "сторожем" not in rule_container(ev, Config())[0]["verdict"].lower()


def test_watchdog_outside_window_does_not_match():
    line = ("nas_jetson_nano-container-watchdog[42]: watchdog: service_a: "
            "running/unhealthy → docker restart OK")
    ev = evidence(events=[{"ts": TS, "source": "docker", "kind": "die",
                           "subject": "service_a", "detail": {"exitCode": 143}}],
                  journal=[(TS + 121, line)])
    assert "сторожем" not in rule_container(ev, Config())[0]["verdict"].lower()


def test_lookalike_watchdog_unit_does_not_match():
    line = ("nas_jetson_nano-container-watchdog-fake[42]: watchdog: service_a: "
            "docker restart OK")
    ev = evidence(events=[{"ts": TS, "source": "docker", "kind": "die",
                           "subject": "service_a", "detail": {"exitCode": 143}}],
                  journal=[(TS, line)])
    assert "сторожем" not in rule_container(ev, Config())[0]["verdict"].lower()


def test_disk_requires_three_distinct_pids_and_zero_counter_deltas():
    proc = {"ts": TS, "pid": 1, "state": "D", "wchan": "request_wait_answer"}
    ev = evidence(procs=[proc, dict(proc), dict(proc)],
                  events=[{"ts": TS, "kind": "mount_hung", "subject": "/mnt/hdd2tb"}],
                  disk_samples=[(TS - 90, "usb-WD", 1, 1, 1, 1, 1),
                                (TS, "usb-WD", 2, 1, 1, 1, 1)])
    assert rule_disk_hang(ev, Config()) == []


def test_single_silent_ssd_is_not_mistaken_for_the_hdd():
    processes = [{"ts": TS, "pid": pid, "state": "D",
                  "wchan": "request_wait_answer"} for pid in (1, 2, 3)]
    events = [{"ts": TS, "kind": "mount_hung", "subject": "/mnt/hdd2tb",
               "detail": {"since": TS - 100}}]
    disks = [(TS - 100, "usb-JMicron_SSD-0:0", 1, 1, 1, 1, 1),
             (TS, "usb-JMicron_SSD-0:0", 1, 1, 1, 1, 1)]
    ev = evidence(procs=processes, events=events, disk_samples=disks)
    assert rule_disk_hang(ev, Config()) == []


def test_thermal_requires_correlated_frequency_drop():
    ev = evidence(samples=[{"ts": TS - 1, "t_cpu": 950, "freq_mhz": 1400},
                          {"ts": TS, "t_cpu": 950, "freq_mhz": 1500}])
    assert rule_thermal(ev, Config()) == []


def test_usb_requires_same_by_id_with_changed_letter():
    ev = evidence(snapshots=[{"disks": {"sda": "disk-A"}},
                             {"disks": {"sda": "disk-B"}}])
    assert rule_usb(ev, Config()) == []


def test_none_power_sample_does_not_create_diagnosis():
    ev = evidence(boot={"clean": False, "last_heartbeat": TS},
                  samples=[{"ts": TS - 1, "vin_mv": None, "vin_ma": None}])
    result = rule_unclean_boot(ev, Config())
    assert result[0]["confidence"] == "unknown"
    assert result[0]["evidence"]
