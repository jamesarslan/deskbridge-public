# Verification record — v0.2.0-rc2

Independent review, 2026-10-12. This matrix replaces unsupported rc1 claims.

| Scope | Result and evidence |
|---|---|
| Python logic/files | 17 original app tests and 16 review regressions pass on Fedora. Three template suites also pass. Regressions cover path traversal, managed-key merging, valid legacy arrays, server definitions/vertical edges, trust stores, disabled pin rejection, bounded scans, IP parsing, ownership isolation, core arguments, autostart-off and no silent trust, JSON failure status, repair and uninstall preservation. |
| Actual TLS and HTTP | Review regressions perform a real local TLS handshake and compare its DER SHA256. HTTP tests verify auth, rejected Origin, cache headers, one HTML response and refusal to start an unconfigured profile. On Windows the TLS test skips when OpenSSL is absent; it passes on Fedora. |
| Windows native configuration/crypto | PowerShell parsing plus test_windows.ps1 pass on this Windows host: saved preferences/permission keys, computer definitions, vertical edges, unchanged reruns, real .NET RSA/PEM generation, stable identity and private-key ACLs. Temporary test directories are removed. |
| Real Linux lifecycle | integration-fedora.py passes with the installed Deskflow core, user systemd and a separate Xvfb X11 display: generated server/client settings, mutual pinning, protocol connection, idempotent start, repeated stop/restart, opt-in autostart enable/disable, server SIGKILL recovery, client reconnect, setup/repair preservation and repeated uninstall. Unique test units/profiles are cleaned up. |
| Actual two-machine connection | The reviewed Windows helper started the existing installed server; the reviewed Linux GUI client detected Wayland, connected to a secure socket and reached ESTABLISHED with the trusted peer. Config validated and autostart remained off. Both apps were stopped afterward to restore their previous state. |
| Physical input | User previously confirmed mouse/keyboard across the left edge after approving GNOME input sharing, with clipboard and TLS recorded. No new physical mouse, typing or clipboard action was performed during rc2 review. A TCP/TLS connection does not replace that test. |
| GNOME permission | Existing nonempty compositor restore token was observed in Deskflow.state without exposing it. The default GUI origin and state location are preserved. Login/reboot persistence and renewed physical input were not independently verified. |
| Keyboard layouts | Added the missing Turkish GNOME input source while preserving existing sources. Deskflow's Xwayland metadata still reported Turkish missing, so its persisted popup-suppression preference was enabled. No claim of complete Turkish/Swedish/English translation coverage. |
| Packaging | Product-only reproducible ZIPs, required helper/launcher files, per-file SHA256 and source revision are verified. Installer downloads use official pinned size/SHA256. Release assets must be re-downloaded and checksum-verified after publication. |
| CI | GitHub refused to start the earlier public CI job: its check annotation explicitly says the account is locked due to a billing issue. No steps ran. Local checks are not a passing CI run. |

## Deliberate limits

Fresh elevated Windows MSI install/update/uninstall was not run during review
(the existing engine was already installed). The real Windows checks cover
helper runtime against that installation and temporary configuration/crypto.
A clean Windows test machine and interactive UAC are required to expand that
coverage. Linux login/reboot startup is not tested by toggling unit enablement.

There is no secure-desktop, other-OS, all-layout, latency or signed-installer
claim. The supplied automatic Linux engine installer targets Fedora 44 x86_64.
The optional Linux server accept rule does not prove a broad firewall policy
restricts access. Concurrent GUI profiles are unsupported by upstream.

## Repeat the checks

python3 tests/test_deskbridge.py
python3 tests/test_regressions.py
python3 tests/test_client_config.py
python3 tests/test_server_config.py
python3 tests/test_server_ini.py

Windows: pwsh -NoProfile -File tests/test_windows.ps1

Fedora with Deskflow, OpenSSL, Xvfb and user systemd:
python3 tests/integration-fedora.py

Virtual-display tests do not use the physical desktop. A real desk check
requires a human: move left, type, copy/paste both ways, and return right.
