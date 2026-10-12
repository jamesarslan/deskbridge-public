@echo off
where pwsh.exe >nul 2>nul
if errorlevel 1 (
  echo Install PowerShell 7 first: https://aka.ms/powershell
  pause
  exit /b 1
)
set "DESKBRIDGE_SETUP_SCRIPT=%~dp0tools\DeskBridge.ps1"
pwsh.exe -NoProfile -Command "$argsList='-NoProfile -ExecutionPolicy Bypass -File '+[char]34+$env:DESKBRIDGE_SETUP_SCRIPT+[char]34+' setup'; $p=Start-Process pwsh.exe -Verb RunAs -ArgumentList $argsList -Wait -PassThru; exit $p.ExitCode"
if errorlevel 1 echo Setup did not finish. See docs/SETUP-WINDOWS.md to inspect the error.
pause
