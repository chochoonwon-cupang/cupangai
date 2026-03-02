param(
  [string]$VmId = "vm-001"
)

$env:VM_ID = $VmId
$env:VM_NAME = "vm-001"
$env:REQUEUE_LEADER_VM = "vm-001"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -m src.main
