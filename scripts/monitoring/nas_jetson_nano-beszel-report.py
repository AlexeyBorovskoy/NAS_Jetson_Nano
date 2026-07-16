#!/usr/bin/env python3
"""
NAS_Jetson_Nano — Beszel metrics for Telegram daily report.
Runs on VPS (localhost access to Hub). Called from Jetson via SSH.
Reads credentials from /etc/nas_jetson_nano-monitor/beszel.env or uses defaults.
Output: plain text, one block per system.
"""
import urllib.request, urllib.error, json, os, sys
from datetime import timedelta

CONF_FILE = '/etc/nas_jetson_nano-monitor/beszel.env'
HUB_URL = 'http://localhost:8091/api'
ADMIN_EMAIL = 'admin@nas_jetson_nano.local'
ADMIN_PASS = ''

# read credentials from env file
if os.path.exists(CONF_FILE):
    with open(CONF_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            v = v.strip('"\'')
            if k == 'BESZEL_ADMIN_EMAIL':
                ADMIN_EMAIL = v
            elif k == 'BESZEL_ADMIN_PASS':
                ADMIN_PASS = v
            elif k == 'BESZEL_HUB_URL':
                HUB_URL = v + '/api'

# also accept env vars for override
ADMIN_EMAIL = os.environ.get('BESZEL_ADMIN_EMAIL', ADMIN_EMAIL)
ADMIN_PASS = os.environ.get('BESZEL_ADMIN_PASS', ADMIN_PASS)

if not ADMIN_PASS:
    print('  ⚠️ Beszel credentials not configured (/etc/nas_jetson_nano-monitor/beszel.env)')
    sys.exit(0)


def api(method, path, data=None, token=None):
    url = HUB_URL + path
    body = json.dumps(data).encode() if data else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = token
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except Exception as e:
        return {'_error': str(e)}


def fmt_bytes(bps):
    """Format bytes per second to human-readable."""
    if bps < 1024:
        return f'{bps:.0f} B/s'
    if bps < 1024 * 1024:
        return f'{bps/1024:.1f} KB/s'
    return f'{bps/1024/1024:.1f} MB/s'


def fmt_uptime(seconds):
    td = timedelta(seconds=int(seconds))
    d = td.days
    h, rem = divmod(td.seconds, 3600)
    m = rem // 60
    if d > 0:
        return f'{d}d {h}h {m}m'
    return f'{h}h {m}m'


try:
    # authenticate
    r = api('POST', '/collections/_superusers/auth-with-password',
            {'identity': ADMIN_EMAIL, 'password': ADMIN_PASS})
    if '_error' in r or 'token' not in r:
        print(f'  ⚠️ Beszel Hub auth failed: {r.get("message", r.get("_error", "?"))}')
        sys.exit(0)
    tok = r['token']

    # get all systems
    r = api('GET', '/collections/systems/records?perPage=50', token=tok)
    systems = r.get('items', [])

    if not systems:
        print('  ⚠️ No systems registered in Beszel Hub')
        sys.exit(0)

    lines = []
    has_warnings = []

    for s in systems:
        name = s['name']
        status = s['status']
        info = s.get('info', {})
        sid = s['id']

        # get latest 1-minute stats for richer data
        stats_r = api('GET',
            f'/collections/system_stats/records?filter=system%3D%22{sid}%22%26%26type%3D%221m%22&sort=-created&perPage=1',
            token=tok)
        stats = {}
        if stats_r.get('items'):
            stats = stats_r['items'][0].get('stats', {})

        icon = '✅' if status == 'up' else '❌'
        if status != 'up':
            has_warnings.append(f'Beszel: {name} is {status}')

        # uptime
        uptime_sec = info.get('u', 0)
        uptime_str = fmt_uptime(uptime_sec) if uptime_sec else '?'

        # version
        ver = info.get('v', '?')

        # CPU
        cpu = stats.get('cpu', info.get('cpu', 0))
        cpub = stats.get('cpub', [])  # [user,nice,sys,iowait,idle]
        iowait = cpub[3] if len(cpub) > 3 else None

        # RAM
        mu = stats.get('mu', 0)   # used GB
        m_total = stats.get('m', 0)    # total GB
        mp = stats.get('mp', info.get('mp', 0))

        # Disk
        du = stats.get('du', 0)
        d_total = stats.get('d', 0)
        dp = stats.get('dp', info.get('dp', 0))

        # Temperature (Jetson has GPU temp)
        temps = stats.get('t', {})
        temp_str = ''
        if temps:
            temp_parts = [f'{k}: {v:.1f}°C' for k, v in temps.items()
                         if k in ('GPU', 'CPU', 'CPU-therm', 'GPU-therm')]
            if not temp_parts:
                temp_parts = [f'{k}: {v:.1f}°C' for k, v in list(temps.items())[:2]]
            temp_str = ' | '.join(temp_parts)

        # Load
        la = stats.get('la', info.get('la', []))
        load_str = ' '.join(f'{x:.2f}' for x in la[:3]) if la else '?'

        # Network bandwidth
        b = stats.get('b', info.get('bb', None))
        net_str = ''
        if isinstance(b, list) and len(b) >= 2:
            net_str = f'↓{fmt_bytes(b[0])} ↑{fmt_bytes(b[1])}'
        elif isinstance(b, (int, float)) and b > 0:
            net_str = f'{fmt_bytes(b)}'

        lines.append(f'  {icon} {name} (v{ver}, up {uptime_str})')
        lines.append(f'     CPU: {cpu:.1f}%{(" iowait "+str(round(iowait,1))+"%") if iowait else ""}'
                     f' | RAM: {mu:.1f}/{m_total:.1f} GB ({mp:.0f}%)'
                     f' | Disk: {du:.1f}/{d_total:.1f} GB ({dp:.0f}%)')
        if temp_str:
            lines.append(f'     Temp: {temp_str}')
        lines.append(f'     Load: {load_str}' + (f' | Net: {net_str}' if net_str else ''))

    print('\n'.join(lines))

    # print warnings for the calling script to pick up
    for w in has_warnings:
        print(f'__WARN__:{w}', file=sys.stderr)

except Exception as e:
    print(f'  ⚠️ Beszel report error: {e}')
