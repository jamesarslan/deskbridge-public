# Security

DeskBridge configures unmodified Deskflow on a trusted LAN. Managed setup
requires TLS and peer fingerprint checks; native engine controls outside
DeskBridge can still change settings. Do not disable either check.

Compare complete SHA256 fingerprints on BOTH machines before pairing.
Discovery observes an unverified certificate and never authorizes it.
--yes never accepts a new peer. Explicit trust commands are an operator
decision and must use a value obtained from the other computer.

Windows setup scopes its own inbound rule to one peer IP and the engine on
Private/Domain profiles, and disables broad upstream Deskflow inbound rules.
Additional rules or administrative policy can still affect access.
Linux clients need no inbound rule. A Linux server peer accept rule does
not restrict existing broad firewalld policy; review that policy yourself.

Private keys and trust stores stay local. Setup/repair/uninstall preserve
identity and pairing. GNOME permission is separate from certificate trust
and can be revoked by the compositor. Input and clipboard are exposed to
the paired computer by design; use only computers you trust.

The dashboard is local-only with per-launch header authentication,
Host/Origin checks, no caching/referrers and serialized actions. It is not
a remote administration endpoint. The original product source is available;
prerelease ZIPs are not signed.

## Report privately

Use this repository's Security tab to report vulnerabilities privately.
Do not put credentials, keys, complete private logs or personal configuration
into public issues. status/diagnose may include LAN addresses, paths and
certificate fingerprints: inspect and remove personal details before sharing.
Describe affected versions, OS/roles and reproduction steps.
Engine-specific reports belong with https://github.com/deskflow/deskflow.

Older rc1 ZIPs are withdrawn after review. Use the latest reviewed prerelease.
