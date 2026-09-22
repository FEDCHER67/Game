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

$wtRoot = Join-Path $root "_agent_worktrees"

$paths = @(
    "terra-a-$slug",
    "terra-b-$slug",
    "integration-$slug"
)

foreach ($name in $paths) {

    $path = Join-Path $wtRoot $name

    if (Test-Path $path) {
        Write-Host "Removing worktree: $path"
        & git worktree remove --force $path
    }
}

git worktree prune

$branches = @(
    "agent/terra-a/$slug",
    "agent/terra-b/$slug",
    "agent/integration/$slug"
)

foreach ($branch in $branches) {

    & git show-ref --verify --quiet "refs/heads/$branch"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Deleting temporary branch: $branch"
        & git branch -D $branch
    }
}

$stateFile = Join-Path $wtRoot "task-$slug.json"

Remove-Item $stateFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "OV TASK CLEANED: $slug"
