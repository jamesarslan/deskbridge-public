# DeskBridge — Testing matrix (what is claimed and how)

Honest per-claim verification record. Updated 2026-10-12 for v0.2.0-rc1.

## Physical (reference desk, 2026-10-12)

| Claim | Evidence |
|---|---|
| Mouse + keyboard cross the Windows-left edge onto the Fedora Wayland client | User confirmed at the desk after approving the GNOME remote-interaction prompt |
| Text clipboard transfer works both ways | Client log: successful clipboard transfer recorded |
| TLS 1.3 with mutual SHA-256 fingerprint pinning active | Client log + trust DBs on both sides; local cert `~/.config/Deskflow/tls/deskflow.pem`, fingerprint unchanged across the v0.1→v0.2 cutover |
| Windows inbound TCP 24800 scoped to the Fedora IP | Windows Firewall rule on Private/Domain profiles (user-applied; `DeskBridge.ps1` manages it) |
| v0.2 adopts an existing v0.1 install in place | `setup --yes` on the default profile keeps the existing cert, writes a `Deskflow.conf.bak.*` backup, stores state; `status`/`diagnose` green except "server reachable" while the server is stopped |

The live session is **not** re-run during product testing; v0.2 wizard output is
content-equivalent to the validated v0.1 config (same keys/values, verified by
`validate_conf` and the byte comparison above).

## Simulated (this machine, isolated profiles, live session untouched)

Run with `--profile testN` (isolated engine home, own unit name, own port) and a
before/after process diff proving the live session was not disturbed:

- Install / upgrade / uninstall lifecycle (`setup` → `uninstall`; engine RPM left
  in place, TLS dir preserved, `.uninstalled_<ts>` config backup left for restore).
- `start` / `stop` / `restart` repeated; stop order = supervisor unit first, then
  process kill (so a deliberate stop is not "restarted" by the supervisor).
- Reconnect/backoff: killing the engine mid-run → systemd-run
  `Restart=on-failure RestartSec=3` brings it back.
- Pairing persistence: trust DB survives restart; a second connect does not
  re-prompt (fingerprints pre-seeded via `trust add`).
- LAN discovery: loopback engine server on a test port is found by `discover`
  (passive TCP probe only — no protocol traffic, no pairing prompts on peers).
- Web UI (`serve`): status GET, start/stop POST with per-launch token; bad token
  → 401; bound to 127.0.0.1 only.
- Config validation: missing keys, TLS off, `externalConfigFile` + legacy
  `internalConfig` conflict, missing screen map — all rejected with actionable
  messages (tests/test_deskbridge.py).
- State adoption: an existing engine config with no app state is adopted for
  `status` / `diagnose` / web UI without writing state (tests/test_deskbridge.py).
- Wizard idempotence: re-running a completed setup reports no change.

## Unit

- `tests/test_deskbridge.py` — app core: version parsing, profile path isolation
  and port allocation, state round-trip, engine config write/validate (client +
  server), screen map content, state adoption, fingerprint canon/normalization,
  trust add/list/remove, firewall rich-rule string, SIDES symmetry.
- `tests/test_server_config.py`, `tests/test_server_ini.py`,
  `tests/test_client_config.py` — shipped config templates parse and carry the
  required keys.
- `tests/run-local-smoke.sh` — real engine: server + client on one box (Xwayland),
  TLS hello + layout exchange held for 10 s.

## CI

Workflows present (`ci.yml`: syntax + unit + config tests + manifest digest
reachability; `release.yml`: bundle build + ZIP-content validation on tag).
GitHub Actions on this account was **broken account-level** as of 2026-10-12
(every workflow fails at build with `startup_failure/BuildFailed`, 0 jobs, all
repos, since ~2026-10-04). Releases were therefore built locally
with the same `ci/` scripts and published via `gh release`; the rc1 assets were
re-downloaded through the API and sha256-verified against `SHA256SUMS`.

## Windows side (manual; enumerated remainder)

The v0.1 PowerShell helper was run physically on 2026-10-12 (install, engine MSI,
firewall scoping, pairing, stop; Desktop shortcuts created). v0.2 does not change
the Windows engine or its config layout; the helper is unchanged in v0.2.0-rc1.
Remainder that stays manual: any future Windows-side helper changes must be run
on the machine; there is no remote (SSH/RDP) access from the Fedora box to the
Windows PC currently, so this cannot be automated from here.

## Known limitations (labeled)

- Single-operator desk setup (one server, one client). Multi-client layouts: the
  engine supports them; the wizard is two-machine oriented.
- Cosmetic (upstream): on a Wayland **server** the cursor may not hide at the
  screen edge (compositor limitation).
- No macOS bundle. No cloud, accounts, telemetry, or update checks.
