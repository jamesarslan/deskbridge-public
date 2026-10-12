# DeskBridge

Free, volunteer-maintained keyboard, mouse and text clipboard sharing for a
Windows server and Fedora desktop. DeskBridge guides and supervises the
unmodified [Deskflow](https://deskflow.org) engine. It is a community project,
not an incorporated charity or an official Symless/Deskflow product.

**Prerelease:** use [v0.2.0-rc2](https://github.com/jamesarslan/deskbridge-public/releases/tag/v0.2.0-rc2).
Earlier rc1 bundles are withdrawn following independent review.

## Install

Download the ZIP for your platform and extract it into a permanent folder.
The small ZIP contains DeskBridge source and helpers. First setup downloads
Deskflow 1.27.0 directly from its official release and checks its pinned
size and SHA256. Internet access is needed for that first installation.

- **Windows 10/11 x64, server:** install PowerShell 7.4+, open **Setup.cmd**,
  approve Windows UAC, and enter the Fedora PC's IP address. Default computer
  names are `windows` and `fedora`, with Fedora on the left. Use the created
  **Start DeskBridge** / **Stop DeskBridge** desktop shortcuts.
- **Fedora 44 x86_64, client:** open a terminal in the extracted folder and run
  `bash Setup.sh`. Choose client, enter the Windows server address, and use
  the same client computer name as the server's layout.
- Compare the **complete SHA256 fingerprints on both computers** when
  Deskflow asks to pair. On GNOME approve its input-sharing permission.
  `--yes` never accepts a new peer automatically.
- Move the Windows cursor left onto Fedora, type, and test clipboard both
  ways. A running process or TCP connection alone is not this physical test.

[Windows setup](docs/SETUP-WINDOWS.md) Â· [Fedora setup](docs/SETUP-FEDORA.md) Â·
[Verification and limits](docs/TESTING.md) Â· [Security](SECURITY.md).

## Daily use

Windows: desktop shortcuts, or `pwsh -File tools/DeskBridge.ps1 start` /
`stop`. Other actions: `restart`, `status`, `diagnose`, `fingerprint`.

Fedora: `python3 src/deskbridge start`, `stop`, `restart`, `status`,
`diagnose`, `fingerprint`. Add `--json` **before** the action for JSON.
Optional local dashboard: `python3 src/deskbridge serve`; open its printed
127.0.0.1 URL. The dashboard controls an already configured profile.

Autostart is off on a fresh setup. Explicitly opt in using the commands in
the platform guide. Setup preserves existing autostart choices and pairing.
Stop the engine before changing settings. Keep the extracted folder because
shortcuts refer to its helper.

Missing-layout warnings indicate a layout difference. Install matching
layouts first; optional `--quiet-layouts` (Fedora) or `-QuietLayouts`
(Windows setup) remembers popup suppression but does not fix translation.

## Contribute and license

[Contributing](CONTRIBUTING.md) Â· [Roadmap](ROADMAP.md) Â·
[Code of conduct](CODE_OF_CONDUCT.md) Â· [Architecture](ARCHITECTURE.md).

DeskBridge's original helpers are MIT licensed. MIT permits commercial reuse
by others; the project's own distribution is free. Deskflow has its own GPL
and component licenses. New DeskBridge ZIPs contain no third-party engine
binaries; see [NOTICE.md](NOTICE.md).
