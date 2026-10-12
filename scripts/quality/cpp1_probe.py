#!/usr/bin/env python3
# CPP-1, step 1: passive, read-only measurement on the live Jetson.
# No sudo, no writes, no load generation. Python 3.6 compatible (host interpreter).
# Run from the workstation:  ssh jetson-via-vps "WINDOW=300 python3 -" < scripts/quality/cpp1_probe.py > out.json
# Result and reading: docs/quality/CPP1_BOTTLENECKS_2026-10-12.ru.md
import json
import os
import re
import statistics
import subprocess
import time

HZ = os.sysconf('SC_CLK_TCK')
WINDOW = int(os.environ.get('WINDOW', '300'))
DISKS = ('sda', 'sdb', 'mmcblk0')


def sh(cmd, timeout=60, inp=None):
    try:
        return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, universal_newlines=True, input=inp).stdout
    except Exception as exc:
        return 'ERR %s' % exc


def read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except Exception:
        return ''


def cpu_total():
    f = [int(x) for x in read('/proc/stat').splitlines()[0].split()[1:9]]
    return dict(zip(('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal'), f))


def diskstats():
    out = {}
    for line in read('/proc/diskstats').splitlines():
        p = line.split()
        if len(p) > 13 and p[2] in DISKS:
            out[p[2]] = {'r': int(p[3]), 'rs': int(p[5]), 'w': int(p[7]), 'ws': int(p[9]), 'busy_ms': int(p[12])}
    return out


def netdev():
    for line in read('/proc/net/dev').splitlines():
        if line.strip().startswith('eth0:'):
            p = line.split(':', 1)[1].split()
            return {'rx': int(p[0]), 'tx': int(p[8])}
    return {}


def containers():
    m = {}
    for line in sh("docker ps --no-trunc --format '{{.ID}}|{{.Names}}|{{.Image}}'").splitlines():
        p = line.split('|')
        if len(p) == 3:
            m[p[0]] = (p[1], p[2])
    return m


def cg_usage(cmap):
    out = {}
    for cid, (name, _) in cmap.items():
        v = read('/sys/fs/cgroup/cpu,cpuacct/docker/%s/cpuacct.usage' % cid).strip()
        if v:
            out[name] = int(v)
    base = '/sys/fs/cgroup/cpu,cpuacct/system.slice'
    try:
        for d in os.listdir(base):
            v = read('%s/%s/cpuacct.usage' % (base, d)).strip()
            if v and (d.startswith('nas') or d.startswith('beszel') or d in ('docker.service', 'containerd.service')):
                out['unit:' + d] = int(v)
    except OSError:
        pass
    return out


def procs(cmap):
    out = {}
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        st = read('/proc/%s/stat' % pid)
        if not st:
            continue
        rp = st.rfind(')')
        f = st[rp + 2:].split()
        comm = st[st.find('(') + 1:rp]
        cg = read('/proc/%s/cgroup' % pid)
        m = re.search(r'/docker/([0-9a-f]{64})', cg)
        owner = cmap.get(m.group(1), ('?', ''))[0] if m else 'host'
        cmd = read('/proc/%s/cmdline' % pid).replace('\0', ' ').strip()[:90]
        rss = re.search(r'VmRSS:\s+(\d+)', read('/proc/%s/status' % pid))
        out[pid] = {'comm': comm, 'owner': owner, 'cmd': cmd, 'ticks': int(f[11]) + int(f[12]),
                    'start': int(f[19]), 'rss_mb': round(int(rss.group(1)) / 1024, 1) if rss else 0}
    return out


def units():
    names = sh("systemctl list-units --all --plain --no-legend 'nasa-*' 'nas_jetson_nano-*' 'nas-*' "
               "'beszel*' | awk '{print $1}' | grep '\\.service$'").split()
    res = []
    for u in names:
        props = {}
        for line in sh('systemctl show %s -p Type -p Result -p ExecMainStartTimestampMonotonic '
                       '-p ExecMainExitTimestampMonotonic -p ExecStart -p ActiveState' % u).splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                props[k] = v
        prog = re.search(r'argv\[\]=(\S+)(?: (\S+))?', props.get('ExecStart', ''))
        start = int(props.get('ExecMainStartTimestampMonotonic', '0') or 0)
        end = int(props.get('ExecMainExitTimestampMonotonic', '0') or 0)
        res.append({'unit': u, 'type': props.get('Type'), 'state': props.get('ActiveState'),
                    'result': props.get('Result'),
                    'prog': ' '.join(x for x in (prog.groups() if prog else ()) if x)[:80],
                    'last_run_s': round((end - start) / 1e6, 2) if end > start else None})
    return res


def curl_lat(url, n):
    vals = []
    for _ in range(n):
        out = sh("curl -s -o /dev/null --max-time 10 -w '%%{http_code} %%{time_total}' '%s'" % url, timeout=15)
        p = out.split()
        if len(p) == 2 and p[0] != '000':
            vals.append(float(p[1]) * 1000)
    if not vals:
        return {'url': url, 'ok': 0}
    vals.sort()
    return {'url': url, 'ok': len(vals), 'p50_ms': round(statistics.median(vals), 1),
            'p95_ms': round(vals[min(len(vals) - 1, int(len(vals) * 0.95))], 1), 'max_ms': round(vals[-1], 1)}


