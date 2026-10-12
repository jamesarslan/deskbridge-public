# DeskBridge - Windows server helper for Deskflow.
# This PC is the Deskflow SERVER: it holds the keyboard/mouse.
# The other PC (e.g. Fedora) connects as a client; screen placement is in server.config.
#
# Usage (PowerShell):
#   .\DeskBridge.ps1 install          [elevation required] verify MSI, install engine,
#                                     write config, add scoped firewall rule
#   .\DeskBridge.ps1 start             start the desktop app (tray + core)
#   .\DeskBridge.ps1 stop               stop all deskflow processes
#   .\DeskBridge.ps1 status             processes, TCP 24800 state, autostart
#   .\DeskBridge.ps1 autostart [-DisableAutostart]  enable/disable logon autostart
#   .\DeskBridge.ps1 uninstall [-RemoveEngine]      [elevation for -RemoveEngine]
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet('install', 'start', 'stop', 'status', 'autostart', 'uninstall', 'help')]
  [string]$Action = 'help',
  [string]$ClientIP = '',
  [switch]$DisableAutostart,
  [switch]$RemoveEngine
)

$ErrorActionPreference = 'Stop'
$ServerName = 'windows'
$Port = 24800
$MsiFile = 'deskflow-1.27.0-win-x64.msi'
$MsiSha256 = '0ca5668c4731f5477d0b189bdb11196a2ca51281985d9d8c0757bf7f3b782d64'
$FirewallRuleName = 'DeskBridge Deskflow Server (TCP 24800)'
$TaskName = 'DeskBridge Deskflow Server'

function Get-LogPrefix { '[deskbridge]' }
function Write-Ok([string]$m)   { Write-Host "$(Get-LogPrefix) $m" -ForegroundColor Green }
function Write-Warn2([string]$m) { Write-Host "$(Get-LogPrefix) $m" -ForegroundColor Yellow }

