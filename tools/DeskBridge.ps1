#requires -Version 7.4
# DeskBridge Windows server helper. Deskflow remains the input-sharing engine.
[CmdletBinding()]
param(
  [Parameter(Position=0)][ValidateSet('setup','install','start','stop','restart','status','diagnose','fingerprint','autostart','uninstall','help')][string]$Action='help',
  [string]$ClientIP='',
  [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')][string]$Name='windows',
  [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')][string]$PeerName='fedora',
  [ValidateSet('left','right','top','bottom')][string]$Side='left',
  [ValidateRange(1,65535)][int]$Port=24800,
  [switch]$QuietLayouts,[switch]$DisableAutostart,[switch]$RemoveEngine,[switch]$Json,[switch]$Notify
)
$ErrorActionPreference='Stop'
$BundleRoot=Split-Path -Parent $PSScriptRoot
$HelperPath=$PSCommandPath
$SettingsRoot=Join-Path $env:ProgramData 'Deskflow'
$StateFile=Join-Path $SettingsRoot 'deskbridge-state.json'
$MsiFile='deskflow-1.27.0-win-x64.msi'
$MsiSha256='0ca5668c4731f5477d0b189bdb11196a2ca51281985d9d8c0757bf7f3b782d64'
$FirewallRuleName='DeskBridge Deskflow Server (TCP 24800)'
$TaskName='DeskBridge Deskflow Server'

function Test-Admin {
  ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Assert-Admin {
  if (-not (Test-Admin)) {throw 'Administrator PowerShell required. Open Setup.cmd for guided setup.'}
}
function Get-DeskDir {
  foreach ($dir in @((Join-Path $env:ProgramFiles 'Deskflow'),(Join-Path ${env:ProgramFiles(x86)} 'Deskflow'))) {
    if (Test-Path -LiteralPath (Join-Path $dir 'deskflow.exe')) {return $dir}
  }
  throw 'Deskflow not installed. Run Setup.cmd first.'
}
function Get-OwnedProcesses {
  try {$dir=Get-DeskDir} catch {return @()}
  $session=(Get-Process -Id $PID).SessionId
  @(Get-Process -Name deskflow,deskflow-core,deskflow-client,deskflow-server -ErrorAction SilentlyContinue |
    Where-Object {$_.SessionId -eq $session -and $_.Path -and [IO.Path]::GetDirectoryName($_.Path) -eq $dir})
}
function Read-Ini([string]$Text) {
  $result=@{};$section=''
  foreach ($line in ($Text -split '\r?\n')) {
    if ($line -match '^\s*\[([^\]]+)\]\s*$') {$section=$Matches[1]}
    elseif ($line -match '^\s*([^;#=]+?)\s*=\s*(.*)$') {$result["$section.$($Matches[1].Trim())"]=$Matches[2].Trim()}
  }
  return $result
}
function Merge-Ini([string]$Text,[System.Collections.IDictionary]$Sections) {
  $lines=[Collections.Generic.List[string]]::new();$lines.AddRange([string[]]($Text -split '\r?\n'))
  foreach ($section in $Sections.Keys) {
    $start=-1
    for ($i=0;$i -lt $lines.Count;$i++) {if ($lines[$i].Trim() -ceq "[$section]") {$start=$i;break}}
    if ($start -lt 0) {$lines.Add('');$lines.Add("[$section]");$start=$lines.Count-1}
    foreach ($key in $Sections[$section].Keys) {
      $end=$lines.Count
      for ($i=$start+1;$i -lt $lines.Count;$i++) {if ($lines[$i] -match '^\s*\[') {$end=$i;break}}
      $found=$false
      for ($i=$start+1;$i -lt $end;$i++) {
        if ($lines[$i] -cmatch ('^\s*'+[regex]::Escape($key)+'\s*=')) {$lines[$i]="$key=$($Sections[$section][$key])";$found=$true;break}
      }
      if (-not $found) {$lines.Insert($end,"$key=$($Sections[$section][$key])")}
    }
  }
  return ($lines -join "`r`n").TrimEnd()+"`r`n"
}
function Write-PreservedFile([string]$Path,[string]$Text) {
  [IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
  if ((Test-Path -LiteralPath $Path) -and [IO.File]::ReadAllText($Path) -ceq $Text) {return}
  if (Test-Path -LiteralPath $Path) {Copy-Item -LiteralPath $Path -Destination "$Path.bak.$([DateTime]::UtcNow.Ticks)"}
  $temp=Join-Path (Split-Path -Parent $Path) ([IO.Path]::GetRandomFileName())
  try {[IO.File]::WriteAllText($temp,$Text,[Text.UTF8Encoding]::new($false));Move-Item -LiteralPath $temp -Destination $Path -Force}
  finally {if (Test-Path -LiteralPath $temp) {Remove-Item -LiteralPath $temp}}
}
function Get-Certificate([string]$Root=$SettingsRoot) {
  $pem=Join-Path $Root 'tls\deskflow.pem'
  if (-not (Test-Path -LiteralPath $pem)) {return $null}
  return [Security.Cryptography.X509Certificates.X509Certificate2]::CreateFromPemFile($pem,$pem)
}
function Get-LocalFingerprint([string]$Root=$SettingsRoot) {
  $certificate=Get-Certificate $Root
  if (-not $certificate) {throw 'Local TLS certificate missing. Run setup first.'}
  try {
    if ($certificate.NotAfter.ToUniversalTime() -lt [DateTime]::UtcNow) {throw 'Local TLS certificate expired; rotate it explicitly and re-pair both PCs.'}
    return 'v2:sha256:'+[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($certificate.RawData)).ToLowerInvariant()
  }
  finally {$certificate.Dispose()}
}
function Initialize-Certificate([string]$Root=$SettingsRoot) {
  $pem=Join-Path $Root 'tls\deskflow.pem'
  if (Test-Path -LiteralPath $pem) {$certificate=Get-Certificate $Root;$certificate.Dispose();return}
  $rsa=[Security.Cryptography.RSA]::Create(2048)
  try {
    $request=[Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=Deskflow',$rsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $certificate=$request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5),[DateTimeOffset]::UtcNow.AddDays(365))
    try {
      [IO.Directory]::CreateDirectory((Split-Path -Parent $pem)) | Out-Null
      [IO.File]::WriteAllText($pem,$rsa.ExportPkcs8PrivateKeyPem()+"`n"+$certificate.ExportCertificatePem()+"`n")
      $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
      & icacls.exe $pem /inheritance:r /grant:r "*${sid}:F" '*S-1-5-18:F' '*S-1-5-32-544:F' | Out-Null
      if ($LASTEXITCODE -ne 0) {throw 'Could not restrict TLS private key access'}
    } finally {$certificate.Dispose()}
  } finally {$rsa.Dispose()}
}
function New-ServerConfig([string]$Existing,[string]$LocalName,[string]$RemoteName,[string]$Edge,[int]$ListenPort,[string]$Root,[bool]$Quiet) {
  if ($LocalName -eq $RemoteName) {throw 'Computer names must be different'}
  $sections=[ordered]@{
    core=[ordered]@{computerName=$LocalName;coreMode='2';processMode='1';port="$ListenPort";preventSleep='false'}
    server=[ordered]@{externalConfig='true';externalConfigFile=(Join-Path $Root 'server.config').Replace('\','/');enableClipboard='true';switchDelay='250'}
    security=[ordered]@{tlsEnabled='true';checkPeerFingerprints='true';keySize='2048'}
    gui=[ordered]@{startCoreWithGui='true';closeToTray='true';autoHide='false';enableUpdateCheck='false'}
  }
  $sections["computer_$LocalName"]=[ordered]@{name=$LocalName};$sections["computer_$RemoteName"]=[ordered]@{name=$RemoteName}
  if ($Quiet) {$sections.gui.ignoreMissingKeyboardLayouts='true'}
  $directions=@{left='left';right='right';top='up';bottom='down'};$opposite=@{left='right';right='left';top='down';bottom='up'}
  $map="section: links`r`n${LocalName}:`r`n    $($directions[$Edge]) = $RemoteName`r`n${RemoteName}:`r`n    $($opposite[$Edge]) = $LocalName`r`nend`r`nsection: options`r`n    clipboardSharing = true`r`nend`r`n"
  return @{Ini=(Merge-Ini $Existing $sections);Map=$map}
}
function Assert-Configuration {
  $path=Join-Path $SettingsRoot 'Deskflow.conf'
  if (-not (Test-Path -LiteralPath $path)) {throw 'Configuration missing. Run Setup.cmd.'}
  $ini=Read-Ini ([IO.File]::ReadAllText($path))
  if ($ini['core.coreMode'] -ne '2') {throw 'Helper supports the Windows server role. Other roles use upstream Deskflow.'}
  foreach ($key in 'tlsEnabled','checkPeerFingerprints') {if ($ini["security.$key"] -notin 'true','1') {throw "security.$key must be true"}}
  if ($ini['core.processMode'] -ne '1') {throw 'Desktop mode required; run setup with the engine stopped.'}
  $listenPort=0
  if (-not [int]::TryParse($ini['core.port'],[ref]$listenPort) -or $listenPort -lt 1 -or $listenPort -gt 65535) {throw 'Invalid configured port'}
  if (-not (Test-Path -LiteralPath $ini['server.externalConfigFile'])) {throw 'Screen map missing'}
  $null=Get-LocalFingerprint
  return $ini
}
function Stop-Engine {
  $procs=@(Get-OwnedProcesses)
  foreach ($proc in ($procs | Where-Object ProcessName -eq 'deskflow')) {$null=$proc.CloseMainWindow()}
  if ($procs.Count) {Start-Sleep -Milliseconds 700}
  Get-OwnedProcesses | Stop-Process -Force
  if (@(Get-OwnedProcesses).Count) {throw 'Deskflow did not stop'}
}
function Start-Engine {
  $ini=Assert-Configuration
  if (@(Get-OwnedProcesses).Count -eq 0) {Start-Process -FilePath (Join-Path (Get-DeskDir) 'deskflow.exe')}
  $deadline=[DateTime]::UtcNow.AddSeconds(8)
  do {
    $owned=@(Get-OwnedProcesses).Id
    $listener=@(Get-NetTCPConnection -LocalPort ([int]$ini['core.port']) -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.OwningProcess -in $owned})
    if ($listener.Count) {Write-Host 'Server listening. Confirm pairing on both PCs and GNOME input permission on the client.';return}
    Start-Sleep -Milliseconds 400
  } while ([DateTime]::UtcNow -lt $deadline)
  throw 'GUI launched but server did not listen. Inspect Deskflow; input has not been verified.'
}
function Get-Status {
  $procs=@(Get-OwnedProcesses);$issues=[Collections.Generic.List[string]]::new();$ini=@{}
  try {$ini=Assert-Configuration} catch {$issues.Add($_.Exception.Message)}
  $conns=@()
  if ($ini['core.port']) {$conns=@(Get-NetTCPConnection -LocalPort ([int]$ini['core.port']) -ErrorAction SilentlyContinue | Where-Object {$_.OwningProcess -in $procs.Id} | Select-Object State,LocalAddress,LocalPort,RemoteAddress,RemotePort)}
  $fingerprint=$null;try {$fingerprint=Get-LocalFingerprint} catch {}
  $rule=Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
  $addresses=@($rule | Get-NetFirewallAddressFilter -ErrorAction SilentlyContinue | Select-Object -ExpandProperty RemoteAddress)
  $service=Get-Service -Name Deskflow -ErrorAction SilentlyContinue
  return [ordered]@{processes=@($procs | Select-Object Id,ProcessName);configErrors=@($issues);tcp=$conns;fingerprint=$fingerprint;firewallPeerAddresses=$addresses;firewallRuleEnabled=@($rule | Select-Object Enabled,Profile);autostart=[bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue);serviceStatus="$($service.Status)";note='TCP alone does not prove physical input or clipboard success.'}
}
function Install-Engine {
  $dir=$null;try {$dir=Get-DeskDir} catch {}
  if ($dir -and (Get-Item -LiteralPath (Join-Path $dir 'deskflow.exe')).VersionInfo.FileVersion -match '^1\.27\.0(\.|$)') {return}
  if ($dir -and [version]((Get-Item -LiteralPath (Join-Path $dir 'deskflow.exe')).VersionInfo.FileVersion -replace '[^0-9.].*$','') -gt [version]'1.27.0.0') {throw 'A newer Deskflow is installed; automatic downgrade refused. Review compatibility before changing it.'}
  if (@(Get-OwnedProcesses).Count) {throw 'Stop Deskflow before upgrading'}
  $msi=Get-EngineInstaller
  $process=Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /qn /norestart" -Wait -PassThru
  if ($process.ExitCode -notin 0,3010) {throw "MSI installation failed: $($process.ExitCode)"}
  if ($process.ExitCode -eq 3010) {Write-Warning 'Windows reports a reboot required; no reboot performed.'}
}
function Get-EngineInstaller {
  $cache=Join-Path $env:LOCALAPPDATA 'DeskBridge\downloads'
  [IO.Directory]::CreateDirectory($cache) | Out-Null
  $msi=Join-Path $cache $MsiFile
  if (-not (Test-Path -LiteralPath $msi)) {
    $temp=Join-Path $cache ([IO.Path]::GetRandomFileName())
    try {
      Write-Host 'Downloading official Deskflow v1.27.0 Windows installer...'
      Invoke-WebRequest -Uri "https://github.com/deskflow/deskflow/releases/download/v1.27.0/$MsiFile" -OutFile $temp
      if ((Get-Item -LiteralPath $temp).Length -ne 15953799 -or (Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLowerInvariant() -ne $MsiSha256) {throw 'Upstream installer size/SHA256 mismatch; refused'}
      Move-Item -LiteralPath $temp -Destination $msi
    } finally {if (Test-Path -LiteralPath $temp) {Remove-Item -LiteralPath $temp}}
  }
  if ((Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash.ToLowerInvariant() -ne $MsiSha256) {throw 'Cached installer SHA256 mismatch; remove that cache file and retry'}
  return $msi
}
function Setup-Server {
  Assert-Admin
  if (@(Get-OwnedProcesses).Count) {throw 'Stop Deskflow before setup. Configuration unchanged.'}
  if ($Name -eq $PeerName) {throw 'Computer names must be different'}
  if (-not $ClientIP) {$script:ClientIP=Read-Host 'Client PC IP address (for firewall)'}
  $address=$null
  if (-not [ipaddress]::TryParse($ClientIP,[ref]$address)) {throw 'ClientIP must be one IP; networks/wildcards not accepted.'}
  Install-Engine
  $conf=Join-Path $SettingsRoot 'Deskflow.conf'
  $existing=if (Test-Path -LiteralPath $conf) {[IO.File]::ReadAllText($conf)} else {''}
  $config=New-ServerConfig $existing $Name $PeerName $Side $Port $SettingsRoot $QuietLayouts
  Write-PreservedFile $conf $config.Ini;Write-PreservedFile (Join-Path $SettingsRoot 'server.config') $config.Map
  Initialize-Certificate
  $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  & icacls.exe $SettingsRoot /grant "*${sid}:(OI)(CI)M" | Out-Null
  if ($LASTEXITCODE -ne 0) {throw 'Could not grant desktop user config access'}
  Stop-Service -Name Deskflow -ErrorAction SilentlyContinue;Set-Service -Name Deskflow -StartupType Manual -ErrorAction SilentlyContinue
  Get-NetFirewallRule -DisplayName 'Deskflow Server','Deskflow Client' -ErrorAction SilentlyContinue | Where-Object Direction -eq Inbound | Disable-NetFirewallRule
  $program=Join-Path (Get-DeskDir) 'deskflow-core.exe';$rule=Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
  if ($rule) {$rule | Set-NetFirewallRule -Enabled True -Direction Inbound -Protocol TCP -LocalPort $Port -RemoteAddress "$address" -Action Allow -Profile Private,Domain -Program $program}
  else {New-NetFirewallRule -DisplayName $FirewallRuleName -Enabled True -Direction Inbound -Protocol TCP -LocalPort $Port -RemoteAddress "$address" -Action Allow -Profile Private,Domain -Program $program | Out-Null}
  Write-PreservedFile $StateFile (([ordered]@{Name=$Name;PeerName=$PeerName;Side=$Side;Port=$Port;ClientIP="$address"} | ConvertTo-Json)+"`n")
  $desktop=[Environment]::GetFolderPath('Desktop');$shell=New-Object -ComObject WScript.Shell
  foreach ($kind in 'Start','Stop') {
    $shortcut=$shell.CreateShortcut((Join-Path $desktop "$kind DeskBridge.lnk"));$shortcut.TargetPath=(Get-Command pwsh.exe).Source
    $shortcut.Arguments="-NoProfile -WindowStyle Hidden -File `"$HelperPath`" $($kind.ToLowerInvariant()) -Notify";$shortcut.WorkingDirectory=$BundleRoot;$shortcut.IconLocation=(Join-Path (Get-DeskDir) 'deskflow.exe');$shortcut.Save()
  }
  Write-Host "Setup saved; client screen is $Side of $Name. Autostart unchanged."
  Write-Host 'Use Start DeskBridge, then compare complete fingerprints on BOTH PCs.'
  Get-LocalFingerprint
}
if ($MyInvocation.InvocationName -eq '.') {return} # expose pure functions to tests
try {
  if (Test-Path -LiteralPath $StateFile) {
    $saved=Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
    foreach ($key in 'Name','PeerName','Side','Port','ClientIP') {if (-not $PSBoundParameters.ContainsKey($key) -and $saved.$key) {Set-Variable -Name $key -Value $saved.$key}}
  }
  switch ($Action) {
    'setup' {Setup-Server}
    'install' {Assert-Admin;if (Test-Path -LiteralPath (Join-Path $SettingsRoot 'Deskflow.conf')) {Install-Engine;Write-Host 'Engine verified; config, pairing and autostart preserved. Use setup to change placement.'} else {Setup-Server}}
    'start' {Start-Engine}
    'stop' {Stop-Engine;Write-Host 'DeskBridge stopped'}
    'restart' {Stop-Engine;Start-Engine}
    'fingerprint' {Get-LocalFingerprint}
    {$_ -in 'status','diagnose'} {$status=Get-Status;if ($Json) {$status | ConvertTo-Json -Depth 6} else {$status | Format-List};if ($status.configErrors.Count) {exit 1}}
    'autostart' {
      Assert-Admin
      if ($DisableAutostart) {Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue}
      else {
        $null=Assert-Configuration;$action=New-ScheduledTaskAction -Execute (Join-Path (Get-DeskDir) 'deskflow.exe')
        $identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name;$trigger=New-ScheduledTaskTrigger -AtLogOn -User $identity
        $principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
      }
      Write-Host "Autostart $(if ($DisableAutostart) {'off'} else {'on'})"
    }
    'uninstall' {
      Assert-Admin;Stop-Engine
      Remove-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue;Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
      if (Test-Path -LiteralPath $StateFile) {
        foreach ($file in 'Deskflow.conf','server.config','deskbridge-state.json') {$path=Join-Path $SettingsRoot $file;if (Test-Path -LiteralPath $path) {Move-Item -LiteralPath $path -Destination "$path.uninstalled.$([DateTime]::UtcNow.Ticks)"}}
      }
      if ($RemoveEngine) {
        $msi=Get-EngineInstaller
        $process=Start-Process msiexec.exe -ArgumentList "/x `"$msi`" /qn /norestart" -Wait -PassThru
        if ($process.ExitCode -notin 0,1605,3010) {throw "MSI uninstall failed: $($process.ExitCode)"}
      }
      Write-Host 'Product removed. TLS/trust/config backups retained; engine retained unless -RemoveEngine.'
    }
    'help' {Write-Host 'Setup.cmd or: .\tools\DeskBridge.ps1 setup -ClientIP <peer-ip> [-Side left|right|top|bottom]. Other actions: install,start,stop,restart,status,diagnose,fingerprint,autostart,uninstall. PowerShell 7 required. Use autostart -DisableAutostart to opt out.'}
  }
} catch {
  $message=$_.Exception.Message
  if ($Notify) {Add-Type -AssemblyName System.Windows.Forms;[void][System.Windows.Forms.MessageBox]::Show($message,'DeskBridge')}
  if ($Json) {@{error=$message} | ConvertTo-Json} else {Write-Error $message -ErrorAction Continue}
  exit 1
}
