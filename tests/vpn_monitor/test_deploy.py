"""Установочные файлы: лимиты юнитов, бюджет таймаутов, установщик ничего лишнего не трогает."""
import os
import re

import report

SVC = os.path.join(os.path.dirname(report.__file__))


def text(*parts):
    return open(os.path.join(SVC, *parts), encoding="utf-8").read()


def test_collect_unit_limits():
    s = text("systemd", "nasa-vpnmon-collect.service")
    for line in ("Type=oneshot", "CPUQuota=20%", "MemoryMax=64M", "Nice=10", "TimeoutStartSec=50",
                 "ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/collect.py"):
        assert line in s, line


def test_collect_timeout_exceeds_subprocess_budget():
    import collect
    s = text("systemd", "nasa-vpnmon-collect.service")
    timeout = int(re.search(r"TimeoutStartSec=(\d+)", s).group(1))
    assert 4 * collect.EXEC_TIMEOUT < timeout < 60  # inspect×2 + exec + journalctl; меньше интервала


def test_collect_timer_every_minute():
    s = text("systemd", "nasa-vpnmon-collect.timer")
    assert "OnUnitActiveSec=60" in s and "OnBootSec=60" in s and "WantedBy=timers.target" in s


def test_report_timer_10_msk_persistent():
    s = text("systemd", "nasa-vpnmon-report.timer")
    assert "OnCalendar=*-*-* 10:00:00 Europe/Moscow" in s and "Persistent=true" in s


def test_report_timeout_exceeds_retry_budget():
    s = text("systemd", "nasa-vpnmon-report.service")
    assert "ExecStart=/usr/bin/python3 /usr/local/lib/nasa-vpnmon/report.py --send" in s
    timeout = int(re.search(r"TimeoutStartSec=(\d+)", s).group(1))
    per_message = 3 * report.HTTP_TIMEOUT + sum(report.RETRY_PAUSES)
    assert timeout > 2 * per_message


def test_installer_touches_nothing_else():
    s = text("install_vps.sh")
    for word in ("amnezia", "ufw", "iptables", "nginx", "sshd", "apt", "pip", "docker", "restart"):
        assert not re.search(r"\b%s\b" % word, s, re.IGNORECASE), word
    assert "telegram.env\n" not in s.replace("[ -f /etc/nasa-vpnmon/telegram.env ]", "")


def test_installer_installs_every_module():
    s = text("install_vps.sh")
    for name in sorted(f for f in os.listdir(SVC) if f.endswith(".py")):
        assert name in s, name


def test_telegram_example_has_no_values():
    for line in text("telegram.env.example").splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.split("=", 1)[1] == "", line


def test_rule13_snapshot_only_reads():
    s = text("rule13_snapshot.sh")
    assert set(re.findall(r"docker\s+(\w+)", s)) == {"inspect"}
    assert "ss -tlnuH" in s
    assert "docker exec" not in s and "wg show" not in s
