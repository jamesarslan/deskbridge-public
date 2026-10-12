#!/usr/bin/env python3
"""Fetch the unmodified official installer; never redistribute it in our ZIPs."""
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request

root = pathlib.Path(__file__).resolve().parent.parent
manifest = json.loads((root / 'ci/manifest.json').read_text())
release = dict(line.strip().split('=', 1) for line in pathlib.Path('/etc/os-release').read_text().splitlines() if '=' in line)
if release.get('ID') != 'fedora' or release.get('VERSION_ID', '').strip('"') != '44' or platform.machine() != 'x86_64':
    sys.exit('This installer supports Fedora 44 x86_64. Install Deskflow >=1.27 from your distribution on other Linux systems.')
installed = subprocess.run(['rpm', '-q', '--qf', '%{VERSION}', 'deskflow'], capture_output=True, text=True)
if installed.returncode == 0 and installed.stdout in (manifest['version'], manifest['version'] + '.0'):
    print('Pinned Deskflow engine already installed; no package changes.')
    sys.exit(0)
artifact = manifest['artifacts']['fedora44']
cache = pathlib.Path.home() / '.cache/deskbridge/downloads'
cache.mkdir(parents=True, exist_ok=True)
destination = cache / artifact['file']
def valid(path):
    return path.is_file() and path.stat().st_size == artifact['size'] and hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256']
if not destination.exists():
    fd, name = tempfile.mkstemp(dir=cache)
    try:
        with os.fdopen(fd, 'wb') as output, urllib.request.urlopen(artifact['url'], timeout=120) as source:
            shutil.copyfileobj(source, output)
        if not valid(pathlib.Path(name)):
            sys.exit('Upstream installer size/SHA256 mismatch; installation refused.')
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)
if not valid(destination):
    sys.exit('Cached engine size/SHA256 mismatch. Remove the cache file and retry.')
command = ['dnf', 'install', str(destination)]
if os.geteuid() != 0:
    command.insert(0, 'sudo')
sys.exit(subprocess.call(command))
