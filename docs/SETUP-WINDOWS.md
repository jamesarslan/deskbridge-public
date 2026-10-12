# DeskBridge — Windows setup (SERVER)

This PC holds the keyboard and mouse, so it runs the Deskflow **server**.
The Fedora PC connects as a client and appears to the **LEFT** of the Windows screen.

## One-time install (elevated PowerShell)

1. Unzip the bundle: `deskbridge-win64-<ver>.zip`.
2. Right-click **PowerShell** → **Run as administrator**, then:
   ```powershell
   cd C:\Path\To\UnzippedFolder
   .\tools\DeskBridge.ps1 install
   ```
   This:
   - verifies the engine MSI sha256 against the pinned digest,
   - installs Deskflow silently (`C:\Program Files\Deskflow`),
   - writes `C:\ProgramData\Deskflow\Deskflow.conf` + `server.config` (screen map),
   - adds the Windows Firewall inbound rule **DeskBridge Deskflow Server (TCP 24800)**,
     scoped to the client IP the script asks for (Private + Domain profiles). If
     Windows shows a firewall prompt on first start, allow it — it should match.
3. The helper generates a self-signed TLS certificate at
   `C:\ProgramData\Deskflow\tls\deskflow.pem` if one does not exist, using
   Git for Windows' OpenSSL. It grants the installing user access to this
   settings directory. Existing certificates are preserved. Desktop mode is
   selected; the upstream service is stopped and set to Manual so sharing
   starts only when you start the app.
4. Start the server (normal user, not elevated):
   ```powershell
   .\tools\DeskBridge.ps1 start
   ```
   A Deskflow tray icon appears. The core starts automatically (`startCoreWithGui=true`)
   and listens on **TCP 24800** with TLS.

## First connection (pairing)

1. On the **Fedora** PC start the client (see SETUP-FEDORA.md).
2. Windows shows a dialog with the **Fedora machine's TLS certificate fingerprint** →
   compare it with the output of `src/deskbridge status` on Fedora (it prints
   "the Windows server shows this in its trust dialog") → confirm.
3. Fedora shows the **Windows machine's fingerprint** → confirm.
4. Fingerprints are stored after confirmation (trusted-clients / trusted-servers);
   later connections pair automatically.
   To compare across machines: `DeskBridge.ps1 status` on Windows prints the local
   certificate fingerprint when it exists.

## Verify

```powershell
.\tools\DeskBridge.ps1 status
```
Expect: `deskflow`/`deskflow-core` processes, TCP 24800 **Established** to the
Fedora PC, autostart state, local TLS fingerprint.

## Daily use

- Mouse to the **left edge** of the Windows screen → cursor appears on Fedora.
- Right edge of the Fedora screen → back to Windows. Keyboard/clipboard follow.
- **Scroll Lock** toggles cursor lock to the local screen (built-in Deskflow feature).
- Start: `.\tools\DeskBridge.ps1 start` — or once trusted:
  `.\tools\DeskBridge.ps1 autostart` (logon scheduled task; **off by default**).
- Stop: `.\tools\DeskBridge.ps1 stop`. Uninstall: `.\tools\DeskBridge.ps1 uninstall [-RemoveEngine]`.

## Notes

- The server must run in the **active console session** (input hooks). If you're
  locked out or on a different RDP session, the client will disconnect.
- Keep the Windows PC on the same LAN (Wi-Fi or Ethernet). Port 24800/TCP must
  reach the Fedora PC (the helper's firewall rule scopes it to the client IP on
  the default Private/Domain profiles; keep your trusted home network Private).
- Version pin: Deskflow **v1.27.0** (both sides, from the same upstream release).
