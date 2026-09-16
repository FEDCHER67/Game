param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Task
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Worktree = Join-Path $RepoRoot "_worktrees\ds1"

if (-not (Test-Path $Worktree)) {
    throw "DeepSeek Worker #1 worktree not found: $Worktree"
}

Write-Host "=== DeepSeek Worker #1 ==="
Write-Host "Worktree: $Worktree"
Write-Host ""

& opencode.cmd run `
    --dir $Worktree `
    --agent deepseek-worker `
    --model deepseek/deepseek-flash `
    --variant max `
    $Task

if ($LASTEXITCODE -ne 0) {
    throw "DeepSeek Worker #1 failed with exit code $LASTEXITCODE"
}