function Test-Admin {
  ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-DeskDir {
  foreach ($d in 'C:\Program Files\Deskflow', 'C:\Program Files (x86)\Deskflow') {
    if (Test-Path $d) { return $d }
  }
  throw "Deskflow not installed (no C:\Program Files\Deskflow). Run: .\DeskBridge.ps1 install"
}

function Invoke-StopDeskflow {
  $stopped = $false
  foreach ($n in 'deskflow-core', 'deskflow-client', 'deskflow-server', 'deskflow') {
    $procs = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($procs) {
      $procs | Stop-Process -Force
      Write-Ok "stopped: $n"
      $stopped = $true
    }
  }
  if (-not $stopped) { Write-Warn2 'nothing was running' }
}

function Get-LocalFingerprint {
  $settings = Join-Path $env:ProgramData 'Deskflow'
  $cert = Join-Path $settings 'tls\deskflow.pem'
  if (Test-Path -LiteralPath $cert) {
    & 'C:\Program Files\Git\usr\bin\openssl.exe' x509 -in $cert -noout -fingerprint -sha256
  } else { Write-Host '  local TLS certificate: not yet generated' }
}

function Initialize-DeskflowCertificate([string]$settings) {
  $tls = Join-Path $settings 'tls'
  $pem = Join-Path $tls 'deskflow.pem'
  if (Test-Path -LiteralPath $pem) { return }
  New-Item -ItemType Directory -Path $tls -Force | Out-Null
  $openssl = 'C:\Program Files\Git\usr\bin\openssl.exe'
  if (-not (Test-Path -LiteralPath $openssl)) {
    $openssl = (Get-Command openssl.exe -ErrorAction Stop).Source
  }
  $tempCert = Join-Path $tls 'certificate.tmp'
  $tempKey = Join-Path $tls 'private-key.tmp'
  try {
    & $openssl req -x509 -newkey rsa:2048 -nodes -keyout $tempKey -out $tempCert -days 365 -subj '/CN=Deskflow' 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Deskflow TLS certificate generation failed' }
    [IO.File]::WriteAllText($pem, ([IO.File]::ReadAllText($tempKey) + [IO.File]::ReadAllText($tempCert)))
    Write-Ok 'local TLS certificate generated'
  } finally {
    Remove-Item -LiteralPath $tempKey,$tempCert -ErrorAction SilentlyContinue
  }
}

$script:DeskDir = $null

switch ($Action) {
  'install' {
    if (-not (Test-Admin)) { throw 'Run this from an elevated (Administrator) PowerShell: right-click PowerShell -> Run as administrator.' }
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $bundleRoot = Split-Path -Parent $scriptDir
    $msi = Join-Path $bundleRoot "engine\$MsiFile"
    if (-not (Test-Path $msi)) { throw "engine MSI not found: $msi (bundle must include engine\$MsiFile)" }
    $sha = (Get-FileHash -Algorithm SHA256 $msi).Hash.ToLower()
    if ($sha -ne $MsiSha256) { throw "SHA256 mismatch for ${MsiFile}: got $sha, expected $MsiSha256. Do NOT install." }
    Write-Ok "SHA256 verified for $MsiFile"
    Write-Ok 'installing Deskflow engine (silent)...'
    $p = Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /qn /norestart" -Wait -PassThru
    if ($p.ExitCode -notin 0,3010) { throw "msiexec exited with $($p.ExitCode)" }
    $script:DeskDir = Get-DeskDir
    $settings = Join-Path $env:ProgramData 'Deskflow'
    if (-not (Test-Path $settings)) { New-Item -ItemType Directory -Path $settings | Out-Null }

    $serverCfg = Join-Path $settings 'server.config'
    $srcCfg = Join-Path $bundleRoot 'config\server.config'
    if (-not (Test-Path $srcCfg)) { throw 'config\server.config missing from bundle' }
    Copy-Item $srcCfg $serverCfg -Force

    $conf = Join-Path $settings 'Deskflow.conf'
    $srcConf = Join-Path $bundleRoot 'config\server.conf'
    if (-not (Test-Path $srcConf)) { throw 'config\server.conf missing from bundle' }
    if (Test-Path $conf) {
      Copy-Item $conf "$conf.bak$(Get-Date -Format yyyyMMddHHmmss)" -Force
      Write-Warn2 'existing Deskflow.conf backed up'
    }
    $configText = (Get-Content -LiteralPath $srcConf -Raw).Replace('C:/ProgramData/Deskflow/server.config', $serverCfg.Replace('\', '/'))
    Set-Content -LiteralPath $conf -Value $configText -Encoding utf8
    $accountSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $settings /grant "*${accountSid}:(OI)(CI)M" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Unable to grant the desktop user access to Deskflow settings' }
    # This setup is on demand. Desktop mode does not require a boot service.
    Stop-Service -Name Deskflow -ErrorAction SilentlyContinue
    Set-Service -Name Deskflow -StartupType Manual -ErrorAction SilentlyContinue
    Initialize-DeskflowCertificate $settings
    Write-Ok "config written: $conf + $serverCfg"

    # The upstream MSI installs broad inbound app rules. Use the scoped rule below.
    Get-NetFirewallRule -DisplayName 'Deskflow Server','Deskflow Client' -ErrorAction SilentlyContinue |
      Where-Object { $_.Direction -eq 'Inbound' } | Disable-NetFirewallRule
    if ([string]::IsNullOrWhiteSpace($ClientIP)) {
      $ClientIP = Read-Host 'Client PC IP address (the other machine) for the firewall rule'
    }
    try { [void][ipaddress]::Parse($ClientIP) } catch { throw "Invalid client IP address: $ClientIP" }
    $existing = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
    if (-not $existing) {
      New-NetFirewallRule -DisplayName $FirewallRuleName -Direction Inbound -Protocol TCP `
        -LocalPort $Port -RemoteAddress $ClientIP -Action Allow -Profile Domain,Private `
        -Description "Deskflow server (DeskBridge) inbound, client $ClientIP" | Out-Null
      Write-Ok "firewall rule added: $FirewallRuleName (private+domain, TCP $Port, from $ClientIP)"
    } elseif (@($existing | Get-NetFirewallAddressFilter).RemoteAddress -notcontains $ClientIP) {
      Write-Warn2 'existing firewall rule is scoped to a different address - remove it and re-run install if the client IP changed'
    } else {
      Write-Ok 'firewall rule already present'
    }
    Write-Ok "installed to $script:DeskDir"
    Write-Ok "next: .\DeskBridge.ps1 start, then run the client on the Fedora PC"
  }

  'start' {
    $script:DeskDir = Get-DeskDir
    if (Get-Process -Name 'deskflow', 'deskflow-core' -ErrorAction SilentlyContinue) {
      Write-Ok 'already running'
      return
    }
    Start-Process -FilePath (Join-Path $script:DeskDir 'deskflow.exe')
    Write-Ok 'started Deskflow (tray icon). On first client connection, confirm the TLS fingerprint dialog.'
  }

  'stop' { Invoke-StopDeskflow }

  'status' {
    $ok = $true
    try { $script:DeskDir = Get-DeskDir } catch { Write-Warn2 $_.Exception.Message; $ok = $false }
    $procs = Get-Process -Name 'deskflow', 'deskflow-core' -ErrorAction SilentlyContinue
    if ($procs) {
      Write-Ok 'processes:'
      $procs | ForEach-Object { Write-Host "  $($_.ProcessName) (pid $($_.Id))" }
    } else {
      Write-Warn2 'no deskflow process running'
      $ok = $false
    }
    $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($conns) {
      Write-Ok "TCP ${Port}:"
      $conns | ForEach-Object {
        Write-Host ("  {0}:{1} -> {2}:{3} [{4}]" -f $_.LocalAddress, $_.LocalPort, $_.RemoteAddress, $_.RemotePort, $_.State)
      }
      if ($conns | Where-Object { $_.State -eq 'Established' }) {
        Write-Ok 'server has an ESTABLISHED client connection'
      } else {
        Write-Warn2 'listening but no established client connection yet'
      }
    } else {
      Write-Warn2 "not listening on port $Port (start the server)"
      $ok = $false
    }
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) { Write-Host "  autostart: enabled (task state: $($task.State))" }
    else { Write-Host '  autostart: disabled (default)' }
    if ($ok) { Get-LocalFingerprint }
    if (-not $ok) { exit 1 }
  }

  'autostart' {
    $script:DeskDir = Get-DeskDir
    if ($DisableAutostart) {
      Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
      Write-Ok 'autostart disabled'
    } else {
      if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Write-Ok 'autostart already enabled'
      } else {
        $a = New-ScheduledTaskAction -Execute (Join-Path $script:DeskDir 'deskflow.exe')
        $t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        Register-ScheduledTask -TaskName $TaskName -Action $a -Trigger $t -Settings $s `
          -Description 'Start Deskflow server (DeskBridge) at user logon' | Out-Null
        Write-Ok "autostart enabled (logon task: $TaskName)"
      }
    }
  }

  'uninstall' {
    Invoke-StopDeskflow
    try {
      $script:DeskDir = Get-DeskDir
      $settings = Join-Path $env:ProgramData 'Deskflow'
      foreach ($f in 'Deskflow.conf', 'server.config') {
        $p = Join-Path $settings $f
        if (Test-Path $p) {
          Move-Item $p "$p.uninstalled$(Get-Date -Format yyyyMMddHHmmss)" -Force
          Write-Ok "moved $f aside"
        }
      }
    } catch { Write-Warn2 "engine not installed, skipping config cleanup: $($_.Exception.Message)" }
    Remove-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    if ($RemoveEngine) {
      if (-not (Test-Admin)) { throw 'Elevation required for -RemoveEngine.' }
      $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
      $bundleRoot = Split-Path -Parent $scriptDir
      $msi = Join-Path $bundleRoot "engine\$MsiFile"
      if (-not (Test-Path $msi)) { throw "engine MSI not found: $msi" }
      $p = Start-Process msiexec.exe -ArgumentList "/x `"$msi`" /qn /norestart" -Wait -PassThru
      if ($p.ExitCode -notin 0,3010) { throw "msiexec exited with $($p.ExitCode)" }
      Write-Ok 'engine removed'
    } else {
      Write-Ok 'engine left installed (remove with: .\DeskBridge.ps1 uninstall -RemoveEngine)'
    }
    Write-Ok 'uninstall complete'
  }

  'help' {
    Write-Host 'Usage: .\DeskBridge.ps1 <install|start|stop|status|autostart|uninstall> [-DisableAutostart] [-RemoveEngine]'
    Write-Host 'See docs/SETUP-WINDOWS.md for the full procedure.'
  }
}
