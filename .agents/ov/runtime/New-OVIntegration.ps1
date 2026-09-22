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

$wtRoot = [System.IO.Path]::GetFullPath((Join-Path $root "_agent_worktrees"))
$stateFile = Join-Path $wtRoot "task-$slug.json"

if (-not (Test-Path -LiteralPath $stateFile -PathType Leaf)) {
    throw "Task state not found: $stateFile"
}

$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json

if ($state.task -ne $slug -or [int]$state.lines -notin 1, 2 -or -not $state.baseCommit) {
    throw "Task state is invalid for '$slug'."
}

$branch = "agent/integration/$slug"
$path = [System.IO.Path]::GetFullPath((Join-Path $wtRoot "integration-$slug"))
$wtPrefix = $wtRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $path.StartsWith($wtPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $path) -ne "integration-$slug") {
    throw "Refusing to create an unexpected integration worktree path: $path"
}

if (Test-Path -LiteralPath $path) {
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
