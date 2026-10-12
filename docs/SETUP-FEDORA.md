# Fedora setup

Fedora 44 x86_64, Python 3, a graphical desktop and its user systemd manager
are required for the supplied installer. Extract the ZIP, open a terminal
there, and run:

```bash
bash Setup.sh
```

The installer retrieves the official pinned RPM directly from Deskflow,
verifies size/SHA256, then asks sudo/dnf to install it. Existing matching
engines are reused. Choose client, enter the server address and match the
computer name configured at the server (default fedora).

For scripted setup:

```bash
python3 src/deskbridge setup --yes --role client --peer 192.168.1.10 --name fedora --autostart off
python3 src/deskbridge start
```

--yes accepts setup defaults, never a new fingerprint. Compare full
fingerprints in native Deskflow pairing dialogs on BOTH machines.
Approve GNOME's input-sharing permission at the physical desktop.
Mouse, keyboard and clipboard need a physical check afterward.

Stop before setup/repair. Existing certificate, trust, GNOME restore token,
keyboard-layout preferences and unrecognized settings are preserved.
Use start / stop / restart / status / diagnose / repair / fingerprint.
For JSON put --json before the action. Optional dashboard: serve.

Explicit login startup:

```bash
python3 src/deskbridge autostart on
python3 src/deskbridge autostart off
python3 src/deskbridge autostart status
```

A client needs no inbound firewall rule. The optional Linux server wizard
adds a peer accept rule; administrators must review broad firewalld policy.
This is not an assertion that every other rule is restricted.

Profiles use --profile NAME before the command. Non-default profiles isolate
configuration and keys; choose an explicit matching --port at both ends.
Deskflow only supports one GUI per user. Core mode is opt-in for isolated
X11 tests; changing engine origin may require a fresh GNOME grant.

If layouts differ, install matching GNOME input sources. Optional setup
--quiet-layouts remembers popup suppression without correcting layouts.
Uninstall removes the product profile/unit, keeps TLS/trust and backups,
and leaves the shared engine package installed.
