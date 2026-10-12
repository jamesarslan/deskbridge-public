# Wayland support — evidence (checked 2026-10-12 against official Deskflow sources)

## Official statements (desktopFlow/deskflow, tag v1.27.0 era master)

- `README.md`: *"TLS encryption is enabled by default. Wayland is supported.
  Clipboard sharing is supported."*
- `README.md` (Wayland section): Wayland support added in **v1.1.17**; on Linux
  client/server on Wayland it uses the **libei** + **libportal** stack;
  requirements: libei ≥ 1.3, libportal ≥ 0.8, Qt 6.7+ for the GUI.
- `wiki/Known-Issues` + discussion **#7499** (Wayland support status matrix):
  - **Server** role on Wayland needs the portal **InputCapture** extension —
    GNOME ≥ 46.
  - **Client** role on Wayland needs the portal **RemoteDesktop** extension.
  - **GNOME 50+ provides V2** of the remote-desktop/input portal, which adds
    **clipboard access** for the client.
  - Known cosmetic bug: on a Wayland *server* the cursor may not hide when it
    leaves the screen edge (compositor limitation; does not affect switching).

## This machine (Fedora 44 Workstation, GNOME session on Wayland)

| Requirement        | Needed      | Installed            | OK |
|--------------------|-------------|----------------------|----|
| libei              | ≥ 1.3       | 1.6.0                | ✓  |
| xdg-desktop-portal | present     | 1.22.1               | ✓  |
| portal (GNOME)      | ≥ 46/50     | 50.0 (V2, clipboard)  | ✓  |
| Qt 6 (GUI)          | 6.7+        | 6.10.x (Qt6Core 6.10) | ✓  |
| Engine build        | fedora-44   | upstream v1.27.0 RPM | ✓  |

Conclusion: **client mode works on GNOME Wayland** (RemoteDesktop portal, V2 with
clipboard). Server mode on this same box would also work (InputCapture portal,
GNOME 50 ≥ 46) — but the server runs on Windows anyway.

## First-run prompts (client, GNOME)

1. Portal permission: "Allow Deskflow to access your session input" — approve.
2. TLS fingerprint dialog — confirm the Windows server certificate (see SETUP docs).

## Residual risk

Verified by docs + installed dependency versions; NOT by a live second machine
(Windows box has no shell access). The loopback engine smoke test
(`tests/run-local-smoke.sh`) additionally proves the v1.27.0 engine binary itself:
config parsing, TCP 24800 listen, TLS handshake, client acceptance.
