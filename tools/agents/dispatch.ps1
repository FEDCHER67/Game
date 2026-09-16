param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("worker1", "worker2", "tester", "research")]
    [string]$Target,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$AgentsDir = $PSScriptRoot

switch ($Target) {
    "worker1" { $ScriptName = "worker1.ps1" }
    "worker2" { $ScriptName = "worker2.ps1" }
    "tester"  { $ScriptName = "tester.ps1" }
    "research"{ $ScriptName = "research.ps1" }
}

& powershell.exe `
    -ExecutionPolicy Bypass `
    -File (Join-Path $AgentsDir $ScriptName) `
    $Task

if ($LASTEXITCODE -ne 0) {
    throw "$Target failed with exit code $LASTEXITCODE"
}