#!/usr/bin/env python3
"""Structural test for config/server.config (Deskflow v1.27 text config).

Engine-verified constraints (v1.27.0):
- '#' lines are rejected by the text-config parser.
- the only valid sections are `links` and `options`; computer names are NOT
  declared here - they must exist in the general config's [internalConfig]
  (see config/server.conf / test_server_ini.py).

Assertions:
- only sections {links, options} exist
- both computers {windows, fedora} appear, windows first (primary screen)
- fedora is linked to the LEFT of windows; windows to the RIGHT of fedora
- no other links exist
- options enables clipboardSharing
"""
import pathlib
import re
import sys

TEXT = (pathlib.Path(__file__).resolve().parent.parent / "config" / "server.config").read_text()

for raw in TEXT.splitlines():
    if "#" in raw:
        sys.exit(f"FAIL: '#' is not allowed in server.config (engine parser rejects it): {raw!r}")

lines = [raw for raw in TEXT.splitlines() if raw.strip()]

sections = {}
order = []
cur = None
sub = None
for line in lines:
    s = line.strip()
    m = re.match(r"section:\s*(\S+)", s)
    if m:
        cur = m.group(1)
        sections.setdefault(cur, {})
        sub = None
        continue
    if s == "end":
        cur = None
        sub = None
        continue
    if cur is None:
        sys.exit(f"FAIL: content outside a section: {line!r}")
    if s.endswith(":"):
        sub = s[:-1].strip()
        if sub not in order:
            order.append(sub)
        sections[cur].setdefault(sub, {})
        continue
    m = re.match(r"(\w+)\s*=\s*(.+)", s)
    if not m:
        sys.exit(f"FAIL: unparsed line: {line!r}")
    key, val = m.group(1), m.group(2).strip()
    if cur == "links":
        if sub is None:
            sys.exit(f"FAIL: link entry before a computer name: {line!r}")
        sections[cur][sub][key] = val
    else:
        sections[cur].setdefault(None, {})[key] = val

if set(sections) != {"links", "options"}:
    sys.exit(f"FAIL: valid sections are links+options only, got {sorted(sections)}")
links = sections["links"]
assert set(links) == {"windows", "fedora"}, f"FAIL: unexpected computers: {sorted(links)}"
assert order[:2] == ["windows", "fedora"], f"FAIL: primary screen must be listed first: {order[:2]}"
assert links["windows"].get("left") == "fedora", "FAIL: windows.left must be fedora"
assert links["fedora"].get("right") == "windows", "FAIL: fedora.right must be windows"
assert set(links["windows"]) == {"left"}, f"FAIL: windows has extra links: {links['windows']}"
assert set(links["fedora"]) == {"right"}, f"FAIL: fedora has extra links: {links['fedora']}"
opts = sections["options"].get(None, {})
assert opts.get("clipboardSharing") == "true", f"FAIL: clipboardSharing must be true, got {opts}"
print("server config OK: windows primary, fedora on left, clipboardSharing=true")
