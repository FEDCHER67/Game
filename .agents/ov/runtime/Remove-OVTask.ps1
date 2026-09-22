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
$rootPath = [System.IO.Path]::GetFullPath($root)
$rootPrefix = $rootPath.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $wtRoot.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use a worktree root outside this repository: $wtRoot"
}

$stateFile = Join-Path $wtRoot "task-$slug.json"

if (-not (Test-Path -LiteralPath $stateFile -PathType Leaf)) {
    throw "Task state not found: $stateFile"
}

$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json

if ($state.task -ne $slug -or [int]$state.lines -notin 1, 2 -or -not $state.baseBranch -or -not $state.baseCommit) {
    throw "Task state is invalid for '$slug'."
}

$currentBranch = (& git branch --show-current).Trim()

if ($currentBranch -ne $state.baseBranch) {
    throw "Run cleanup from recorded base branch '$($state.baseBranch)'. Current: '$currentBranch'"
}

$worktreeNames = @("terra-a-$slug", "integration-$slug")
$lineBranches = @("agent/terra-a/$slug")
$branches = @("agent/terra-a/$slug", "agent/integration/$slug")

if ([int]$state.lines -eq 2) {
    $worktreeNames += "terra-b-$slug"
    $lineBranches += "agent/terra-b/$slug"
    $branches += "agent/terra-b/$slug"
}

$worktreeOutput = @(& git worktree list --porcelain)

if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect registered worktrees."
}

$registeredWorktrees = @{}
$branchWorktrees = @{}
$worktreeBlocks = ($worktreeOutput -join "`n") -split "(?:\r?\n){2,}"

foreach ($block in $worktreeBlocks) {
    $lines = $block -split "\r?\n"
    $worktreeLine = $lines | Where-Object { $_.StartsWith("worktree ") } | Select-Object -First 1

    if (-not $worktreeLine) {
        continue
    }

    $worktreePath = [System.IO.Path]::GetFullPath($worktreeLine.Substring(9))
    $registeredWorktrees[$worktreePath] = $true
    $branchLine = $lines | Where-Object { $_.StartsWith("branch refs/heads/") } | Select-Object -First 1

    if ($branchLine) {
        $branchWorktrees[$branchLine.Substring(18)] = $worktreePath
    }
}

$taskWorktrees = @{}

foreach ($name in $worktreeNames) {
    $path = [System.IO.Path]::GetFullPath((Join-Path $wtRoot $name))
    $wtPrefix = $wtRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

    if (-not $path.StartsWith($wtPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $path) -ne $name) {
        throw "Refusing to remove an unexpected worktree path: $path"
    }

    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "Recorded task worktree is missing: $path"
    }

    if (-not $registeredWorktrees.ContainsKey($path)) {
        throw "Refusing to remove unregistered worktree-like directory: $path"
    }

    $worktreeStatus = @(& git -C $path status --porcelain)

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect task worktree: $path"
    }

    if ($worktreeStatus.Count -gt 0) {
        throw "Refusing to remove dirty task worktree: $path"
    }

    $taskWorktrees[$name] = $path
}

foreach ($branch in $branches) {
    & git show-ref --verify --quiet "refs/heads/$branch"

    if ($LASTEXITCODE -ne 0) {
        throw "Recorded temporary branch is missing: $branch"
    }
}

$expectedBranchWorktrees = @{
    "agent/terra-a/$slug" = $taskWorktrees["terra-a-$slug"]
    "agent/integration/$slug" = $taskWorktrees["integration-$slug"]
}

if ([int]$state.lines -eq 2) {
    $expectedBranchWorktrees["agent/terra-b/$slug"] = $taskWorktrees["terra-b-$slug"]
}

foreach ($branch in $branches) {
    if ($branchWorktrees.ContainsKey($branch) -and $branchWorktrees[$branch] -ne $expectedBranchWorktrees[$branch]) {
        throw "Recorded temporary branch is checked out in an unexpected worktree: $branch"
    }
}

$integrationBranch = "agent/integration/$slug"

foreach ($lineBranch in $lineBranches) {
    $cherry = @(& git cherry $integrationBranch $lineBranch)

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to verify integration coverage for $lineBranch."
    }

    if (@($cherry | Where-Object { $_.StartsWith("+") }).Count -gt 0) {
        throw "$lineBranch has changes not preserved by $integrationBranch."
    }
}

& git diff --quiet $state.baseBranch $integrationBranch
$preservedOnBase = $LASTEXITCODE -eq 0

if (-not $preservedOnBase -and $LASTEXITCODE -gt 1) {
    throw "Unable to compare $integrationBranch with recorded base branch '$($state.baseBranch)'."
}

if (-not $preservedOnBase) {
    & git diff --quiet $integrationBranch

    if ($LASTEXITCODE -eq 0) {
        $preservedOnBase = $true
        Write-Host "Integration result is preserved by the current base working tree."
    }
    elseif ($LASTEXITCODE -gt 1) {
        throw "Unable to compare the current base working tree with $integrationBranch."
    }
}

if (-not $preservedOnBase) {
    throw "Integration result is not preserved on base branch '$($state.baseBranch)' or its current working tree."
}

foreach ($name in $worktreeNames) {
    $path = $taskWorktrees[$name]
    Write-Host "Removing worktree: $path"
    & git worktree remove $path

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to remove $path. Resolve it without discarding work, then retry."
    }
}

foreach ($branch in $branches) {
    Write-Host "Deleting proven-preserved temporary branch: $branch"
    & git branch -D $branch

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to delete temporary branch '$branch'. Its state file was retained; inspect the checkout and retry."
    }
}

Remove-Item -LiteralPath $stateFile -ErrorAction Stop

Write-Host ""
Write-Host "OV TASK CLEANED: $slug"
