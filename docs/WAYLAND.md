# GNOME Wayland

Deskflow 1.27.0 uses libei and xdg-desktop-portal for GNOME input sharing.
The human approves remote interaction on the Fedora desktop. Certificate
pairing and GNOME input permission are separate decisions.

The default GUI origin matches the previously validated desktop setup.
DeskBridge preserves client/server xdpRestoreToken keys on configuration
changes. The compositor can revoke permissions or invalidate a token;
stored tokens alone do not prove permission is active.

A real physical Windows-server/Fedora-GNOME-client session worked before
this review after human approval. The independent automated lifecycle tests
use a separate Xvfb X11 desktop, not GNOME Wayland. They cannot demonstrate
physical cursor behavior, permission persistence across login, secure
desktop, or every keyboard layout.

Install the same layouts on both computers to avoid missing-layout dialogs.
The upstream Don't show again choice is preserved. Optional quiet-layouts
only suppresses that dialog; it does not improve translation.

If input stops: check server listener, full fingerprints, native Deskflow
logs and the GNOME permission prompt. Stop/start only the affected profile;
do not reset certificates or revoke unrelated permissions as a first step.
