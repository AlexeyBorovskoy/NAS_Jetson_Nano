#!/usr/bin/env python3
"""Exercise each new peer in one temporary client network namespace."""
import base64
import configparser
import ipaddress
import json
import os
import pathlib
import secrets
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import awg_control
import awg_material

NS = 'awgst'
HOST_IF = 'awgst-host'
CLIENT_IF = 'awgst-lan'
WG_IF = 'awgtest0'
UAPI = '/run/amneziawg/' + WG_IF + '.sock'
ENDPOINT = None


def run(args, check=True, timeout=10):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('Acceptance command failed: ' + args[0])
    return result


def inside(args, **kwargs):
    return run(['ip', 'netns', 'exec', NS] + args, **kwargs)


def client_payload(config):
    device = config['Interface']
    peer = config['Peer']
    lines = ['private_key=' + base64.b64decode(device['PrivateKey']).hex(),
             'listen_port=0', 'replace_peers=true',
             'header_protection_key=' + base64.b64decode(device['HeaderProtectionKey']).hex()]
    for key, conf_name in awg_material.CONF_NAMES.items():
        lines.append(key + '=' + device[conf_name])
    lines += ['public_key=' + base64.b64decode(peer['PublicKey']).hex(),
              'preshared_key=' + base64.b64decode(peer['PresharedKey']).hex(),
              'endpoint=' + peer['Endpoint'], 'replace_allowed_ips=true',
              'allowed_ip=0.0.0.0/0', 'allowed_ip=::/0',
              'persistent_keepalive_interval=25']
    return 'set=1\n' + '\n'.join(lines) + '\n\n'


DNS_TEST = """import socket,struct,secrets
ident=secrets.randbelow(65536)
question=b''.join(bytes([len(x)])+x.encode() for x in 'example.com'.split('.'))+b'\\0'+struct.pack('!HH',1,1)
query=struct.pack('!HHHHHH',ident,0x0100,1,0,0,0)+question
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.settimeout(4);s.sendto(query,('1.1.1.1',53));data,_=s.recvfrom(4096)
 answer=struct.unpack('!HHHHHH',data[:12])
 assert answer[0]==ident and answer[1]&15==0 and answer[3]>0
print('DNS_OK')
"""


def configure_client(config, proc):
    deadline = time.monotonic() + 8
    while not pathlib.Path(UAPI).exists():
        if proc.poll() is not None or time.monotonic() > deadline:
            raise RuntimeError('Client daemon did not become ready')
        time.sleep(0.1)
    awg_control.ipc_request(UAPI, client_payload(config))
    inside(['ip', 'address', 'add', config['Interface']['Address'], 'dev', WG_IF])
    inside(['ip', 'link', 'set', WG_IF, 'mtu', '1280', 'up'])
    inside(['ip', 'route', 'add', 'default', 'dev', WG_IF])


def probe_dns():
    for _ in range(3):
        result = inside(['python3', '-c', DNS_TEST], check=False, timeout=6)
        if result.returncode == 0 and result.stdout.strip() == 'DNS_OK':
            return True
        time.sleep(0.3)
    return False


def exercise(path, ipify_ip):
    started = time.monotonic()
    config = configparser.ConfigParser(interpolation=None)
    config.read(path)
    env = os.environ.copy()
    env.update(LOG_LEVEL='error', GOMAXPROCS='1')
    proc = subprocess.Popen(['ip', 'netns', 'exec', NS, 'nice', '-n', '10',
                             '/opt/amnezia-awg3-sweden/bin/amneziawg-go', '-f', WG_IF],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    try:
        configure_client(config, proc)
        dns_ok = probe_dns()
        result = inside(['curl', '-4', '--noproxy', '*', '-fsS', '--max-time', '8',
                         '--resolve', 'api.ipify.org:443:' + ipify_ip, 'https://api.ipify.org'],
                        check=False, timeout=10)
        status = awg_control.safe_status(awg_control.ipc_request(UAPI, 'get=1\n\n'))
        https_ok = result.returncode == 0 and result.stdout.strip() == ENDPOINT
        row = {'client': path.stem, 'dns_ok': dns_ok, 'https_ok': https_ok,
               'handshake': status['handshakes'] == 1,
               'duration_ms': round((time.monotonic() - started) * 1000)}
        row['pass'] = all(row[k] for k in ['dns_ok', 'https_ok', 'handshake'])
        return row
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        inside(['ip', 'link', 'delete', WG_IF], check=False)
        if pathlib.Path(UAPI).exists():
            pathlib.Path(UAPI).unlink()


def prepare_network():
    run(['ip', 'link', 'add', HOST_IF, 'type', 'veth', 'peer', 'name', CLIENT_IF])
    run(['ip', 'link', 'set', CLIENT_IF, 'netns', NS])
    run(['ip', 'address', 'add', '10.203.31.1/30', 'dev', HOST_IF])
    run(['ip', 'link', 'set', HOST_IF, 'up'])
    inside(['ip', 'address', 'add', '10.203.31.2/30', 'dev', CLIENT_IF])
    inside(['ip', 'link', 'set', CLIENT_IF, 'up'])
    inside(['ip', 'link', 'set', 'lo', 'up'])
    inside(['ip', 'route', 'add', ENDPOINT + '/32', 'via', '10.203.31.1'])


def main():
    global ENDPOINT
    ENDPOINT = str(ipaddress.IPv4Address(os.environ['AWG_ENDPOINT']))
    if (NS in run(['ip', 'netns', 'list']).stdout.split()
            or run(['ip', 'link', 'show', HOST_IF], check=False).returncode == 0
            or pathlib.Path(UAPI).exists()):
        raise RuntimeError('Temporary test resources are already in use')
    profiles = sorted(pathlib.Path('/opt/amnezia-awg3-sweden/private/clients').glob('*.conf'))
    if len(profiles) != 23:
        raise RuntimeError('Expected exactly 23 profiles')
    ipify_ip = socket.getaddrinfo('api.ipify.org', 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    rows = []
    created = False
    try:
        run(['ip', 'netns', 'add', NS])
        created = True
        prepare_network()
        for path in profiles:
            row = exercise(path, ipify_ip)
            rows.append(row)
            print(json.dumps(row), flush=True)
            if not row['pass']:
                break
    finally:
        run(['ip', 'link', 'delete', HOST_IF], check=False)
        if created:
            run(['ip', 'netns', 'delete', NS])
    result = {'passed': sum(x['pass'] for x in rows), 'requested': 23, 'rows': rows,
              'test_scope': 'synthetic isolated clients on the VPS, not mobile ISP',
              'temporary_namespace_removed': NS not in run(['ip', 'netns', 'list']).stdout.split(),
              'additional_test_firewall_rules': False}
    print('FINAL_RESULT ' + json.dumps(result), flush=True)
    if result['passed'] != 23:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
