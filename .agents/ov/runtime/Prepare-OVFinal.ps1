param(
    [Parameter(Mandatory = $true)]
    [string]$Task
)

$ErrorActionPreference = "Stop"

$root = (& git rev-parse --show-toplevel).Trim()
Set-Location $root

$slug = $Task.ToLowerInvariant()
$slug = $slug -replace '[^a-z0-9-]+', '-'
$slug = $slug.Trim('-')

$stateFile = Join-Path $root "_agent_worktrees\task-$slug.json"

if (-not (Test-Path $stateFile)) {
    throw "Task state not found."
}

$state = Get-Content $stateFile -Raw | ConvertFrom-Json

$current = (& git branch --show-current).Trim()

if ($current -ne $state.baseBranch) {
    throw "Main tree must be on base branch '$($state.baseBranch)'. Current: '$current'"
}

$dirty = & git status --porcelain

if ($dirty) {
    throw "Base working tree must be clean before final squash."
}

$integrationBranch = "agent/integration/$slug"

Write-Host "Squashing:"
Write-Host "$integrationBranch -> $($state.baseBranch)"

& git merge --squash $integrationBranch

if ($LASTEXITCODE -ne 0) {
    throw "Final squash failed."
}

Write-Host ""
Write-Host "FINAL RESULT IS STAGED."
Write-Host "DeepSeek MAX Git must now inspect:"
Write-Host "  git status"
Write-Host "  git diff --cached"
Write-Host "  git diff --check"
Write-Host ""
Write-Host "Then DeepSeek MAX creates the ONE final commit."
