$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

powershell -ExecutionPolicy Bypass -File scripts/kill_workers.ps1
Start-Sleep -Seconds 2
python -m src.main
