param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("worker1", "worker2", "research")]
    [string]$Target,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$AgentsDir = $PSScriptRoot

switch ($Target) {
    "worker1" {
        & powershell.exe -ExecutionPolicy Bypass `
            -File (Join-Path $AgentsDir "worker1.ps1") `
            $Task
    }

    "worker2" {
        & powershell.exe -ExecutionPolicy Bypass `
            -File (Join-Path $AgentsDir "worker2.ps1") `
            $Task
    }

    "research" {
        & powershell.exe -ExecutionPolicy Bypass `
            -File (Join-Path $AgentsDir "research.ps1") `
            $Task
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "$Target failed with exit code $LASTEXITCODE"
}
