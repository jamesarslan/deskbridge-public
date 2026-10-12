# Real configuration, PEM identity and upgrade-preservation checks in a temp dir.
$ErrorActionPreference='Stop'
. "$PSScriptRoot\..\tools\DeskBridge.ps1"
function Assert([bool]$Condition,[string]$Message) {if (-not $Condition) {throw $Message}}
$root=Join-Path ([IO.Path]::GetTempPath()) ('deskbridge-test-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root) | Out-Null
try {
  $existing="[client]`nxdpRestoreToken=synthetic`n[gui]`nignoreMissingKeyboardLayouts=true`n[custom]`nfutureKey=keep`n"
  $config=New-ServerConfig $existing 'host' 'guest' 'top' 24991 $root $false
  $ini=Read-Ini $config.Ini
  Assert ($ini['client.xdpRestoreToken'] -eq 'synthetic') 'Permission token lost'
  Assert ($ini['gui.ignoreMissingKeyboardLayouts'] -eq 'true') 'Popup preference lost'
  Assert ($ini['custom.futureKey'] -eq 'keep') 'Unknown engine preference lost'
  Assert ($ini['computer_guest.name'] -eq 'guest') 'Missing computer definition'
  Assert ($config.Map.Contains('up = guest') -and $config.Map.Contains('down = host')) 'Invalid vertical links'
  Assert ((New-ServerConfig $config.Ini 'host' 'guest' 'top' 24991 $root $false).Ini -ceq $config.Ini) 'Rerun changes config'
  $path=Join-Path $root 'Deskflow.conf'
  Write-PreservedFile $path $config.Ini;Write-PreservedFile $path $config.Ini
  Assert (@(Get-ChildItem -LiteralPath $root -Filter '*.bak.*').Count -eq 0) 'Unchanged configuration backed up again'
  Initialize-Certificate $root
  $fingerprint=Get-LocalFingerprint $root
  Assert ($fingerprint -match '^v2:sha256:[a-f0-9]{64}$') 'Invalid SHA256 fingerprint'
  $certPath=Join-Path $root 'tls\deskflow.pem';$hash=(Get-FileHash -LiteralPath $certPath).Hash
  Initialize-Certificate $root
  Assert ((Get-FileHash -LiteralPath $certPath).Hash -eq $hash) 'Certificate regenerated during rerun'
  Assert (@((Get-Acl -LiteralPath $certPath).Access | Where-Object {$_.IsInherited}).Count -eq 0) 'Private key has inherited access'
  Write-Host 'Windows configuration, idempotence, real PEM and key ACL checks PASS'
} finally {
  $resolved=[IO.Path]::GetFullPath($root)
  if ($resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolved).StartsWith('deskbridge-test-')) {Remove-Item -LiteralPath $resolved -Recurse -Force}
}
