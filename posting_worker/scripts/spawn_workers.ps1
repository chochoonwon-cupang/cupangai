param([int]$WorkerCount = 5)

$root = Split-Path -Parent $PSScriptRoot

# Leader 1개 (VM_ID는 uuid로, 이름은 leader)
$leaderId = [guid]::NewGuid().ToString()
$cmdLeader = "`$env:ROLE='leader'; `$env:VM_ID='$leaderId'; `$env:VM_NAME='leader'; cd '$root'; python -m src.main"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmdLeader
Start-Sleep -Milliseconds 200

# Worker N개 (VM_ID는 uuid로, VM_NAME만 vm-001 형태)
for ($i = 1; $i -le $WorkerCount; $i++) {
  $vmId = [guid]::NewGuid().ToString()
  $vmName = "vm-{0:D3}" -f $i
  $cmd = "`$env:ROLE='worker'; `$env:VM_ID='$vmId'; `$env:VM_NAME='$vmName'; cd '$root'; python -m src.main"
  Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
  Start-Sleep -Milliseconds 200
}
