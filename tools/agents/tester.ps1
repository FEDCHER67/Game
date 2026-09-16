param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Task
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

Write-Host "=== DeepSeek Tester ==="
Write-Host "Repository: $RepoRoot"
Write-Host ""

& opencode.cmd run `
    --dir $RepoRoot `
    --agent deepseek-tester `
    --model deepseek/deepseek-flash `
    --variant max `
    $Task

if ($LASTEXITCODE -ne 0) {
    throw "DeepSeek Tester failed with exit code $LASTEXITCODE"
}