#!/usr/bin/env python3
"""Configure the isolated Sweden AWG service without logging key material."""
import json
import pathlib
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path('/opt/amnezia-awg3-sweden')
INTERFACE = 'awgse0'
ADDRESS = '10.73.3.1/24'
SUBNET = '10.73.3.0/24'
WAN = 'enp0s3'
SOCKET = '/run/amneziawg/awgse0.sock'
NAT = ['/usr/sbin/iptables', '-w', '5', '-t', 'nat']
NAT_RULE = ['POSTROUTING', '-s', SUBNET, '-o', WAN, '-m', 'comment',
            '--comment', 'amnezia-awg3-sweden', '-j', 'MASQUERADE']


def ipc_request(path, payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(path)
        client.sendall(payload.encode('ascii'))
        data = b''
        while not data.endswith(b'\n\n'):
            block = client.recv(65536)
            if not block:
                raise RuntimeError('UAPI response ended without a terminator')
            data += block
            if len(data) > 1048576:
                raise RuntimeError('UAPI response exceeded the limit')
    text = data.decode('ascii')
    lines = text[:-2].splitlines()
    if not lines or lines[-1] != 'errno=0':
        raise RuntimeError('UAPI operation was rejected')
    return text


def boolean(value):
    if value not in ('0', '1'):
        raise RuntimeError('Invalid UAPI boolean')
    return value == '1'


COUNTERS = {'public_key': ('peer_count', lambda value: 1),
            'last_handshake_time_sec': ('handshakes', lambda value: int(value) > 0),
            'rx_bytes': ('rx_bytes', int), 'tx_bytes': ('tx_bytes', int)}
VALUES = {'listen_port': ('listen_port', str),
          'random_trailers': ('random_trailers', boolean),
          'disable_cookies': ('disable_cookies', boolean),
          'header_protection_key': ('header_protection_enabled', lambda value: value != '0' * 64)}


def safe_status(text):
    result = dict(peer_count=0, handshakes=0, rx_bytes=0, tx_bytes=0)
    for line in text.splitlines():
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key in COUNTERS:
            name, convert = COUNTERS[key]
            result[name] += convert(value)
        elif key in VALUES:
            name, convert = VALUES[key]
            result[name] = convert(value)
    return result


def run(arguments, check=True):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
    if check and result.returncode:
        raise RuntimeError('Host network operation failed: ' + arguments[0])
    return result.returncode


def nat_present():
    code = run(NAT + ['-C'] + NAT_RULE, check=False)
    if code not in (0, 1):
        raise RuntimeError('Cannot inspect the service NAT rule')
    return code == 0


def start():
    deadline = time.monotonic() + 12
    while not pathlib.Path(SOCKET).exists():
        if time.monotonic() >= deadline:
            raise RuntimeError('Service UAPI socket did not become ready')
        time.sleep(0.1)
    payload = (ROOT / 'private/server.uapi').read_text(encoding='ascii')
    ipc_request(SOCKET, 'set=1\n' + payload.rstrip('\n') + '\n\n')
    status = safe_status(ipc_request(SOCKET, 'get=1\n\n'))
    if status.get('peer_count') != 23 or status.get('listen_port') != '7843':
        raise RuntimeError('Applied service identity does not match the plan')
    if not status.get('header_protection_enabled'):
        raise RuntimeError('Header protection was not enabled')
    if status.get('random_trailers') is not True or status.get('disable_cookies') is not False:
        raise RuntimeError('AWG 3.1 protection settings do not match the plan')
    run(['/usr/sbin/ip', 'address', 'replace', ADDRESS, 'dev', INTERFACE])
    run(['/usr/sbin/ip', 'link', 'set', 'dev', INTERFACE, 'mtu', '1280', 'up'])
    print(json.dumps(status, sort_keys=True))


def stop():
    run(['/usr/sbin/ip', 'link', 'delete', 'dev', INTERFACE], check=False)


def nat_start():
    if not nat_present():
        run(NAT + ['-A'] + NAT_RULE)


def nat_stop():
    if nat_present():
        run(NAT + ['-D'] + NAT_RULE)


def main():
    actions = {'start': start, 'stop': stop,
               'nat-start': nat_start, 'nat-stop': nat_stop,
               'status': lambda: print(json.dumps(safe_status(ipc_request(SOCKET, 'get=1\n\n'))))}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        raise SystemExit('Expected start, stop, status, nat-start or nat-stop')
    actions[sys.argv[1]]()


if __name__ == '__main__':
    main()
