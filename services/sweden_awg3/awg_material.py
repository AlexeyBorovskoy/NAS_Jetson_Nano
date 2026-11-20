#!/usr/bin/env python3
"""Generate independent AWG identities; never print credentials."""
import base64
import ipaddress
import os
import pathlib
import secrets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

PARAMETERS = {'jc': '4', 'jmin': '10', 'jmax': '50', 's1': '12', 's2': '12',
              's3': '12', 's4': '12', 'h1': '1', 'h2': '2', 'h3': '3', 'h4': '4',
              'random_trailers': 'true', 'disable_cookies': 'false'}
CONF_NAMES = {'jc': 'Jc', 'jmin': 'Jmin', 'jmax': 'Jmax', 's1': 'S1', 's2': 'S2',
              's3': 'S3', 's4': 'S4', 'h1': 'H1', 'h2': 'H2', 'h3': 'H3', 'h4': 'H4',
              'random_trailers': 'RandomTrailers', 'disable_cookies': 'DisableCookies'}


def encode(value):
    return base64.b64encode(value).decode('ascii')


def identity():
    data = bytearray(secrets.token_bytes(32))
    data[0] &= 248
    data[31] = (data[31] & 127) | 64
    private = bytes(data)
    public = X25519PrivateKey.from_private_bytes(private).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return private, public


def generate(count, endpoint, port=7843, subnet='10.73.3.0/24'):
    network = ipaddress.ip_network(subnet)
    if not 1 <= count <= network.num_addresses - 3:
        raise ValueError('Peer count does not fit the dedicated subnet')
    ipaddress.IPv4Address(endpoint)
    if not 1024 <= port <= 65535:
        raise ValueError('Expected a non-privileged UDP port')
    server_private, server_public = identity()
    protection = secrets.token_bytes(32)
    server = ['private_key=' + server_private.hex(), 'listen_port=' + str(port),
              'replace_peers=true', 'header_protection_key=' + protection.hex()]
    server += [key + '=' + value for key, value in PARAMETERS.items()]
    clients = []
    for index in range(1, count + 1):
        private, public = identity()
        psk = secrets.token_bytes(32)
        address = str(network.network_address + index + 1)
        server += ['public_key=' + public.hex(), 'preshared_key=' + psk.hex(),
                   'replace_allowed_ips=true', 'allowed_ip=' + address + '/32']
        lines = ['[Interface]', 'PrivateKey = ' + encode(private), 'Address = ' + address + '/32',
                 'DNS = 1.1.1.1, 8.8.8.8', 'MTU = 1280',
                 'HeaderProtectionKey = ' + encode(protection)]
        lines += [CONF_NAMES[key] + ' = ' + value for key, value in PARAMETERS.items()]
        lines += ['', '[Peer]', 'PublicKey = ' + encode(server_public),
                  'PresharedKey = ' + encode(psk), 'AllowedIPs = 0.0.0.0/0, ::/0',
                  'Endpoint = ' + endpoint + ':' + str(port), 'PersistentKeepalive = 25', '']
        clients.append({'id': 'SE-AWG3-' + str(index).zfill(2), 'address': address,
                        'conf': '\n'.join(lines)})
    return '\n'.join(server) + '\n', clients


def write_new(path, contents):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='ascii', newline='\n') as stream:
        stream.write(contents)


def provision(root, endpoint):
    root = pathlib.Path(root)
    if (root / 'server.uapi').exists() or (root / 'clients').exists():
        raise RuntimeError('Refusing to replace existing credentials')
    payload, clients = generate(23, endpoint)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    (root / 'clients').mkdir(mode=0o700)
    write_new(root / 'server.uapi', payload)
    for client in clients:
        write_new(root / 'clients' / (client['id'] + '.conf'), client['conf'])
    return len(clients)
