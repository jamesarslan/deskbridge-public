# Roadmap

## v0.2.0 (stable)

The v0.2.0-rc1 surface is the full v0.2 scope: single-file `src/deskbridge`
(setup wizard, profiles, status/diagnose/repair, supervision, opt-in
autostart, web UI), parameterized Windows helper, verified bundles. Stable
release follows the RC validation period with no new features.

## v0.3 candidates (no order promised)

- **macOS bundle** — the engine supports it; the product does not ship it
  yet (no validated macOS flow).
- **Multi-client wizard** — engine supports arbitrary screen maps; the
  wizard is two-machine oriented today.
- **Windows wizard parity** — the Windows side is a console script
  (install/start/stop/status/autostart/uninstall); discovery, diagnose and
  the web UI exist only on the CLI side.
- **Bundle signing** — detached signatures for the release zips
  (engine digests are already pinned and verified).
- **Engine pin automation** — detect new Deskflow releases and run the
  verification matrix before moving the pin.

## Non-goals

- Cloud, accounts, telemetry, update checks (engine
  `enableUpdateCheck=false` stays).
- Replacing or patching the engine GUI.
- Multi-machine fleets beyond what the engine's config format already
  supports.
