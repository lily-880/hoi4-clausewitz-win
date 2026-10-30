# Copy this repo into Paradox Documents for easy local runs.
$ErrorActionPreference = "Stop"
$Dest = Join-Path $env:USERPROFILE "Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win"
$Src = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Src "clausewitz_win.py"))) {
  $Src = $PSScriptRoot
  if (-not (Test-Path (Join-Path $Src "clausewitz_win.py"))) {
    Write-Error "Run from the repo (scripts/install_to_documents.ps1)"
  }
}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
robocopy $Src $Dest /MIR /XD .git __pycache__ .venv venv research\re-dumps /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
Write-Host "Installed to $Dest"
Write-Host "Try:  cd `"$Dest`"; `$env:HOI4_PATH='D:\STEAM\steam\steamapps\common\Hearts of Iron IV'; python clausewitz_win.py doctor"
