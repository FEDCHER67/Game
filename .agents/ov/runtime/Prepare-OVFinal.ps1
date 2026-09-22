param(
    [Parameter(Mandatory = $true)]
    [string]$Task
)

$ErrorActionPreference = "Stop"

$root = (& git rev-parse --show-toplevel).Trim()

if (-not $root) {
    throw "Not inside a Git repository."
}

Set-Location $root

$slug = $Task.ToLowerInvariant()
$slug = $slug -replace '[^a-z0-9-]+', '-'
$slug = $slug.Trim('-')

if (-not $slug) {
    throw "Invalid task name."
}

$stateFile = Join-Path $root "_agent_worktrees\task-$slug.json"

if (-not (Test-Path -LiteralPath $stateFile -PathType Leaf)) {
    throw "Task state not found."
}

$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json

if ($state.task -ne $slug -or -not $state.baseBranch -or -not $state.baseCommit) {
    throw "Task state is invalid for '$slug'."
}

$current = (& git branch --show-current).Trim()

if ($current -ne $state.baseBranch) {
    throw "Main tree must be on base branch '$($state.baseBranch)'. Current: '$current'"
}

$dirty = & git status --porcelain

if ($dirty) {
    throw "Base working tree must be clean before final squash."
}

$integrationBranch = "agent/integration/$slug"

& git show-ref --verify --quiet "refs/heads/$integrationBranch"

if ($LASTEXITCODE -ne 0) {
    throw "Integration branch not found: $integrationBranch"
}

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
