#!/usr/bin/env python3
"""Build reproducible product-only ZIPs; setup fetches official engine binaries."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLE_FILES = [
    'README.md','LICENSE','NOTICE.md','VERSION','ARCHITECTURE.md',
    'CONTRIBUTING.md','SECURITY.md','CODE_OF_CONDUCT.md','ROADMAP.md',
    'docs/TESTING.md','docs/SETUP-WINDOWS.md','docs/SETUP-FEDORA.md','docs/WAYLAND.md',
    'src/deskbridge','tools/DeskBridge.ps1','tools/install-fedora.py','ci/manifest.json',
    'ci/package_bundles.py','tests/test_deskbridge.py','tests/test_regressions.py',
    'tests/test_windows.ps1','tests/integration-fedora.py',
]
def digest(data):
    return hashlib.sha256(data).hexdigest()
def source_bytes(rel):
    data=(ROOT/rel).read_bytes().replace(b'\r\n', b'\n')
    return data.replace(b'\n', b'\r\n') if rel.endswith(('.ps1','.cmd')) else data
def main():
    stage = pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'stage'
    release = stage/'release';release.mkdir(parents=True, exist_ok=True)
    version = json.loads((ROOT/'VERSION').read_text())['version']
    commit = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    sums=[]
    for platform, launcher in (('win64','Setup.cmd'),('fedora44','Setup.sh')):
        name=f'deskbridge-{platform}-{version}'
        files={rel:source_bytes(rel) for rel in [*BUNDLE_FILES,launcher]}
        files['SOURCE-REVISION.txt']=(commit+'\n').encode()
        files['SHA256SUMS.files']=''.join(f'{digest(data)}  {rel}\n' for rel,data in sorted(files.items())).encode()
        target=release/(name+'.zip')
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
            for rel,data in sorted(files.items()):
                entry=zipfile.ZipInfo(f'{name}/{rel}',date_time=(1980,1,1,0,0,0))
                entry.create_system=3;entry.compress_type=zipfile.ZIP_DEFLATED
                mode=0o755 if rel=='src/deskbridge' or rel.endswith('.sh') else 0o644
                entry.external_attr=(0o100000|mode)<<16
                archive.writestr(entry,data)
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
            assert all(archive.read(name+'/'+rel)==data for rel,data in files.items())
            assert not any('/engine/' in rel for rel in archive.namelist())
        sums.append(f'{digest(target.read_bytes())}  {target.name}')
    (release/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
    notes=f'''# DeskBridge v{version}

Reviewed prerelease: preserves saved settings, identity and trust; explicit
autostart; no automatic acceptance of discovered fingerprints. Corrected
process ownership, stop, crash recovery and reconnect handling.
Windows adds Setup.cmd, setup/restart/diagnose/fingerprint and desktop shortcuts.

Source commit: {commit}

Small ZIPs contain DeskBridge source, helpers, documentation and checksums.
Setup downloads Deskflow 1.27.0 directly from its official GitHub release,
verifies pinned size/SHA256 and installs it. Internet is required for the
first engine installation. Existing matching engines are reused.

Windows: extract into a permanent folder, open Setup.cmd, approve Windows UAC,
enter the other PC's IP, then use Start DeskBridge. PowerShell 7 is required.
Fedora 44 x86_64: extract, open a desktop terminal there, run bash Setup.sh.
Compare complete fingerprints on BOTH PCs and approve GNOME input sharing.

Tests and limits: docs/TESTING.md distinguishes isolated X11 loopback from
physical GNOME Wayland input. Fresh elevated MSI installation, secure desktop,
other OS releases and signing remain outside verified test coverage.
This is a prerelease, not a signed production installer.
'''
    (release/'RELEASE.md').write_text(notes)
    print('\n'.join(sums))
if __name__=='__main__':
    main()
