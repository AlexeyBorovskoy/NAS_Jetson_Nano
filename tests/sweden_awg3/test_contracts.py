import base64
import json
import contextlib
import io
import pathlib
import tempfile
import sys
import unittest
from unittest import mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'services/sweden_awg3'))
import awg_control
import awg_material
import accept_clients


class Contracts(unittest.TestCase):
    def setUp(self):
        platform_socket = mock.patch.object(awg_control.socket, 'AF_UNIX', 1, create=True)
        platform_socket.start()
        self.addCleanup(platform_socket.stop)

    def test_status_never_exports_credentials(self):
        text = ('private_key=PRIVATE_MARKER\nheader_protection_key=' + 'a' * 64 + '\n'
                'listen_port=7843\npublic_key=PUBLIC_MARKER\npreshared_key=PSK_MARKER\n'
                'random_trailers=1\ndisable_cookies=0\n'
                'last_handshake_time_sec=10\nrx_bytes=12\ntx_bytes=34\nerrno=0\n\n')
        result = awg_control.safe_status(text)
        self.assertEqual((result['peer_count'], result['handshakes'], result['rx_bytes']), (1, 1, 12))
        self.assertIs(result['random_trailers'], True)
        self.assertIs(result['disable_cookies'], False)
        for marker in ('PRIVATE_MARKER', 'PUBLIC_MARKER', 'PSK_MARKER', 'a' * 64):
            self.assertNotIn(marker, json.dumps(result))

    def test_uapi_failure_is_rejected_without_disclosure(self):
        with mock.patch('awg_control.socket.socket') as factory:
            factory.return_value.__enter__.return_value.recv.return_value = b'private_key=DO_NOT_LOG\nerrno=22\n\n'
            with self.assertRaisesRegex(RuntimeError, '^UAPI operation was rejected$'):
                awg_control.ipc_request('unused', 'get=1\n\n')

    def test_uapi_success_requires_complete_response(self):
        with mock.patch('awg_control.socket.socket') as factory:
            client = factory.return_value.__enter__.return_value
            client.recv.side_effect = [b'listen_port=7843\n', b'errno=0\n', b'\n']
            self.assertEqual(awg_control.ipc_request('unused', 'get=1\n\n'), 'listen_port=7843\nerrno=0\n\n')
            client.sendall.assert_called_once_with(b'get=1\n\n')

    def test_uapi_truncated_response_fails(self):
        with mock.patch('awg_control.socket.socket') as factory:
            factory.return_value.__enter__.return_value.recv.side_effect = [b'errno=0\n', b'']
            with self.assertRaisesRegex(RuntimeError, 'without a terminator'):
                awg_control.ipc_request('unused', 'get=1\n\n')

    def test_single_line_set_acknowledgment_is_valid(self):
        with mock.patch('awg_control.socket.socket') as factory:
            factory.return_value.__enter__.return_value.recv.return_value = b'errno=0\n\n'
            self.assertEqual(awg_control.ipc_request('unused', 'set=1\n\n'), 'errno=0\n\n')

    def test_twenty_three_independent_profiles(self):
        payload, clients = awg_material.generate(23, '198.51.100.10')
        self.assertEqual(len(clients), 23)
        self.assertEqual(len({item['address'] for item in clients}), 23)
        private_keys = set()
        psks = set()
        for item in clients:
            values = dict(line.split(' = ', 1) for line in item['conf'].splitlines() if ' = ' in line)
            private_keys.add(values['PrivateKey'])
            psks.add(values['PresharedKey'])
            self.assertEqual(len(base64.b64decode(values['PrivateKey'])), 32)
            self.assertIn('disable_cookies=false', payload)
            self.assertEqual(values['Endpoint'], '198.51.100.10:7843')
        self.assertEqual(len(private_keys), 23)
        self.assertEqual(len(psks), 23)
        self.assertEqual(payload.count('public_key='), 23)

    def test_invalid_plan_is_rejected(self):
        for count in (0, -1, 255):
            with self.assertRaises(ValueError):
                awg_material.generate(count, '198.51.100.10')

    def test_invalid_port_is_rejected(self):
        for port in (0, 1023, 65536):
            with self.assertRaises(ValueError):
                awg_material.generate(1, '198.51.100.10', port=port)

    def test_boundary_peer_counts_are_supported(self):
        for count in (1, 253):
            _, clients = awg_material.generate(count, '198.51.100.10', port=1024)
            self.assertEqual(len(clients), count)
        self.assertEqual(len(awg_material.generate(1, '198.51.100.10', port=65535)[1]), 1)

    def test_provision_never_overwrites_credentials(self):
        base = pathlib.Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=base) as temporary:
            path = pathlib.Path(temporary).resolve()
            path.relative_to(base)
            self.assertEqual(awg_material.provision(path, '198.51.100.10'), 23)
            original = (path / 'server.uapi').read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'replace existing credentials'):
                awg_material.provision(path, '198.51.100.10')
            self.assertTrue((path / 'server.uapi').read_bytes() == original)

    def test_network_failure_does_not_disclose_command_output(self):
        with mock.patch('awg_control.subprocess.run') as execute:
            execute.return_value.returncode = 1
            execute.return_value.stderr = 'DO_NOT_DISCLOSE'
            with self.assertRaisesRegex(RuntimeError, '^Host network operation failed: ip$'):
                awg_control.run(['ip', 'link'])

    def test_start_validates_configuration_before_network_changes(self):
        good = {'peer_count': 23, 'listen_port': '7843', 'header_protection_enabled': True,
                'random_trailers': True, 'disable_cookies': False}
        invalid = [dict(good, peer_count=22), dict(good, header_protection_enabled=False),
                   dict(good, random_trailers=False), dict(good, disable_cookies=True)]
        with mock.patch('awg_control.pathlib.Path.exists', return_value=True), \
             mock.patch('pathlib.Path.read_text', return_value='dummy-payload'), \
             mock.patch('awg_control.ipc_request', return_value='errno=0\n\n'), \
             mock.patch('awg_control.safe_status') as inspect, \
             mock.patch('awg_control.run') as network:
            for status in invalid:
                inspect.return_value = status
                with self.assertRaises(RuntimeError):
                    awg_control.start()
            network.assert_not_called()
            inspect.return_value = good
            with contextlib.redirect_stdout(io.StringIO()):
                awg_control.start()
            self.assertEqual(network.call_count, 2)

    def test_start_socket_timeout_is_bounded(self):
        with mock.patch('awg_control.pathlib.Path.exists', return_value=False), \
             mock.patch('awg_control.time.monotonic', side_effect=[0, 13]), \
             mock.patch('awg_control.run') as network:
            with self.assertRaisesRegex(RuntimeError, 'did not become ready'):
                awg_control.start()
            network.assert_not_called()

    def test_unknown_control_action_is_rejected(self):
        with mock.patch('awg_control.sys.argv', ['ctl', 'unknown']):
            with self.assertRaises(SystemExit):
                awg_control.main()

    def test_acceptance_requires_valid_explicit_endpoint_before_host_access(self):
        with mock.patch.dict('os.environ', {'AWG_ENDPOINT': 'invalid'}), \
             mock.patch('accept_clients.run') as network:
            with self.assertRaises(ValueError):
                accept_clients.main()
            network.assert_not_called()

    def test_acceptance_preserves_existing_namespace(self):
        with mock.patch.dict('os.environ', {'AWG_ENDPOINT': '198.51.100.10'}), \
             mock.patch('accept_clients.run') as network, \
             mock.patch('accept_clients.subprocess.Popen') as daemon:
            network.return_value.stdout = 'awgst (id: 0)\n'
            with self.assertRaisesRegex(RuntimeError, 'already in use'):
                accept_clients.main()
            network.assert_called_once_with(['ip', 'netns', 'list'])
            daemon.assert_not_called()

    def test_acceptance_cleans_up_client_when_configuration_fails(self):
        with mock.patch('accept_clients.configparser.ConfigParser'), \
             mock.patch('accept_clients.subprocess.Popen') as daemon, \
             mock.patch('accept_clients.configure_client', side_effect=RuntimeError('rejected')), \
             mock.patch('accept_clients.inside') as network, \
             mock.patch('accept_clients.pathlib.Path.exists', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'rejected'):
                accept_clients.exercise(pathlib.Path('unused.conf'), '198.51.100.20')
            daemon.return_value.terminate.assert_called_once_with()
            daemon.return_value.wait.assert_called_once_with(timeout=5)
            network.assert_called_once_with(['ip', 'link', 'delete', 'awgtest0'], check=False)


if __name__ == '__main__':
    unittest.main()
