# DeskBridge — Architecture (v0.2.0)

DeskBridge makes two computers on a LAN share one keyboard and mouse (plus
clipboard) the way a hardware KVM switch does, with TLS-encrypted traffic and
a guided setup. It is a thin, tested product layer over the unmodified
[Deskflow](https://deskflow.org) engine (GPL-2.0 with OpenSSL exception),
pinned to **1.27.0**.

## Components

```
+-------------------+     +---------------------+
| Windows PC        |     | Fedora / Linux       |
| (server role)     |     | (client role)        |
+-------------------+     +---------------------+
 DeskBridge.ps1            deskbridge (Python 3, stdlib only)
  install/start/stop/status   console wizard + local web UI (serve)
  msiexec install             engine RPM (vendored, pinned 1.27.0)
  schtasks autostart          systemd user units (transient + persistent)
  scoped firewall rule        firewalld rich rule (server role only)
        |                            |
   Deskflow 1.27.0              Deskflow 1.27.0 (unmodified engine)
   deskflow.exe (GUI)            /usr/bin/deskflow (GUI, offscreen)
   %ProgramData%\Deskflow         ~/.config/Deskflow (default profile)
```

One machine is the **server** (owns the keyboard/mouse), the other is the
**client**. The product supports both roles on both OSes; the typical two-PC
desk is one of each.

## Engine facts (verified against v1.27.0 source, 2026-10-12)

- Protocols/CLI: `deskflow-core v1.27.0, protocol v1.8`. Core flags:
  `-h/--help`, `-v/--version`, `--new-instance`, `-s/--settings <file>`
  (override config file).
- TLS is **on by default** (`tlsEnabled` default true); the core loads one
  PEM (private key + self-signed cert, CN=Deskflow, RSA 2048) from
  `<config home>/Deskflow/tls/deskflow.pem`. Peer pinning:
  `security/checkPeerFingerprints`; accepted server fingerprints persist in
  `<config home>/Deskflow/tls/trusted-servers`.
- **Wayland (client)**: the engine detects Wayland (`platform::isWayland()`)
  and uses `EiComputer` — libei emulated input over an
  xdg-desktop-portal remote-desktop session (`XdpSession` with clipboard
  enabled). GNOME shows a trust prompt on first capture; the grant is
  remembered per portal origin (the app that requested it). On X11 the
  engine uses XTEST. The engine aborts (no display) unless
  `QT_QPA_PLATFORM=offscreen` is set in non-session contexts.
- **Cursor lock / return to host**: built in. Scroll Lock toggles the
  cursor locked to the current computer (`disableLockToComputer` default
  false); `lockCursorToScreen` hotkey action configurable.
- **Keyboard layouts**: the client compares the server's active layout with
  locally installed layouts (`KeyboardLayoutManager`). If a server layout is
  missing locally, the GUI shows a "Missing Keyboard Layouts" modal **with a
  "Don't show this again" checkbox** that sets
  `gui/ignoreMissingKeyboardLayouts` (persisted); the core logs a warning
  once per layout change. Key translation uses XKB keycodes
  (`KeyMap`), so modifier behavior is preserved when layouts match.
- **Modals the product can suppress**: the server's "new client accepted"
  prompt is skipped entirely when the server runs with
  `server/externalConfig=true` (our server config sets it), so a
  wizard-managed server never pops unexpected dialogs.
- Client reconnect: the engine retries the TCP connection internally
  (~3 s cadence observed) and re-requests the portal session after a
  "portal remote desktop session was closed" event. The product adds
  process-level supervision (`Restart=on-failure`).
- GUI binary on Linux is `/usr/bin/deskflow`; headless core is
  `/usr/bin/deskflow-core`. The **GUI binary is the product's default
  engine** on Fedora: the physically validated live session ran it, and the
  Wayland input trust grant belongs to that app origin — launching the
  different `deskflow-core` origin would force a re-grant. `deskflow-core`
  remains available as an opt-in (`engine=core`) for X11 boxes.
- Server config uses an external screen map (`serverConfig=` file,
  `server/externalConfig=true`), no legacy `internalConfig`.

## On-disk layout

### Fedora (user-scoped; nothing under /etc)

| Path | Owner | Content |
|---|---|---|
| `~/.config/DeskBridge/<profile>/deskbridge.json` | app | app state: role, computer name, peer, port, engine (`gui`/`core`), autostart, wizard completion |
| `~/.config/Deskflow/Deskflow.conf` (+ `tls/`) | engine | engine config for the **default** profile (standard path; existing state adopted in place) |
| `~/.config/DeskBridge/<profile>/xdg/Deskflow/...` | engine | engine config for **non-default** profiles, via `XDG_CONFIG_HOME` override (isolates config, TLS keys, trust DB) |
| `~/.local/state/deskbridge/<profile>.log` | engine | engine log file (configured via `[log]`) |
| `~/.config/systemd/user/deskbridge-<profile>.service` | app | persistent user unit, only when autostart enabled |
| transient `deskbridge-<profile>` unit | app | created by `start` via `systemd-run --user --collect` |
| bundle `src/deskbridge` (run from the unzipped bundle) | bundle | product CLI (user-scoped; nothing under /etc) |
| `/usr/bin/deskflow(-core)` | engine RPM | pinned 1.27.0 |

Profiles: `default` uses the standard engine paths (so a pre-existing
physically-validated setup is adopted with zero data movement); any other
name gets a fully isolated engine home, its own unit name and a distinct
port (24800 + offset) — used for testing and for running a client and a
server on the same box.

### Windows (machine-scoped, as validated)

| Path | Content |
|---|---|
| `%ProgramData%\DeskBridge\DeskBridge.json` | app state (same shape) |
| `%ProgramData%\Deskflow\Deskflow.conf` | engine config (server INI + `serverConfig=`) |
| `%ProgramData%\Deskflow\server.config` | screen map |
| `%ProgramData%\Deskflow\tls\deskflow.pem` | local TLS cert |
| `C:\Program Files\DeskFlow\deskflow.exe` | engine MSI (pinned 1.27.0) |
| Scheduled task `DeskBridge` (logon trigger) | autostart, off by default |
| Windows Firewall rule | TCP 24800 inbound **scoped to the peer IP** (server role only) |

## Product behavior

### Onboarding (`setup` wizard)

1. **Role** — server (keyboard/mouse machine) or client.
2. **Peer** — LAN discovery (TCP 24800 + engine protocol hello) with manual
   IP fallback; shows found computer names.
3. **Name** — this computer's name in the layout (default: hostname).
4. **Screen placement** — interactive ASCII map: the server machine places
   the client left/right/above/below its own screen (arrows); the client
   machine just confirms it points at the server. The server-side map is
   what the engine enforces; the client only needs name + address.
5. **Security** — TLS is always on; the wizard generates/keeps the local
   cert and prints both fingerprints so the operator can complete the pair
   (first connect shows the peer's fingerprint to trust; the product shows
   what to compare).
6. **Firewall** — server role on Fedora: adds a firewalld rich rule
   `source <peerIP> port 24800 tcp accept` (persists, scoped); server role
   on Windows: the matching scoped rule. Client role: no inbound rule
   needed (outbound only); the wizard verifies reachability instead.
7. **Keyboard layout** (client): reads local XKB layouts (GNOME
   `org.gnome.desktop.input-sources`) and warns, honestly, that any
   server-side layout not installed locally will not be translated; offers
   to pre-set `gui/ignoreMissingKeyboardLayouts` to suppress the engine
   modal.
8. **Success check** — starts the engine, waits, reports: process up, TCP
   connection state, fingerprint trust state, Wayland permission hint
   (client), and what the user should see (cursor leaving the server screen
   edge onto the client).

All wizard inputs are overridable as flags for automation; a completed
`deskbridge.json` makes re-runs idempotent ("no change") unless values
differ.

### Lifecycle

- `start` — engine is the GUI binary (Fedora default, `QT_QPA_PLATFORM=offscreen`)
  or `deskflow.exe` (Windows). Fedora: transient user unit via
  `systemd-run --user --unit=deskbridge-<profile> --collect` with
  `Restart=on-failure RestartSec=3` — the unit inherits the session's
  Wayland environment even when invoked over SSH (validated). Windows:
  `Start-Process deskflow.exe`.
- `stop` — validated order: supervisor/unit first (so a deliberate stop is
  not "restarted"), then process kill of `deskflow-core`/`deskflow`.
- `restart`, `status` (processes, unit, TCP state on the profile port,
  engine version, cert + fingerprint, trusted peers, engine-log tail,
  autostart state), `diagnose` (display protocol, config validation,
  reachability, firewall, layout, redacted log tail, actionable fixes).
- `autostart enable|disable|status` — Fedora: persistent user unit
  (`WantedBy=default.target`, `After=graphical-session.target`) + enable;
  Windows: scheduled task at logon. Off by default.
- Engine single-instance locking (both apps) makes double-start safe: a
  second start exits cleanly; the product reports "already running".

### Reliability

- Supervision as above; the engine's own ~3 s reconnect plus portal
  re-session covers network blips; the supervisor covers crashes.
- `repair` — regenerate the engine config from `deskbridge.json` (engine
  files are derived artifacts), re-verify engine presence/version,
  re-apply the firewall rule (server), refresh autostart. Settings,
  certificate, and trust DB are never overwritten; upgrades that replace
  the app leave them in place (app code under /usr, state under the home
  dir, engine under the package manager — no overlap).
- Upgrade-safety: the app writes the engine config only from the wizard or
  `repair`; the engine itself only updates its own keys (QSettings preserves
  unknown keys), so a Deskflow update never clobbers the screen map or
  `remoteHost`.

### Local web UI (`serve`, Fedora bonus)

Stdlib-only HTTP server bound to 127.0.0.1 (default :8472), a per-launch
token printed in the terminal (URL + token), serving: live status, the
ASCII screen map, start/stop buttons, fingerprints, pairing guide. It calls
the same command core as the CLI (`--json`), so it is fully covered by the
same test paths.

## Packaging

- **Fedora ZIP bundle**: `src/deskbridge` (single-file CLI, executable), the
  engine RPM (official 1.27.0, unmodified; installed by the operator with
  `dnf`), `config/` templates, docs. The engine stays a separate third-party
  GPL component: distributed unmodified and credited, never rebuilt or merged
  into a product package.
- **Windows ZIP bundle**: `tools/DeskBridge.ps1`, the engine MSI (official
  1.27.0), `config/` templates, docs. `ci/package_bundles.py` validates actual
  ZIP contents after the build (a v0.1 zip once shipped without its script —
  this class of bug stays caught).
- `ci/manifest.json` pins engine URLs + SHA-256.

## Testing (what is claimed and how)

`docs/TESTING.md` records the matrix honestly, per claim:

- **Physical** (reference desk, 2026-10-12, v0.1 stack): mouse/keyboard/
  clipboard across Windows 11 server ↔ Fedora 44 Wayland client over TLS
  with fingerprint pinning; reconnect after network drop; Wayland trust
  prompt once; clean stop. (v0.2 wizard-generated config is
  content-equivalent; the live session is not re-run during product
  testing.)
- **Simulated** (this machine, isolated profiles, no live-session
  interference): install/upgrade/uninstall, start/stop/restart ×N,
  reconnect/backoff (kill engine → supervisor restart), pairing
  persistence (trust DB survives restart; second connect does not re-prompt),
  discovery (loopback server on a test port), web UI, config validation,
  firewall rule application, wizard idempotence, before/after process diff
  proving the live session untouched.
- **CI**: workflows present; availability recorded as of release day.
- **Windows**: enumerated remainder (msiexec install, pairing prompt, scoped
  firewall rule, autostart task, uninstall) — the v0.1 script performed these
  physically on 2026-10-12; v0.2.0-rc1 ships the same script with the firewall
  scope parameterized (`-ClientIP`) and no other engine/config changes.

## Non-goals (v0.2)

- macOS support (engine supports it; product does not ship it yet).
- Multi-client layouts beyond the two-machine desk (engine supports it;
  wizard is two-machine oriented, config format unchanged).
- Replacing the engine GUI. The product is a wrapper; the engine GUI
  remains available and reads the same config (external config mode).
- No cloud, no accounts, no telemetry, no update check (engine
  `enableUpdateCheck=false`).

## License

Product: MIT. Engine: Deskflow 1.27.0, GPL-2.0-only with
LicenseRef-OpenSSL-Exception, unmodified, credited in README and
`deskbridge --version`. The two are separate components; the product does
not link against engine code.
