#!/usr/bin/env python3
"""Учёт VPN и нагрузки VPS: один замер, только чтение (спецификация 2026-10-04 §5, §8).

В контейнере выполняется только WG_READ_SCRIPT; docker вызывается только с exec и inspect.
"""
import argparse
import os
import subprocess
import sys
import time
import types

import vpnmon_parse as vp
import vpnmon_store as vs

AWG = "amnezia-awg2"
XRAY = "amnezia-xray"
# set -e: сбой wg — это «awg2 недоступен», а не «ноль пиров» (иначе все пиры стали бы удалёнными).
WG_READ_SCRIPT = (
    "set -e; wg show awg0 allowed-ips; echo @@; wg show awg0 transfer; echo @@; "
    "wg show awg0 latest-handshakes; echo @@; cat /opt/amnezia/awg/clientsTable 2>/dev/null || true"
)
INSPECT_FORMAT = "{{.State.Pid}}|{{.State.StartedAt}}|{{.State.Running}}"
JOURNAL_PREV_BOOT = ["journalctl", "-b", "-1", "-n", "200", "-o", "cat", "-q", "--no-pager"]
DB_PATH = "/var/lib/nasa-vpnmon/vpnmon.db"
NAMES_PATH = "/etc/nasa-vpnmon/names.conf"
EXEC_TIMEOUT = 10


def run(cmd):
    """stdout команды или None (ошибка, код ≠ 0, таймаут): один источник не роняет замер."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=EXEC_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout if res.returncode == 0 else None


def make_proc_reader(root):
    """Функция чтения файла относительно root (обычно /proc); нет файла — пустая строка."""
    def read(rel):
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""
    return read


def disk_pct(path):
    """Заполнение файловой системы, % — как Use% у df."""
    st = os.statvfs(path)
    used = st.f_blocks - st.f_bfree
    return 100.0 * used / (used + st.f_bavail) if used + st.f_bavail else 0.0


def inspect(runner, name):
    """(pid, StartedAt, запущен) контейнера; None, если docker не ответил."""
    out = runner(["docker", "inspect", "-f", INSPECT_FORMAT, name])
    try:
        return vp.parse_inspect(out) if out else None
    except ValueError:
        return None


def gather_awg(runner, conf):
    """(пиры, имена) из amnezia-awg2; None, если контейнер не ответил или пиров ноль."""
    out = runner(["docker", "exec", AWG, "sh", "-c", WG_READ_SCRIPT])
    if out is None:
        return None
    try:
        allowed, transfer, handshakes, table_text = vp.split_sections(out, 4)
        peers = vp.parse_peers(allowed, transfer, handshakes)
    except ValueError:
        return None
    if not peers:
        return None
    try:
        table = vp.parse_clients_table(table_text)
    except ValueError:
        table = None
    return peers, vp.resolve_names(peers, table, conf)


def container_counters(proc, info, iface, boot_id):
    """(эпоха, rx, tx) интерфейса в namespace запущенного контейнера; иначе None."""
    if not info or not info[2]:
        return None
    pair = vp.parse_net_dev(proc("%d/net/dev" % info[0]), iface)
    return None if pair is None else ("%s|%s" % (boot_id, info[1]),) + pair


def gather_host(proc, disk, awg_info, xray_info):
    """Метрики хоста по контракту vpnmon_store.record_host."""
    stat = proc("stat")
    boot_id = proc("sys/kernel/random/boot_id").strip()
    iface = vp.parse_default_iface(proc("net/route"))
    wan = vp.parse_net_dev(proc("net/dev"), iface) if iface else None
    mem_used, mem_total = vp.parse_mem(proc("meminfo"))
    conntrack = proc("sys/net/netfilter/nf_conntrack_count").strip()
    return {
        "boot_id": boot_id, "btime": vp.parse_btime(stat), "cpu": vp.parse_cpu(stat),
        "mem_used": mem_used, "mem_total": mem_total, "load1": vp.parse_load1(proc("loadavg")),
        "disk_pct": disk, "conntrack": int(conntrack) if conntrack.isdigit() else None,
        "counters": {
            "wan": None if wan is None else ("%s|%s" % (boot_id, iface),) + wan,
            "awg": container_counters(proc, awg_info, "awg0", boot_id),
            "xray": container_counters(proc, xray_info, "eth0", boot_id),
        },
        "started": {AWG: awg_info[1] if awg_info else None,
                    XRAY: xray_info[1] if xray_info else None},
    }


def snapshot(src):
    """Один замер без записи: (awg или None, сведения о контейнере awg, хост)."""
    awg_info, xray_info = inspect(src.runner, AWG), inspect(src.runner, XRAY)
    awg = gather_awg(src.runner, src.conf) if awg_info and awg_info[2] else None
    host = gather_host(src.proc, src.disk, awg_info, xray_info)
    host["awg_ok"] = awg is not None
    return awg, awg_info, host


def collect_once(db, now, src):
    """Замер и запись одной транзакцией (§6: при ошибке не пишется ничего)."""
    awg, awg_info, host = snapshot(src)
    old_boot = vs.get_state(db).get("boot_id")
    if old_boot and old_boot != host["boot_id"]:
        host["shutdown_reason"] = vp.shutdown_reason(src.runner(JOURNAL_PREV_BOOT) or "")
    with db:
        vs.record_host(db, now, host)
        if awg is not None:
            vs.record_peers(db, now, awg[0], awg[1], "%s|%s" % (host["boot_id"], awg_info[1]))
    return awg, host


def print_snapshot(awg, host):
    """--dry-run: разобранный замер для сверки с `wg show awg0 transfer`."""
    print("boot_id=%s cpu=%s mem=%d/%d load1=%.2f disk=%.1f%% conntrack=%s" % (
        host["boot_id"], host["cpu"], host["mem_used"], host["mem_total"], host["load1"],
        host["disk_pct"], host["conntrack"]))
    for name, cur in sorted(host["counters"].items()):
        print("%s: %s" % (name, "нет" if cur is None else "rx=%d tx=%d" % cur[1:]))
    if awg is None:
        print("awg: недоступен")
        return
    peers, names = awg
    for key, p in sorted(peers.items(), key=lambda kv: -kv[1]["tx"]):
        print("%s  %-24s %-12s rx=%d tx=%d hs=%d" % (
            key[:8], names.get(key, "?"), p["vpn_ip"], p["rx"], p["tx"], p["handshake"]))
    print("peers=%d" % len(peers))


def default_sources(names_path):
    try:
        with open(names_path, encoding="utf-8") as fh:
            conf = vp.parse_names_conf(fh.read())
    except OSError:
        conf = []
    return types.SimpleNamespace(runner=run, proc=make_proc_reader("/proc"),
                                 disk=disk_pct("/"), conf=conf)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Учёт VPN и нагрузки VPS: один замер (только чтение)")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--names", default=NAMES_PATH)
    ap.add_argument("--dry-run", action="store_true", help="напечатать замер, ничего не записывать")
    args = ap.parse_args(argv)
    os.umask(0o077)
    src = default_sources(args.names)
    if args.dry_run:
        awg, _, host = snapshot(src)
        print_snapshot(awg, host)
        return 0
    db = vs.open_db(args.db)
    try:
        collect_once(db, time.time(), src)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
