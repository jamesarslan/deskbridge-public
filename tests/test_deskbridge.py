#!/usr/bin/env python3
"""Regression tests for the DeskBridge app core (pure logic, no root, no display).

Run: python3 tests/test_deskbridge.py
"""
import importlib.machinery
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader(
    "deskbridge_app", str(ROOT / "src" / "deskbridge"))
spec = importlib.util.spec_from_loader("deskbridge_app", loader)
db = importlib.util.module_from_spec(spec)
loader.exec_module(db)


class TestVersion(unittest.TestCase):
    def test_app_version_reads_repo_version(self):
        v = db.app_version()
        self.assertTrue(v, "version parsed")
        repo = json.loads((ROOT / "VERSION").read_text())["version"]
        self.assertEqual(v, repo)

    def test_parse_version_ordering(self):
        self.assertLess(db.parse_version("1.26.0"), db.parse_version("1.27.0"))
        self.assertEqual(db.parse_version("v1.27.0 (build 5)"), (1, 27, 0))
        self.assertEqual(db.parse_version("unknown"), (0, 0, 0))


class TestPaths(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_profile_uses_standard_engine_paths(self):
        p = db.Paths("default", self.home)
        self.assertIsNone(p.xdg)
        self.assertEqual(p.engine_home, self.home / ".config" / "Deskflow")
        self.assertEqual(p.engine_conf, self.home / ".config" / "Deskflow" / "Deskflow.conf")
        self.assertEqual(p.port, 24800)
        self.assertEqual(p.unit, "deskbridge-default")
        self.assertEqual(p.log_file, self.home / ".local" / "state" / "deskbridge" / "default.log")
        self.assertEqual(p.state_file, self.home / ".config" / "DeskBridge" / "default" / "deskbridge.json")

    def test_nondefault_profile_isolated_with_distinct_port(self):
        a = db.Paths("alpha", self.home)
        b = db.Paths("beta", self.home)
        self.assertEqual(a.xdg, a.app_home / "xdg")
        self.assertEqual(a.engine_home, a.app_home / "xdg" / "Deskflow")
        self.assertNotEqual(a.engine_conf, db.Paths("default", self.home).engine_conf)
        self.assertNotEqual(a.port, 24800)
        self.assertNotEqual(a.port, b.port)
        self.assertEqual(db.Paths("alpha", self.home).port, a.port)  # stable
        self.assertTrue(24800 < a.port < 24901)


class TestState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.paths = db.Paths("default", pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_roundtrip_and_defaults(self):
        st = db.default_state("default")
        self.assertIsNone(st["role"])
        self.assertFalse(st["wizard_done"])
        st.update(role="client", name="fedora", peer="192.168.1.10")
        db.save_state(self.paths, st)
        loaded = db.load_state(self.paths)
        self.assertEqual(loaded["role"], "client")
        self.assertEqual(loaded["name"], "fedora")
        self.assertEqual(loaded["peer"], "192.168.1.10")
        self.assertIsNotNone(loaded["updated"])
        self.assertEqual(loaded["engine"], "gui")

    def test_load_state_tolerates_corrupt_file(self):
        self.paths.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.paths.state_file.write_text("{not json")
        st = db.load_state(self.paths)
        self.assertEqual(st, db.default_state("default"))


class TestEngineConf(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.paths = db.Paths("default", pathlib.Path(self._tmp.name))
        self.client = dict(db.default_state("default"), role="client", name="fedora", peer="192.168.1.10")
        self.server = dict(db.default_state("default"), role="server", name="windows",
                            map={"windows": {"left": "fedora"}, "fedora": {"right": "windows"}})

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_client_conf_is_valid_and_backs_up(self):
        self.paths.engine_conf.parent.mkdir(parents=True)
        self.paths.engine_conf.write_text("[core]\ncomputerName = old\n")
        backups = db.write_engine_conf(self.paths, self.client)
        self.assertEqual(len(backups), 1)
        self.assertIn("[core]", self.paths.engine_conf.read_text())
        self.assertEqual(db.validate_conf(self.paths, self.client), [])
        flat = db.read_engine_conf(self.paths)
        self.assertEqual(flat["core.computerName"], "fedora")
        self.assertEqual(flat["core.coreMode"], "1")
        self.assertEqual(flat["core.port"], "24800")
        self.assertEqual(flat["client.remoteHost"], "192.168.1.10")
        self.assertEqual(flat["security.tlsEnabled"], "true")
        self.assertEqual(flat["security.checkPeerFingerprints"], "true")

    def test_write_server_conf_and_map(self):
        db.write_engine_conf(self.paths, self.server)
        db.write_server_map(self.paths, self.server)
        self.assertEqual(db.validate_conf(self.paths, self.server), [])
        flat = db.read_engine_conf(self.paths)
        self.assertEqual(flat["core.coreMode"], "2")
        self.assertEqual(flat["server.externalConfig"], "true")
        self.assertEqual(flat["server.externalConfigFile"], str(self.paths.server_map))
        self.assertEqual(flat["server.enableClipboard"], "true")
        text = self.paths.server_map.read_text()
        self.assertIn("section: links", text)
        self.assertIn("fedora:", text)
        self.assertIn("    right = windows", text)
        self.assertIn("windows:", text)
        self.assertIn("    left = fedora", text)
        self.assertIn("clipboardSharing = true", text)

    def test_validate_conf_detects_broken_configs(self):
        db.write_engine_conf(self.paths, self.client)
        # TLS off is never acceptable
        bad = self.paths.engine_conf.read_text().replace("tlsEnabled = true", "tlsEnabled = false")
        self.paths.engine_conf.write_text(bad)
        self.assertTrue(any("tlsEnabled" in e for e in db.validate_conf(self.paths, self.client)))
        # missing remoteHost
        self.paths.engine_conf.write_text("[core]\ncomputerName = fedora\n[client]\n")
        self.assertTrue(any("remoteHost" in e for e in db.validate_conf(self.paths, self.client)))
        # externalConfigFile + legacy internalConfig conflict
        self.paths.engine_conf.write_text("[core]\ncomputerName = windows\n"
                                           "[server]\nexternalConfigFile = /tmp/x\n"
                                           "[internalConfig]\nwindows:\n    left = fedora\nend\n")
        self.assertTrue(any("internalConfig" in e for e in db.validate_conf(self.paths, self.server)))
        # missing screen map
        self.server["map"] = {"windows": {"left": "fedora"}}
        self.paths.engine_conf.write_text("[core]\ncomputerName = windows\n"
                                           "[server]\nexternalConfig = true\n"
                                           f"externalConfigFile = {self.paths.server_map}\n"
                                           "enableClipboard = true\nswitchDelay = 250\n")
        errs = db.validate_conf(self.paths, self.server)
        self.assertTrue(any("screen map" in e for e in errs))


class TestAdopt(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.paths = db.Paths("default", pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _write_client_conf(self):
        self.paths.engine_conf.parent.mkdir(parents=True, exist_ok=True)
        self.paths.engine_conf.write_text(
            "[core]\ncomputerName = fedora\ncoreMode = 1\nport = 24800\n"
            "[client]\nremoteHost = 192.168.1.10\n")

    def test_adopts_client_from_legacy_conf(self):
        self._write_client_conf()
        st = db.adopt_state(self.paths, db.default_state("default"))
        self.assertEqual(st["role"], "client")
        self.assertEqual(st["name"], "fedora")
        self.assertEqual(st["peer"], "192.168.1.10")

    def test_adopts_server_from_core_mode_2(self):
        self._write_client_conf()
        self.paths.engine_conf.write_text(
            "[core]\ncomputerName = windows\ncoreMode = 2\nport = 24800\n"
            "[server]\nexternalConfig = true\n")
        st = db.adopt_state(self.paths, db.default_state("default"))
        self.assertEqual(st["role"], "server")
        self.assertEqual(st["name"], "windows")

    def test_no_conf_or_bad_mode_leaves_state_untouched(self):
        st0 = db.default_state("default")
        self.assertEqual(db.adopt_state(self.paths, st0), st0)
        self.paths.engine_conf.parent.mkdir(parents=True, exist_ok=True)
        self.paths.engine_conf.write_text("[core]\ncomputerName = x\n")
        self.assertEqual(db.adopt_state(self.paths, st0), st0)

    def test_existing_role_never_overwritten(self):
        self._write_client_conf()
        st = dict(db.default_state("default"), role="server", name="other")
        self.assertEqual(db.adopt_state(self.paths, st), st)


class TestFingerprints(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.paths = db.Paths("default", pathlib.Path(self._tmp.name))
        self.fp = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def tearDown(self):
        self._tmp.cleanup()

    def test_canon_normalizes_prefix_and_case(self):
        self.assertEqual(db.fingerprint_canon(self.fp), f"v2:sha256:{self.fp}")
        self.assertEqual(db.fingerprint_canon("v2:sha256:" + self.fp.upper()),
                         f"v2:sha256:{self.fp}")
        with self.assertRaises(ValueError):
            db.fingerprint_canon("v2:sha256:beef")
        with self.assertRaises(ValueError):
            db.fingerprint_canon("sha1:" + self.fp)

    def test_trust_add_list_remove(self):
        self.assertTrue(db.trust_add(self.paths, self.fp)["added"])
        self.assertFalse(db.trust_add(self.paths, "v2:sha256:" + self.fp.upper())["added"])
        self.assertEqual(db.trust_lines(self.paths), [f"v2:sha256:{self.fp}"])
        self.assertTrue(db.trust_remove(self.paths, self.fp)["removed"])
        self.assertFalse(db.trust_remove(self.paths, self.fp)["removed"])
        self.assertEqual(db.trust_lines(self.paths), [])


class TestFirewallRule(unittest.TestCase):
    def test_rich_rule_scoped_to_peer(self):
        rule = db.rich_rule("192.168.1.10", 24800)
        self.assertEqual(
            rule,
            'rule family="ipv4" source address="192.168.1.10" '
            'port port="24800" protocol="tcp" accept')

    def test_sides_are_symmetric(self):
        self.assertEqual(db.SIDES["left"], "right")
        self.assertEqual(db.SIDES["bottom"], "top")
        for side, other in db.SIDES.items():
            self.assertEqual(db.SIDES[other], side)


if __name__ == "__main__":
    unittest.main(verbosity=2)
