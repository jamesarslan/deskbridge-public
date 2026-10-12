#!/usr/bin/env python3
"""Structural test for config/server.conf (Deskflow INI settings, Windows server).

Format verified against the v1.27.0 engine (desktop src/lib/server/Config.cpp
Config::read + src/lib/common/Settings.cpp):
- computer names are declared as [computer_<name>] INI groups with a
  name= key ("general config"); the text config (server.config) carries only
  links + options.
- a legacy [internalConfig] section with a partial screen list SEGFAULTS the
  engine (QList::at() on empty fixArray), so it must NOT be present.

Assertions:
- core: computerName=windows, coreMode=2 (server), port=24800
- exactly the computer groups {computer_windows, computer_fedora} with
  matching name= values
- no internalConfig section
- server: externalConfig enabled, externalConfigFile points at ProgramData/Deskflow/server.config
- security: TLS on, fingerprint checks on (first-run pairing)
- gui: core starts with the GUI app
"""
import configparser
import pathlib
import sys

raw = (pathlib.Path(__file__).resolve().parent.parent / "config" / "server.conf").read_text()
if "#" in raw:
    sys.exit("FAIL: keep server.conf comment-free (engine INI parser strictness unverified)")

c = configparser.ConfigParser()
try:
    c.read_string(raw)
except configparser.Error as e:
    sys.exit(f"FAIL: cannot parse INI: {e}")

if c.has_section("internalConfig"):
    sys.exit("FAIL: legacy [internalConfig] present - v1.27 engine segfaults on partial screen lists")

checks = [
    ("core", "computername", "windows"),
    ("core", "coremode", "2"),
    ("core", "processmode", "1"),
    ("core", "port", "24800"),
    ("server", "externalconfig", "true"),
    ("server", "enableclipboard", "true"),
    ("security", "tlsenabled", "true"),
    ("security", "checkpeerfingerprints", "true"),
    ("gui", "startcorewithgui", "true"),
]
for sec, opt, want in checks:
    got = c.get(sec, opt, fallback=None)
    if got != want:
        sys.exit(f"FAIL: [{sec}] {opt} = {got!r}, want {want!r}")

ext = c.get("server", "externalconfigfile", fallback=None)
if ext != "C:/ProgramData/Deskflow/server.config":
    sys.exit(f"FAIL: externalConfigFile = {ext!r}")

groups = [s for s in c.sections() if s.startswith("computer_")]
want_groups = ["computer_windows", "computer_fedora"]
if groups != want_groups:
    sys.exit(f"FAIL: computer groups = {groups}, want {want_groups} (order: primary first)")
for g in want_groups:
    name = c.get(g, "name", fallback=None)
    want = g.removeprefix("computer_")
    if name != want:
        sys.exit(f"FAIL: [{g}] name = {name!r}, want {want!r}")
print("server INI OK: computer groups declared, TLS + pairing on, no legacy internalConfig")
