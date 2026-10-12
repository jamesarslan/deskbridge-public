# DeskBridge — share your keyboard and mouse between Windows and Linux

**One keyboard. One mouse. Two computers.** Move your pointer off the edge of
your Windows screen and keep working on your Fedora desktop, with text
clipboard sharing across both machines.

DeskBridge is a free, open-source software KVM setup and lifecycle helper for
[Deskflow](https://deskflow.org). It adds guided installation, saved pairing,
screen positioning, Start/Stop shortcuts and diagnostics around the existing
Deskflow engine. Both computers keep running their own apps on their own hardware.

[**Download Windows / Fedora**](https://github.com/jamesarslan/deskbridge-public/releases/tag/v0.2.0-rc2)
· [Setup guides](#install) · [Build story](#built-with-a-custom-ai-harness-and-local-qwen)
· [Verified coverage](docs/TESTING.md)

**Prerelease:** use [v0.2.0-rc2](https://github.com/jamesarslan/deskbridge-public/releases/tag/v0.2.0-rc2).
Earlier rc1 bundles are withdrawn following independent review.

## What you can do

- Share a Windows keyboard and mouse with a Fedora/Linux desktop over your network.
- Place Fedora to the left of Windows and cross between them at the screen edge.
- Copy and paste text between the two computers.
- Pair through TLS with explicitly compared certificate fingerprints.
- Start and stop sharing when you need it; login startup is optional.

The reviewed configuration is a Windows server and Fedora 44 GNOME Wayland
client. The user confirmed physical mouse and keyboard sharing after granting
GNOME input permission. The release also passed connection and isolated
crash-recovery/reconnect checks. See the [test matrix](docs/TESTING.md) for
exact coverage and remaining limitations.

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

## Built with a custom AI harness and local Qwen

DeskBridge grew from a practical question: could a custom AI coding setup help
make a Windows-and-Linux desk work smoothly with one keyboard and mouse?

Development used a custom [OMP harness](https://github.com/jamesarslan/omp-harness)
with a local Qwen 27B model served from an NVIDIA GeForce RTX 5090. The harness
connected model generation to development tools and work on the Linux machine.
The shared development preset also used OpenRouter Jev for typed decisions;
the final release received a separate Codex review and fixes.

We studied how existing keyboard and mouse sharing solutions work and adapted
open-source tools to fit a Windows-and-Fedora desk. That workflow produced
DeskBridge's setup, configuration, lifecycle and packaging helpers around the
existing Deskflow engine. Deskflow's contributors deserve credit for the
underlying input-sharing technology.

**Using DeskBridge needs no GPU, LLM or AI account.** AI helped build the
helpers; normal keyboard and mouse sharing runs through Deskflow.

## Questions before trying it

**Is this a remote desktop or headless server access app?**

The supported use is sharing input between two running desktop sessions.
DeskBridge does not stream a remote screen. A machine without a physical
monitor may require a configured graphical session or virtual display, which
is outside the verified product setup. Use SSH for terminal-only servers.

**Is it an open-source alternative to a hardware KVM or Synergy?**

It addresses the keyboard-and-mouse sharing part of a multi-computer desk,
using Deskflow. It does not switch video cables or promise Synergy feature
parity, remote video, native file transfer or other operating-system bundles.

**Is it ready to try?**

Yes, as a prerelease for the documented Windows/Fedora setup. Fresh elevated
Windows installation and login/reboot behavior still need broader testing.
GitHub CI could not start because of an account billing lock; local checks
and their limits are recorded in [TESTING.md](docs/TESTING.md).

## Contribute and license

[Contributing](CONTRIBUTING.md) Â· [Roadmap](ROADMAP.md) Â·
[Code of conduct](CODE_OF_CONDUCT.md) Â· [Architecture](ARCHITECTURE.md).

DeskBridge's original helpers are MIT licensed. MIT permits commercial reuse
by others; the project's own distribution is free. Deskflow has its own GPL
and component licenses. New DeskBridge ZIPs contain no third-party engine
binaries; see [NOTICE.md](NOTICE.md).

This is an independent, volunteer-maintained community project, not an
incorporated nonprofit or an official Symless/Deskflow product. Try the
prerelease, report reproducible issues, or help improve the setup guides.
