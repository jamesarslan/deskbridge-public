# Contributing

DeskBridge is a free community project around unmodified Deskflow.
Original product code is MIT licensed. Contributions should remain small,
testable and considerate of existing working desktops.

- Keep the Linux app standard-library-only (Python 3.10+) and Windows
  helper PowerShell 7.4+ compatible.
- Preserve engine settings, permission tokens, certificates and trust
  during upgrades. Never silently accept a network-discovered identity.
- Match only owned processes. Never disrupt an unrelated desktop, change
  unrelated firewall policy or automatically enable login startup.
- Never commit private addresses, credentials, keys, logs or live state.
- Keep docs and the verification matrix accurate. Separate mocked tests,
  isolated real-engine tests, physical input and CI results.
- Download the pinned official engine directly during setup; do not
  redistribute third-party binaries without addressing source/licenses.

## Tests

python3 tests/test_deskbridge.py
python3 tests/test_regressions.py
python3 tests/test_client_config.py
python3 tests/test_server_config.py
python3 tests/test_server_ini.py

On Windows: pwsh -NoProfile -File tests/test_windows.ps1
On Fedora with installed Deskflow, Xvfb and user systemd:
python3 tests/integration-fedora.py

The integration test uses an isolated X11 display and owned test profiles.
It cannot validate GNOME Wayland or physical keyboard/mouse behavior.

## Release

Commit the reviewed tree, then run python3 ci/package_bundles.py stage.
Build ZIPs identify their source commit and contain per-file SHA256 checks.
Tag vX.Y.Z[-rcN], publish with the correct prerelease flag, re-download
assets and verify their checksums and contents. Never call unavailable
or failed CI passing. Keep prereleases immutable; issue a new version for
corrections. No release signing is implemented yet.
