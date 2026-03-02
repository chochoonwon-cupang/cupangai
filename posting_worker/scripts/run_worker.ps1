param(
  [string]$VmId = "vm-002"
)

$env:VM_ID = $VmId
$env:VM_NAME = $VmId
$env:REQUEUE_LEADER_VM = "vm-001"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -m src.main
