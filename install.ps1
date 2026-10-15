# Vex Assistant 4.3 (public build) setup. Built with Windows' own IExpress; this script downloads nothing.
# The speech engine and AI brain are downloaded later by the app's first-run setup, only when you click.
# Installs for the current user only into %LOCALAPPDATA%\Programs\VexAssistant (no admin rights needed).
# Adds "Vex Assistant" Start menu + Desktop shortcuts and an Apps & features entry with an uninstaller.
# Never touches antivirus, accounts, the camera or system settings.
param([string]$Root = "", [switch]$Test, [switch]$NoLaunch)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$ver = "4.3.0"
$src = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = $env:VEXPUB_ROOT }
if (-not $Root) { $Root = Join-Path $env:LOCALAPPDATA "Programs\VexAssistant" }
if ($env:VEXPUB_TEST -eq "1") { $Test = $true }
if ($Test) { $NoLaunch = $true }
Write-Host ""
Write-Host "  Vex Assistant $ver setup" -ForegroundColor Cyan
Write-Host "  Installing to $Root"
Write-Host ""
$marker = Join-Path $Root ".vex-assistant-install"
if ((Test-Path $Root) -and (Get-ChildItem $Root -Force -EA 0 | Select -First 1) -and -not (Test-Path $marker) -and -not (Test-Path (Join-Path $Root "app\run_vex.pyw"))) {
  throw "The folder $Root already has other files in it. Pick an empty folder (or the existing Vex Assistant folder)."
}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
"Vex Assistant install folder. The uninstaller only empties folders that contain this file." | Set-Content $marker
# stop a running copy of THIS install only
Get-Process pythonw, python -EA 0 | ? { $_.Path -and $_.Path -like "$Root\*" } | Stop-Process -Force
Start-Sleep 1
if (Test-Path "$Root\app") { Remove-Item "$Root\app" -Recurse -Force }   # program files only; settings, memory and logs stay
$zip = Join-Path $src "VexAssistant-4.3.zip"
if (Test-Path $zip) {
  Write-Host "  Unpacking (about 1 minute)..."
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
  try {
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    foreach ($e in $z.Entries) {
      $name = $e.FullName -replace '^VexAssistant-[^/\\]+[/\\]', ''
      if (-not $name) { continue }
      $dest = [System.IO.Path]::GetFullPath((Join-Path $Root $name))
      if (-not $dest.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) { continue }
      if ($name.EndsWith('/') -or $name.EndsWith('\')) { New-Item -ItemType Directory -Force $dest | Out-Null; continue }
      $dir = Split-Path -Parent $dest
      if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
      [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $dest, $true)
    }
  } finally { $z.Dispose() }
} elseif (Test-Path (Join-Path $src "app\run_vex.pyw")) {
  Write-Host "  Copying files..."
  foreach ($d in "app", "python") { robocopy (Join-Path $src $d) (Join-Path $Root $d) /E /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null }
  if (Test-Path (Join-Path $src "README.txt")) { Copy-Item (Join-Path $src "README.txt") $Root -Force }
} else { throw "Setup files are missing. Unzip the whole download first, then run Install.cmd." }
Get-ChildItem "$Root\app" -Recurse -Directory -Filter __pycache__ -EA 0 | Remove-Item -Recurse -Force
New-Item -ItemType Directory -Force "$Root\models", "$Root\data" | Out-Null
Copy-Item $MyInvocation.MyCommand.Path "$Root\install.ps1" -Force -EA 0
$pyw = "$Root\python\pythonw.exe"
if (-not (Test-Path $pyw)) { throw "The bundled Python runtime did not unpack. Please download the installer again." }
$ico = "$Root\app\vex.ico"
$startLnk = Join-Path ([Environment]::GetFolderPath("Programs")) "Vex Assistant.lnk"
$deskLnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Vex Assistant.lnk"
$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\VexAssistantPublic"

# uninstaller (works for this folder only). Removes EVERYTHING by default: program, voice pack, models,
# settings, memory, encrypted keys, logs, crash reports, cache, shortcuts, startup entries and the Apps entry.
$RootQ = $Root.Replace("'", "''"); $startQ = $startLnk.Replace("'", "''"); $deskQ = $deskLnk.Replace("'", "''")
@"
# Vex Assistant uninstaller. Removes everything Vex Assistant put on this PC.
# -KeepData keeps settings/memory/logs (for reinstalling). Ollama is a separate app (remove it in Settings > Apps).
param([switch]`$Quiet, [switch]`$KeepData)
`$ErrorActionPreference = 'SilentlyContinue'
`$Root = '$RootQ'
Get-Process pythonw, python -EA 0 | ? { `$_.Path -and `$_.Path -like "`$Root\*" } | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" -EA 0 | ? { `$_.CommandLine -like "*`$Root*" } | % { Stop-Process -Id `$_.ProcessId -Force -EA 0 }
Remove-Item '$startQ', '$deskQ' -EA 0
Remove-Item (Join-Path ([Environment]::GetFolderPath('Startup')) 'Vex Assistant.lnk') -EA 0
Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'VexAssistantPublic' -EA 0
Remove-Item '$key' -Recurse -EA 0
Remove-Item (Join-Path `$env:TEMP 'vex_screen.png'), (Join-Path `$env:TEMP 'vex_look.jpg') -Force -EA 0
Start-Sleep 2
if (`$KeepData) {
  foreach (`$d in 'app', 'python', 'models', 'voicepack', 'cache') { Remove-Item (Join-Path `$Root `$d) -Recurse -Force -EA 0 }
  Write-Host "Vex Assistant removed. Your settings are kept in `$Root."
} else {
  Set-Location `$env:TEMP
  if (-not (Test-Path (Join-Path `$Root '.vex-assistant-install'))) { Write-Host "`$Root doesn't look like a Vex Assistant folder; nothing deleted."; exit 1 }
  Get-ChildItem `$Root -Force -EA 0 | ? { `$_.Name -notin 'Uninstall.ps1', 'Uninstall.cmd' } | Remove-Item -Recurse -Force -EA 0
  Start-Process cmd.exe -ArgumentList "/c ping -n 3 127.0.0.1 >nul & rd /s /q ```"`$Root```"" -WindowStyle Hidden
  Write-Host 'Vex Assistant and all of its data were removed.'
}
Write-Host 'If you installed Ollama for it, Ollama is a separate app: remove it in Settings > Apps if you no longer want it.'
if (-not `$Quiet) { Start-Sleep 4 }
"@ | Set-Content "$Root\Uninstall.ps1" -Encoding UTF8
"@echo off`r`ncd /d %TEMP%`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"%~dp0Uninstall.ps1`"" | Set-Content "$Root\Uninstall.cmd" -Encoding ASCII

if (-not $Test) {
  $ws = New-Object -ComObject WScript.Shell
  foreach ($l in @($startLnk, $deskLnk)) {
    $s = $ws.CreateShortcut($l); $s.TargetPath = $pyw; $s.Arguments = "`"$Root\app\run_vex.pyw`""; $s.WorkingDirectory = "$Root\app"
    $s.IconLocation = $ico; $s.Description = "Vex Assistant - your desktop AI assistant"; $s.Save()
  }
  New-Item $key -Force | Out-Null
  $p = @{DisplayName = "Vex Assistant"; DisplayVersion = $ver; Publisher = "Vex Assistant (community build)"; DisplayIcon = $ico; InstallLocation = $Root; EstimatedSize = 400000
         UninstallString = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$Root\Uninstall.ps1`""; NoModify = 1; NoRepair = 1}
  foreach ($n in $p.Keys) { New-ItemProperty $key -Name $n -Value $p[$n] -Force | Out-Null }
}
New-Item -ItemType Directory -Force "$Root\logs" | Out-Null
"$(Get-Date -f s) installed $ver" | Add-Content "$Root\logs\setup.log"

# friendly checks (no downloads)
$wv = $false
foreach ($k in "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
               "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
               "HKCU:\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}") { if (Test-Path $k) { $wv = $true } }
if (-not $wv) { Write-Host "  Note: Microsoft Edge WebView2 Runtime wasn't found. Windows 11 has it built in; on Windows 10 get it free from" -ForegroundColor Yellow
                Write-Host "  https://developer.microsoft.com/microsoft-edge/webview2/ (Evergreen Bootstrapper) if the window stays blank." -ForegroundColor Yellow }
$ol = (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") -or [bool](Get-Command ollama -EA 0)
Write-Host ""
Write-Host "  Vex Assistant installed." -ForegroundColor Green
Write-Host "  First run: a short setup downloads the voice pack (about 240 MB) and, if you want, sets up the free Ollama brain."
if (-not $NoLaunch) { Start-Process $pyw -ArgumentList "`"$Root\app\run_vex.pyw`"" -WorkingDirectory "$Root\app" }
