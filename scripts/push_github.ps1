# Create lily-880/hoi4-clausewitz-win (if missing) and push main.
# Uses Windows Git Credential Manager (already has github.com for lily-880).
$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent $PSScriptRoot
Set-Location $RepoDir
$Owner = "lily-880"
$Name = "hoi4-clausewitz-win"
$Remote = "https://github.com/$Owner/$Name.git"

if (-not (Test-Path .git)) {
  git init -b main
  git add -A
  git -c user.name=lily-880 -c user.email=428468631@qq.com commit -m "Initial Phase 1: Windows ReadProcessMemory backend for HOI4 1.19.4"
}

# Resolve credential via git helper (GCM)
$cred = echo "protocol=https`nhost=github.com`n`n" | git credential fill
$token = ($cred | Select-String -Pattern '^password=(.+)$').Matches.Groups[1].Value
$user = ($cred | Select-String -Pattern '^username=(.+)$').Matches.Groups[1].Value
if (-not $token) { throw "No GitHub credential from git credential fill" }

$pair = "{0}:{1}" -f $user, $token
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ Authorization = "Basic $b64"; Accept = "application/vnd.github+json"; "User-Agent" = "hoi4-clausewitz-win-push" }

try {
  Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Name" | Out-Null
  Write-Host "Repo exists"
} catch {
  $body = @{ name = $Name; description = "Windows Clausewitz-style HOI4 live memory bridge (Phase 1 read-only)"; private = $false; auto_init = $false } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Headers $headers -Uri "https://api.github.com/user/repos" -Body $body -ContentType "application/json" | Out-Null
  Write-Host "Created https://github.com/$Owner/$Name"
}

git remote remove origin 2>$null
git remote add origin $Remote
git push -u origin main
Write-Host "Pushed $Remote"
