# Architecture

DeskBridge is a Python standard-library Linux CLI and a PowerShell 7.4+ Windows
server helper over unmodified Deskflow 1.27.0. There is no custom input driver.
One server owns the keyboard/mouse; its client occupies a configured edge.

## Configuration and lifecycle

Linux's default profile adopts ~/.config/Deskflow. Other profiles isolate
config, TLS and engine state beneath ~/.config/DeskBridge/<profile>.
Profile names are validated before path construction. Ports derived from
names are conveniences, not collision-free allocations: specify the SAME
--port at both ends for a non-default pairing.

The GUI is the default engine, preserving the application origin used for
GNOME permissions. Upstream permits only one GUI per desktop user. Concurrent
isolated tests use explicitly selected core engines with --new-instance.
Core launch includes the required server/client positional argument.

User units live under ~/.config/systemd/user/deskbridge-<profile>.service.
Start creates a unit without enabling login startup. Explicit autostart on
enables it for graphical-session.target. Process failures have a five-second
restart delay and a three-starts-per-minute limit. Deliberate stop stops the
unit first. The product targets exact environment markers/config homes of
the current user's processes; it does not terminate arbitrary Deskflow apps.

Windows uses the installed Program Files engine in desktop mode, settings
under ProgramData/Deskflow, and an optional interactive-user login task.
Setup creates Start/Stop desktop shortcuts pointing to the permanent folder.
The Windows helper supports the server role; other Windows roles use the
upstream app.

Setup merges managed INI keys while preserving GNOME restore tokens,
keyboard-layout preferences and other engine settings. Changed files get
backups; unchanged files are not rewritten. TLS identity/trust is retained
during setup, repair and product uninstall. Editing a running profile is
refused. Uninstall leaves the shared engine installed unless explicitly
requested otherwise on Windows.

## Pairing and permissions

TLS and fingerprint checks are required by managed configuration. Server and
client use trusted-clients and trusted-servers respectively. Native dialogs
require operator comparison. A network-probed fingerprint is unverified;
--yes never trusts it. An explicit --trust-fingerprint must come from the
other computer; a client additionally checks it against the observed server.

GNOME's input permission is granted by the human at its desktop. Persisting
a token does not prove the compositor still accepts it. X11 loopback tests
cannot validate this permission or physical input.

## Firewall and dashboard

Windows setup updates the managed TCP rule to the exact peer IP and engine
executable on Private/Domain profiles; broad upstream Deskflow inbound rules
are disabled. Other policies must still be reviewed by the administrator.
A Linux client needs no inbound rule. Linux server setup adds a peer allow
rich rule; this alone DOES NOT restrict an existing broad firewalld policy.
The CLI reports that limitation rather than declaring the machine restricted.

The optional dashboard binds to 127.0.0.1. A random per-launch token is sent in
an API header, with local Host/Origin checks. It strips the token from page
history, disables caching and referrers, renders diagnostic text safely and
serializes actions. It is a local control surface, not remote administration.

## Packaging

Reproducible ZIPs contain the product's source, launchers and documentation.
Platform setup retrieves the official upstream MSI/RPM with size/SHA256
verification. SOURCE-REVISION.txt and per-file checksums identify the build.
There is no DeskBridge RPM, signing system or updater in this prerelease.
