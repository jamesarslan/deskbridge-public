# DeskBridge — Fedora setup (CLIENT)

This machine (GNOME on **Wayland**) runs the Deskflow **client**. The Windows PC
is the server (it holds the keyboard/mouse). v0.2+ uses the single-file `src/deskbridge` CLI.

## One-time install (as your desktop user)

1. Unzip the bundle: `deskbridge-fedora44-<ver>.zip`.
2. In the unzipped folder:
   ```bash
   sudo dnf install -y engine/deskflow-1.27.0-fedora-44-x86_64.rpm
   chmod +x src/deskbridge
   ./src/deskbridge setup --yes --role client --peer <windows-ip> --name fedora
   ```
   The setup command (non-interactive variant of the wizard) verifies the engine,
   keeps or generates the local TLS certificate `~/.config/Deskflow/tls/deskflow.pem`,
   writes the engine config (backing up any existing one to `Deskflow.conf.bak.<ts>`),
   stores app state in `~/.config/DeskBridge/default/deskbridge.json`, and prints the
   fingerprint to compare on the Windows machine.
   An existing engine config (e.g. from a v0.1 install) is **adopted in place**:
   certificate and trust database are never regenerated.
   - Engine RPM sha256 is pinned in `SHA256SUMS.engine` / `ci/manifest.json`:
     `71cdeec92e4351fced4cf907db5e936959a0923b2855284ca52d8cf1088205a9`.
   - Without `--yes` the same steps run as an interactive wizard (LAN discovery,
     screen placement, layout check): `./src/deskbridge setup`.

## First start (pairing)

```bash
./src/deskbridge start
```
The Deskflow app opens (system tray) and its core connects to the Windows server.
Then, in order:
1. **GNOME input-permission prompt**: "Deskflow" asks to access your session input
   (Wayland RemoteDesktop portal). **Approve** — the Wayland equivalent of X11
   input injection. GNOME remembers the decision.
2. **TLS fingerprint dialog**: the client verifies the **Windows server's**
   certificate fingerprint. Compare with `./src/deskbridge fingerprint` (this side)
   and `.\tools\DeskBridge.ps1 fingerprint` (Windows) → confirm. It is stored in
   `~/.config/Deskflow/tls/trusted-servers`; later connections pair automatically.
3. The Windows side confirms Fedora's fingerprint in its own dialog
   (see SETUP-WINDOWS.md).

Trust database helpers: `./src/deskbridge trust list|add <fp>|remove <fp>`.

## Verify

```bash
./src/deskbridge status       # processes, unit, TCP 24800, engine, cert, autostart
./src/deskbridge diagnose      # config/TLS/firewall/reachability checks with fixes
./src/deskbridge serve         # optional local web UI on 127.0.0.1:8472 (token printed)
```

## Daily use

- Mouse to the **right edge** of the Fedora screen → cursor moves to Windows.
  Left edge of Windows → back to Fedora. Keyboard/clipboard follow
  (clipboardSharing on). **Scroll Lock** toggles cursor lock to the local screen.
- Start: `./src/deskbridge start`. Stop: `./src/deskbridge stop`.
- `./src/deskbridge autostart enable` — persistent systemd **user** unit
  (starts with your GNOME session; **off by default**). `autostart status|disable`.
- `./src/deskbridge repair` — regenerate the engine config from state (cert +
  trust DB are never touched).
- Uninstall: `./src/deskbridge uninstall` (keeps TLS certs + config backup;
  `--remove-engine` also removes the engine RPM).

## Profiles

`default` uses the standard engine paths (`~/.config/Deskflow`). Other profile
names (`--profile name`) get a fully isolated engine home, their own systemd unit
and a distinct port — for testing or running both roles on one box.

## Wayland notes

- Deskflow supports Wayland (since v1.17) via `libei` + `xdg-desktop-portal`;
  this machine has libei 1.6.0 and xdg-desktop-portal-gnome 50.0 (V2, includes
  clipboard). See WAYLAND.md for the doc evidence and known cosmetic bug.
- The product launches the **GUI** binary (`/usr/bin/deskflow`) by default on
  purpose: the portal input-trust grant belongs to that app origin. `deskflow-core`
  is available as an opt-in (`engine=core` in state) for X11 boxes.
- If the mouse works but **clipboard** doesn't, check that the GNOME input
  permission was granted for "Deskflow" (portal permission UI) and restart the client.
