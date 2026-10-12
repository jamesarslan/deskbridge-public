# Security

## Model

DeskBridge bridges one keyboard/mouse (+ text clipboard) between two machines
on a trusted LAN. The security properties come from the Deskflow engine,
which this project configures but does not modify:

- **TLS is always on** (`security/tlsEnabled=true` is enforced by
  `src/deskbridge` validation; there is no plaintext mode in the product).
- **Peer pinning**: `security/checkPeerFingerprints=true`; the first
  connection shows the peer's SHA-256 certificate fingerprint in a dialog on
  both sides, and accepted fingerprints persist in local trust databases
  (`~/.config/Deskflow/tls/trusted-servers` / `trusted-clients`).
- **Firewall scoping**: the server-side inbound rule for TCP 24800 is scoped
  to the client IP (`-ClientIP` on Windows, rich rule on firewalld) instead of
  the broad rule the upstream MSI installs.

## Known limits (read before reporting)

- The trust model is **operator pairing on a trusted LAN**. Anyone who can
  complete pairing with you is a trusted peer by design; this product does
  not add authentication beyond the engine's.
- Traffic is encrypted **between the two machines only**. Nothing prevents
  on-path observation of connection metadata on the LAN.
- Certificates are **self-signed** (CN=Deskflow, RSA 2048), generated
  locally; pinning, not a CA chain, is the protection.
- The Windows helper disables the upstream MSI's broad inbound rules and
  creates the scoped rule; if you remove the rule manually, port 24800
  behavior returns to Windows defaults.
- Engine vulnerabilities: track <https://github.com/deskflow/deskflow/issues>.
  This project pins Deskflow 1.27.0 and will move the pin on release.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's private vulnerability
reporting for this repository (Security tab → "Report a vulnerability"), or
email the repository owner via the GitHub profile contact route with the
details and, if you have one, a suggested fix.

Reports include: affected versions, both machine OSes and roles
(server/client), the exact `status` / `diagnose` output (it redacts secrets),
and steps to reproduce.
