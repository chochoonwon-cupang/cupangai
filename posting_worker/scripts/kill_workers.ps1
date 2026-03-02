# scripts/kill_workers.ps1 — 워커만 정확히 종료 (다른 Python 프로그램 보존)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*worker.py*" -or $_.CommandLine -like "*src.main*" } |
  ForEach-Object {
    try {
      Write-Host "Killing PID=$($_.ProcessId) $($_.CommandLine)"
      Stop-Process -Id $_.ProcessId -Force
    } catch {}
  }

Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process chromedriver -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
