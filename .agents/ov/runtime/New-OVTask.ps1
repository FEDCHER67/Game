param(
    [Parameter(Mandatory = $true)]
    [string]$Task,

    [ValidateSet(1,2)]
    [int]$Lines = 1
)

$ErrorActionPreference = "Stop"

$root = (& git rev-parse --show-toplevel).Trim()

if (-not $root) {
    throw "Not inside a Git repository."
}

Set-Location $root

$dirty = & git status --porcelain

if ($dirty) {
    throw "Main working tree must be clean before starting a NORMAL agent task."
}

$slug = $Task.ToLowerInvariant()
$slug = $slug -replace '[^a-z0-9-]+', '-'
$slug = $slug.Trim('-')

if (-not $slug) {
    throw "Invalid task name."
}

$baseBranch = (& git branch --show-current).Trim()

if (-not $baseBranch) {
    throw "Main working tree is in detached HEAD state."
}

$baseCommit = (& git rev-parse HEAD).Trim()

$wtRoot = Join-Path $root "_agent_worktrees"

$wtRoot = [System.IO.Path]::GetFullPath($wtRoot)
$rootPath = [System.IO.Path]::GetFullPath($root)
$rootPrefix = $rootPath.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $wtRoot.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use a worktree root outside this repository: $wtRoot"
}

New-Item -ItemType Directory -Force -Path $wtRoot | Out-Null

function New-AgentLine {
    param(
        [string]$Line
    )

    $branch = "agent/$Line/$slug"
    $path = [System.IO.Path]::GetFullPath((Join-Path $wtRoot "$Line-$slug"))
    $wtPrefix = $wtRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

    if (-not $path.StartsWith($wtPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $path) -ne "$Line-$slug") {
        throw "Refusing to create an unexpected worktree path: $path"
    }

    if (Test-Path -LiteralPath $path) {
        throw "Worktree already exists: $path"
    }

    & git show-ref --verify --quiet "refs/heads/$branch"

    if ($LASTEXITCODE -eq 0) {
        throw "Branch already exists: $branch"
    }

    Write-Host "Creating $Line"
    Write-Host "Branch:   $branch"
    Write-Host "Worktree: $path"

    & git worktree add -b $branch $path $baseCommit

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create $Line worktree."
    }
}

New-AgentLine "terra-a"

if ($Lines -eq 2) {
    New-AgentLine "terra-b"
}

$state = [ordered]@{
    task       = $slug
    lines      = $Lines
    baseBranch = $baseBranch
    baseCommit = $baseCommit
    created    = (Get-Date).ToString("o")
}

$state |
    ConvertTo-Json |
    Set-Content (Join-Path $wtRoot "task-$slug.json") -Encoding UTF8

Write-Host ""
Write-Host "OV TASK READY"
Write-Host "Task:       $slug"
Write-Host "Lines:      $Lines"
Write-Host "Base:       $baseBranch"
Write-Host "Base commit:$baseCommit"
