# Windows server setup

Requires Windows 10/11 x64 and PowerShell 7.4+. Extract the win64 release ZIP
into a permanent folder, then open Setup.cmd. Windows will request elevation.
Enter the other PC's single IP address. Setup downloads and checksum-verifies
the official Deskflow installer if the pinned engine is not already installed.

The defaults are computer names windows/fedora, Fedora on the left, TCP 24800.
To customize, open Administrator PowerShell in the extracted folder:

```powershell
.\tools\DeskBridge.ps1 setup -ClientIP 192.168.1.20 -Name windows -PeerName fedora -Side left
```

Stop Deskflow before reconfiguring. Setup saves changed-file backups and
preserves existing certificate, trust and saved preferences. Subsequent
install actions preserve config; setup explicitly changes placement.

Use the Start DeskBridge / Stop DeskBridge desktop shortcuts. On first
connection compare complete fingerprints shown by both PCs and accept only
after matching them. Show the local value using:

```powershell
.\tools\DeskBridge.ps1 fingerprint
.\tools\DeskBridge.ps1 diagnose -Json
```

Setup manages one server rule scoped to the peer IP, engine executable and
Private/Domain profiles. It disables broad upstream Deskflow inbound rules.
Use a trusted private network and review additional firewall policy. A public
Windows network profile is intentionally not opened.

Autostart is opt-in, from Administrator PowerShell:

```powershell
.\tools\DeskBridge.ps1 autostart
.\tools\DeskBridge.ps1 autostart -DisableAutostart
```

The Deskflow service stays stopped/Manual; this product uses the desktop app.
MSI return 3010 is reported as a reboot requirement, never an automatic reboot.
Uninstall requires elevation:

```powershell
.\tools\DeskBridge.ps1 uninstall
# Only if you also want the shared engine removed:
.\tools\DeskBridge.ps1 uninstall -RemoveEngine
```

Product uninstall removes its rule/task and backs up its managed configuration.
TLS/trust remain. No elevated fresh-install or secure-desktop claim is made by
the rc2 test record; see TESTING.md.
