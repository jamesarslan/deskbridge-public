# DeskBridge

Deskflow-based KVM bridge for a two-machine desk:

```
 +--------+  +----------+
 | fedora |  | windows  |   <- move mouse LEFT across the windows left edge
 +--------+  +----------+
 (client)            (server: keyboard + mouse attached here)
```

- **Windows = Deskflow server** (holds the physical keyboard/mouse).
- **Fedora 44 (GNOME Wayland) = Deskflow client**.
- Shared mouse, keyboard and **text clipboard** across TCP **24800**, **TLS on**
  (Deskflow default) with first-run **fingerprint pairing**.
- Login-time autostart is **optional and off by default** on both sides.
- Guided `setup` wizard (role, LAN discovery, screen placement, pairing),
  `status` / `diagnose` / `repair`, supervisor restart on crash, and a local
  web UI on Fedora (`serve`). See `ARCHITECTURE.md`.
- Engine: **unmodified upstream Deskflow v1.27.0** (pinned sha256 in
  `ci/manifest.json`). Wrapper layer (this repo) is MIT; engine stays GPL-2.0
  (see `NOTICE.md`, `licenses/`).

## Bundles (GitHub releases)

| File | Contents |
|---|---|
| `deskbridge-win64-<ver>.zip` | `engine/deskflow-1.27.0-win-x64.msi`, `tools/DeskBridge.ps1`, `config/server.config`, `docs/SETUP-WINDOWS.md` |
| `deskbridge-fedora44-<ver>.zip` | `engine/deskflow-1.27.0-fedora-44-x86_64.rpm`, `src/deskbridge`, `config/client.conf`, `docs/SETUP-FEDORA.md` |

Each zip ships its own `SHA256SUMS.engine`; the release page ships `SHA256SUMS`
for the zips.

## Quick start

Windows (elevated PowerShell, in unzipped folder):
```powershell
.\tools\DeskBridge.ps1 install
.\tools\DeskBridge.ps1 start
```
Fedora (as your desktop user, in unzipped folder):
```bash
sudo dnf install -y engine/*.rpm
./src/deskbridge setup --yes --role client --peer <windows-ip> --name fedora
./src/deskbridge start
```
First connection: confirm the TLS fingerprint dialog on **both** machines
(compare `src/deskbridge fingerprint` with `.\tools\DeskBridge.ps1 fingerprint`);
on Fedora approve the GNOME input-permission prompt once.
Details: `docs/SETUP-WINDOWS.md`, `docs/SETUP-FEDORA.md`, `docs/WAYLAND.md`.

Helpers on both sides: `status`, `stop`, `start`, `restart`, `autostart`,
`uninstall`; Fedora additionally `setup`, `diagnose`, `repair`, `discover`,
`fingerprint`, `trust`, `layout`, `serve` (web UI), `version`.

## Repo layout

```
src/      deskbridge (Fedora CLI, single file, Python 3 stdlib only)
config/   server.config (Deskflow screen map), client.conf (client INI), server.conf (INI template)
tools/    DeskBridge.ps1 (Windows console wizard)
ci/       manifest.json (pinned artifacts), download_manifest.py, package_bundles.py
tests/     config structure tests, app-core regression tests, manifest fetch, loopback engine smoke
docs/     setup guides, Wayland evidence, testing matrix
.github/  ci.yml (syntax/tests/manifest checks), release.yml (bundles on tag v*)
```

## Build

```bash
tests/fetch-engine.sh                 # download pinned engine into engine/
python3 ci/download_manifest.py stage # CI: verify digests
python3 ci/package_bundles.py stage   # CI: build bundles + SHA256SUMS + RELEASE.md
tests/test_deskbridge.py              # app-core regression tests (no root/display needed)
tests/run-local-smoke.sh              # loopback engine test (needs an X display)
```

Tagging `vX.Y.Z` on `main` builds and publishes the release automatically.

## Status & limitations

See `docs/TESTING.md` (verification matrix) and `RELEASE.md` per release.
