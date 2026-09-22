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
$stateFile = Join-Path $wtRoot "task-$slug.json"

if (-not (Test-Path $stateFile)) {
    throw "Task state not found: $stateFile"
}

$state = Get-Content $stateFile -Raw | ConvertFrom-Json

$branch = "agent/integration/$slug"
$path = Join-Path $wtRoot "integration-$slug"

if (Test-Path $path) {
    throw "Integration worktree already exists."
}

& git show-ref --verify --quiet "refs/heads/$branch"

if ($LASTEXITCODE -eq 0) {
    throw "Integration branch already exists: $branch"
}

& git worktree add -b $branch $path $state.baseCommit

if ($LASTEXITCODE -ne 0) {
    throw "Failed to create integration worktree."
}

$lines = @("terra-a")

if ([int]$state.lines -eq 2) {
    $lines += "terra-b"
}

foreach ($line in $lines) {

    $lineBranch = "agent/$line/$slug"

    $commits = @(
        & git rev-list --reverse "$($state.baseCommit)..$lineBranch"
    )

    if ($commits.Count -eq 0) {
        throw "$lineBranch has no checkpoint commit. DeepSeek QA must PASS and DeepSeek Git must checkpoint it first."
    }

    foreach ($commit in $commits) {

        Write-Host "Integrating $line commit $commit"

        & git -C $path cherry-pick $commit

        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "INTEGRATION CONFLICT"
            Write-Host "Sol High must diagnose this conflict."
            Write-Host "Correction must go through Terra High."
            throw "Cherry-pick failed."
        }
    }
}

Write-Host ""
Write-Host "INTEGRATION WORKTREE READY"
Write-Host $path