HEALTH_TIMING = r'''
import asyncio, time, json, sys
try:
    from app.services import home_health as h
    from app.config import settings
    from app.routers import storage as s
    from app.services import system_info
    try:
        from app.services import home_health_checks as c
    except Exception:
        c = None
except Exception as e:
    print(json.dumps({"import_error": repr(e)})); sys.exit(0)

async def t(coro):
    t0 = time.perf_counter()
    try:
        await coro
    except Exception:
        pass
    return round((time.perf_counter() - t0) * 1000, 1)

async def main():
    r = {"python": sys.version.split()[0]}
    rows = []
    for _ in range(5):
        row = {}
        if c is not None:
            row["containers"] = await t(c.container_problems(system_info, settings.expected_containers))
            row["storage"] = await t(c.storage_problems(s, h.DISK_WARN_PCT, h.DUMP_MAX_AGE_HOURS))
        row["hdd_stat"] = await t(h._check_hdd_mount())
        row["systemd"] = await t(h._check_failed_units())
        row["total"] = await t(h.build_health())
        rows.append(row)
    r["runs"] = rows
    print(json.dumps(r))

asyncio.run(main())
'''


def sample(cmap):
    return {'cpu': cpu_total(), 'disk': diskstats(), 'net': netdev(), 'cg': cg_usage(cmap),
            'procs': procs(cmap), 't': time.time()}


def system_delta(a, b):
    """Whole-system CPU split, disk and network over the window."""
    dt = b['t'] - a['t']
    c0, c1, d0, d1, n0, n1 = a['cpu'], b['cpu'], a['disk'], b['disk'], a['net'], b['net']
    tot = sum(c1.values()) - sum(c0.values())
    res = {'window_s': round(dt), 'ncpu': os.cpu_count() or 4,
           'cpu_pct_of_all_cores': {k: round(100.0 * (c1[k] - c0[k]) / tot, 1) for k in c0}}
    res['disks'] = {k: {'reads': d1[k]['r'] - d0[k]['r'], 'read_mb': round((d1[k]['rs'] - d0[k]['rs']) / 2048, 1),
                        'writes': d1[k]['w'] - d0[k]['w'], 'write_mb': round((d1[k]['ws'] - d0[k]['ws']) / 2048, 1),
                        'util_pct': round(100.0 * (d1[k]['busy_ms'] - d0[k]['busy_ms']) / (dt * 1000), 1)}
                    for k in d0 if k in d1}
    res['eth0_kbps'] = {k: round((n1[k] - n0[k]) * 8 / dt / 1000, 1) for k in n0} if n0 and n1 else {}
    # CPU per cgroup (containers + accounted units): % of ONE core over the window
    res['cgroup_cpu_pct_one_core'] = sorted(
        [(k, round(100.0 * (b['cg'][k] - a['cg'][k]) / 1e9 / dt, 2)) for k in a['cg'] if k in b['cg']],
        key=lambda x: -x[1])
    return res


def process_delta(a, b):
    """Per-process CPU over the window, RSS at the end; Python processes summed separately."""
    dt = b['t'] - a['t']
    rows = []
    for pid, p in b['procs'].items():
        q = a['procs'].get(pid)
        d = p['ticks'] - (q['ticks'] if q and q['start'] == p['start'] else 0)
        rows.append({'pid': int(pid), 'owner': p['owner'], 'comm': p['comm'], 'cmd': p['cmd'],
                     'cpu_pct_one_core': round(100.0 * d / HZ / dt, 2), 'rss_mb': p['rss_mb'],
                     'python': 'python' in p['comm'] or 'python' in p['cmd'] or 'uvicorn' in p['cmd']})
    rows.sort(key=lambda r: -r['cpu_pct_one_core'])
    py = [r for r in rows if r['python']]
    return {'top_cpu': rows[:20], 'top_rss': sorted(rows, key=lambda r: -r['rss_mb'])[:20],
            'python_procs': {'count': len(py), 'cpu_pct_one_core_sum': round(sum(r['cpu_pct_one_core'] for r in py), 2),
                             'rss_mb_sum': round(sum(r['rss_mb'] for r in py), 1),
                             'list': [(r['owner'], r['cmd'][:60], r['cpu_pct_one_core'], r['rss_mb']) for r in py]}}


def main():
    cmap = containers()
    a = sample(cmap)
    time.sleep(WINDOW)
    b = sample(cmap)
    res = system_delta(a, b)
    res.update(process_delta(a, b))
    ncpu = res['ncpu']
    res['mem'] = {k: v for k, v in (l.split(':') for l in read('/proc/meminfo').splitlines()[:6])}
    res['loadavg'] = read('/proc/loadavg').strip()
    res['cpu_freq_khz'] = [read('/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq' % i).strip() for i in range(ncpu)]
    res['tegrastats'] = sh('timeout 3 tegrastats --interval 1000 | tail -1', timeout=10).strip()[:300]
    res['units'] = units()
    res['latency'] = [curl_lat('http://127.0.0.1:8099/healthcheck', 30), curl_lat('http://127.0.0.1:8090/health', 30),
                      curl_lat('http://127.0.0.1:2283/api/server/ping', 20), curl_lat('http://127.0.0.1:8080/status.php', 10)]
    api = [n for n, _ in cmap.values() if n.endswith('nasa_api')]
    res['build_health'] = sh('docker exec -i %s python -' % api[0], timeout=180, inp=HEALTH_TIMING).strip()[-1500:] if api else 'no api container'
    res['container_images'] = sorted(set('%s=%s' % (n, i.split('@')[0]) for n, i in cmap.values()))
    res['py_versions'] = {n: sh('docker exec %s python --version 2>&1 || docker exec %s python3 --version 2>&1' % (n, n),
                                timeout=20).strip()[:40] for n, _ in cmap.values()
                          if any(x in n for x in ('api', 'gateway', 'llm', 'stt', 'proxy', 'backup', 'download', 'status'))}
    print(json.dumps(res, ensure_ascii=False))


main()
