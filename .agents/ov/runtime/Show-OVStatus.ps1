$ErrorActionPreference = "Stop"

$root = (& git rev-parse --show-toplevel).Trim()

if (-not $root) {
    throw "Not inside a Git repository."
}

Set-Location $root

$worktreeRoot = Join-Path $root "_agent_worktrees"

Write-Host "=== CURRENT WORKTREE ==="
Write-Host "Root: $root"
& git branch --show-current
& git status --short

Write-Host "`n=== WORKTREES ==="
& git worktree list

Write-Host "`n=== AGENT BRANCHES ==="
& git branch --list "agent/*"

Write-Host "`n=== ACTIVE TASK STATES ==="
Get-ChildItem -LiteralPath $worktreeRoot -Filter "task-*.json" -File -ErrorAction SilentlyContinue |
    Select-Object Name, LastWriteTime

Write-Host "`n=== EXPECTED OV LAYOUT ==="
$layoutPaths = @(
    ".agents/ov/handoffs/terra-a",
    ".agents/ov/handoffs/terra-b",
    ".agents/ov/research/deepseek",
    ".agents/ov/qa/terra-a",
    ".agents/ov/qa/terra-b",
    ".agents/ov/qa/final",
    ".agents/ov/integration",
    ".agents/ov/git",
    ".agents/ov/reports",
    ".agents/ov/runtime",
    "_agent_worktrees"
)

$layoutStatus = foreach ($relativePath in $layoutPaths) {
    $path = Join-Path $root $relativePath
    [PSCustomObject]@{
        Path   = $relativePath
        Exists = Test-Path -LiteralPath $path
    }
}

$layoutStatus | Format-Table -AutoSize
