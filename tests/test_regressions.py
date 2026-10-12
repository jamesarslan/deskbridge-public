"""Review regressions: real temporary files/HTTP/TLS, mocked system services."""
import argparse
import contextlib
import hashlib
import http.client
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader('review_app', str(ROOT / 'src/deskbridge'))
spec = importlib.util.spec_from_loader(loader.name, loader)
db = importlib.util.module_from_spec(spec)
loader.exec_module(db)

class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        self.paths = db.Paths('review', self.home)
        self.client = dict(db.default_state('review'), role='client', name='client', peer='198.51.100.2', port=24990)
    def tearDown(self):
        self.tmp.cleanup()
    def test_profile_traversal_rejected(self):
        for name in ('../escape', '/', '', 'a/b', 'a\\b', '..', 'x\nEnvironment=evil'):
            with self.assertRaises(ValueError):
                db.Paths(name, self.home)
    def test_merge_preserves_permission_preferences_and_unknown_keys(self):
        self.paths.engine_home.mkdir(parents=True)
        self.paths.engine_conf.write_text('[client]\nxdpRestoreToken=synthetic\n[gui]\nignoreMissingKeyboardLayouts=true\n[custom]\nfutureKey=value\n')
        db.write_engine_conf(self.paths, self.client)
        flat = db.read_engine_conf(self.paths)
        self.assertEqual(flat['client.xdpRestoreToken'], 'synthetic')
        self.assertEqual(flat['gui.ignoreMissingKeyboardLayouts'], 'true')
        self.assertEqual(flat['custom.futureKey'], 'value')
        self.assertEqual(db.write_engine_conf(self.paths, self.client), [])
    def test_valid_legacy_arrays_do_not_invalidate_external_config(self):
        db.write_engine_conf(self.paths, self.client)
        with self.paths.engine_conf.open('a') as f:
            f.write('\n[internalConfig]\nnumRows=1\nnumColumns=2\n')
        self.assertEqual(db.validate_conf(self.paths, self.client), [])
    def test_server_groups_vertical_links_and_trust_store(self):
        state = dict(self.client, role='server', map={'host': {'top': 'guest'}, 'guest': {'bottom': 'host'}}, name='host')
        db.write_engine_conf(self.paths, state)
        db.write_server_map(self.paths, state)
        self.assertEqual(db.validate_conf(self.paths, state), [])
        self.assertEqual(db.read_engine_conf(self.paths)['computer_guest.name'], 'guest')
        self.assertIn('up = guest', self.paths.server_map.read_text())
        self.assertIn('down = host', self.paths.server_map.read_text())
        self.assertEqual(self.paths.trust_db.name, 'trusted-clients')
    def test_fingerprint_check_cannot_be_disabled(self):
        db.write_engine_conf(self.paths, self.client)
        self.paths.engine_conf.write_text(self.paths.engine_conf.read_text().replace('checkPeerFingerprints = true', 'checkPeerFingerprints = false'))
        self.assertTrue(any('checkPeerFingerprints' in s for s in db.validate_conf(self.paths, self.client)))
    def test_scan_size_and_family_bounded(self):
        with patch.object(db, 'tcp_open') as probe:
            for cidr in ('10.0.0.0/8', '::/0'):
                with self.assertRaises(ValueError):
                    db.discover(cidr, 24800)
            probe.assert_not_called()
    def test_ip_output_columns(self):
        result = subprocess.CompletedProcess([], 0, '2: eth0 inet 192.168.1.20/24 brd 192.168.1.255 scope global eth0\n', '')
        with patch.object(db, 'run', return_value=result):
            self.assertEqual(db.local_networks(), [('192.168.1.20', '24')])
    def test_profile_ownership_is_exact(self):
        a = db.Paths('alpha', self.home)
        other = db.Paths('alphabet', self.home)
        process = {'pid': 99, 'name': 'deskflow', 'cmdline': 'deskflow', 'environ': f'XDG_CONFIG_HOME={other.xdg}\0'.encode()}
        with patch.object(db, 'find_engine_processes', return_value=[process]):
            self.assertEqual(db.profile_processes(a), [])
            self.assertEqual(db.profile_processes(db.Paths('default', self.home)), [])
    def test_core_command_has_mode_settings_and_multi_instance(self):
        with patch.object(db.shutil, 'which', return_value='/usr/bin/deskflow-core'):
            command = db.engine_command(self.paths, dict(self.client, engine='core'))
        self.assertEqual(command[1], 'client')
        self.assertIn('--new-instance', command)
        self.assertEqual(command[-1], str(self.paths.engine_conf))
    def test_setup_off_is_off_and_yes_never_trusts(self):
        with patch.object(db, 'Paths', return_value=self.paths), patch.object(db, 'find_engine_processes', return_value=[]), patch.object(db, 'ensure_cert', return_value={'created': False}), patch.object(db, 'cert_fingerprint', return_value='a'*64), patch.object(db, 'deep_probe') as probe, patch.object(db, 'autostart_set', return_value={'enabled': False}) as auto, patch.object(db, 'autostart_enabled', return_value=False), patch.object(db, 'local_layouts', return_value=[]), contextlib.redirect_stdout(io.StringIO()):
            rc = db.main(['--profile', 'review', 'setup', '--yes', '--role', 'client', '--peer', '198.51.100.2', '--name', 'client', '--autostart', 'off'])
        self.assertEqual(rc, 0)
        self.assertIs(auto.call_args.args[1], False)
        probe.assert_not_called()
        self.assertFalse(self.paths.trust_db.exists())
    def test_failed_diagnose_json_exit_nonzero(self):
        with patch.object(db, 'Paths', return_value=self.paths), patch.object(db, '_diagnose_checks', return_value=[{'status': 'fail', 'what': 'test', 'detail': '', 'fix': ''}]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(db.cmd_diagnose(argparse.Namespace(profile='review', json=True)), 1)
    def test_client_repair_does_not_access_absent_firewall(self):
        db.save_state(self.paths, self.client)
        db.write_engine_conf(self.paths, self.client)
        with patch.object(db, 'Paths', return_value=self.paths), patch.object(db, 'profile_processes', return_value=[]), patch.object(db, 'ensure_cert', return_value={'created': False}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(db.cmd_repair(argparse.Namespace(profile='review', json=False)), 0)
    def test_unit_uses_graphical_target_and_profile_marker(self):
        with patch.object(db.shutil, 'which', return_value='/usr/bin/deskflow-core'), patch.object(db, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            db.write_unit(self.paths, dict(self.client, engine='core'))
        text = db.unit_file(self.paths).read_text()
        self.assertIn('WantedBy=graphical-session.target', text)
        self.assertIn('DESKBRIDGE_PROFILE=review', text)
        self.assertIn('XDG_STATE_HOME=', text)
        self.assertIn('StartLimitBurst=3', text)
    def test_uninstall_preserves_foreign_files_and_tls(self):
        db.save_state(self.paths, self.client)
        db.write_engine_conf(self.paths, self.client)
        foreign = self.paths.app_home / 'user-notes.txt'; foreign.write_text('keep')
        self.paths.tls_dir.mkdir(parents=True); self.paths.cert.write_text('synthetic test identity')
        with patch.object(db, 'Paths', return_value=self.paths), patch.object(db, 'stop_engine', return_value={'stopped': True}), patch.object(db, 'autostart_enabled', return_value=False), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(db.cmd_uninstall(argparse.Namespace(profile='review', json=True)), 0)
            self.assertEqual(db.cmd_uninstall(argparse.Namespace(profile='review', json=True)), 0)
        self.assertEqual(foreign.read_text(), 'keep')
        self.assertTrue(self.paths.cert.exists())

class NetworkRegressions(unittest.TestCase):
    def test_real_tls_probe_hashes_der_without_auto_trust(self):
        if not shutil.which('openssl'):
            self.skipTest('OpenSSL unavailable; TLS integration runs on Fedora')
        with tempfile.TemporaryDirectory() as tmp:
            p = db.Paths('tls-test', pathlib.Path(tmp))
            self.assertNotIn('error', db.ensure_cert(p))
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(p.cert))
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0));listener.listen(1);listener.settimeout(10)
                def serve():
                    connection, _ = listener.accept()
                    with connection:
                        with ctx.wrap_socket(connection, server_side=True): pass
                thread = threading.Thread(target=serve);thread.start()
                result = db.deep_probe('127.0.0.1', listener.getsockname()[1], p.cert)
                thread.join(10)
            self.assertTrue(result['ok'], result)
            self.assertFalse(result['verified'])
            self.assertEqual(result['fingerprint'], 'v2:sha256:' + db.cert_fingerprint(p))
            self.assertFalse(p.trust_db.exists())
    def test_http_auth_origin_headers_and_unconfigured_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0));port = sock.getsockname()[1]
            env = dict(os.environ, HOME=tmp, USERPROFILE=tmp, PYTHONDONTWRITEBYTECODE='1')
            process = subprocess.Popen([sys.executable, str(ROOT/'src/deskbridge'), '--profile', 'http-test', 'serve', '--port', str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            try:
                line = process.stderr.readline();token = re.search(r'\?t=([\w-]+)', line).group(1)
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
                connection.request('GET', '/');response = connection.getresponse();body = response.read()
                self.assertEqual(response.status, 200);self.assertTrue(body.endswith(b'</html>\n'))
                self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                connection.close()
                url = f'http://127.0.0.1:{port}/api/status'
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(url, timeout=15)
                self.assertEqual(error.exception.code, 401)
                req = urllib.request.Request(url, headers={'X-DeskBridge-Token': token})
                with urllib.request.urlopen(req, timeout=15) as response:
                    self.assertEqual(json.load(response)['profile'], 'http-test')
                req = urllib.request.Request(url, headers={'X-DeskBridge-Token': token, 'Origin': 'https://untrusted.example'})
                with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(req, timeout=15)
                req = urllib.request.Request(url.replace('/status','/start'), data=b'', headers={'X-DeskBridge-Token': token})
                with urllib.request.urlopen(req, timeout=15) as response:
                    self.assertFalse(json.load(response)['started'])
            finally:
                process.terminate();process.communicate(timeout=10)

if __name__ == '__main__':
    unittest.main(verbosity=2)
