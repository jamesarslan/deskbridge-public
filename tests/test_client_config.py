#!/usr/bin/env python3
"""Structural test for config/client.conf (Deskflow INI config, Fedora client)."""
import configparser
import pathlib
import sys

c = configparser.ConfigParser()
try:
    c.read(pathlib.Path(__file__).resolve().parent.parent / "config" / "client.conf")
except configparser.Error as e:
    sys.exit(f"FAIL: cannot parse INI: {e}")

checks = [
    ("core", "computername", "fedora"),
    ("core", "coremode", "1"),
    ("core", "port", "24800"),
    ("client", "remotehost", "192.168.1.10"),
    ("security", "tlsenabled", "true"),
    ("security", "checkpeerfingerprints", "true"),
    ("gui", "startcorewithgui", "true"),
]
for sec, opt, want in checks:
    got = c.get(sec, opt, fallback=None)
    if got != want:
        sys.exit(f"FAIL: [{sec}] {opt} = {got!r}, want {want!r}")
print("client config OK: client mode, remoteHost=192.168.1.10 (sample), TLS + fingerprint checks on")
