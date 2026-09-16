param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "union1",
        "tester1",
        "fixer1",
        "union2",
        "tester2",
        "fixer2",
        "integration-tester",
        "integration-fixer",
        "research"
    )]
    [string]$Target,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Task
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$config = @{
    "union1" = @{
        Agent = "union-alpha-1"
        Repo  = Join-Path $ProjectRoot "_worktrees\ua1"
    }
    "tester1" = @{
        Agent = "deepseek-tester-1"
        Repo  = Join-Path $ProjectRoot "_worktrees\ua1"
    }
    "fixer1" = @{
        Agent = "deepseek-fixer-1"
        Repo  = Join-Path $ProjectRoot "_worktrees\ua1"
    }

    "union2" = @{
        Agent = "union-alpha-2"
        Repo  = Join-Path $ProjectRoot "_worktrees\ua2"
    }
    "tester2" = @{
        Agent = "deepseek-tester-2"
        Repo  = Join-Path $ProjectRoot "_worktrees\ua2"
    }
    "fixer2" = @{
        Agent = "deepseek-fixer-2"
        Repo  = Join-Path $ProjectRoot "_worktrees\ua2"
    }

    "integration-tester" = @{
        Agent = "deepseek-integration-tester"
        Repo  = $ProjectRoot
    }
    "integration-fixer" = @{
        Agent = "deepseek-integration-fixer"
        Repo  = $ProjectRoot
    }

    "research" = @{
        Agent = "deepseek-researcher"
        Repo  = $ProjectRoot
    }
}

$TaskText = ""

if ($Task -and $Task.Count -gt 0) {
    $TaskText = ($Task -join " ")
}
elseif (-not [Console]::IsInputRedirected) {
    throw "No task supplied. Pass task text or pipe task text through stdin."
}
else {
    $TaskText = [Console]::In.ReadToEnd()
}

if ([string]::IsNullOrWhiteSpace($TaskText)) {
    throw "Task is empty."
}

$selected = $config[$Target]
$repo = $selected.Repo
$agent = $selected.Agent

if (-not (Test-Path -LiteralPath $repo)) {
    throw "Repository/worktree does not exist: $repo"
}

Write-Host "=== $Target ==="
Write-Host "Agent: $agent"
Write-Host "Repository: $repo"

Push-Location $repo

try {
    # Intentionally pipe prompt through stdin.
    # This avoids Windows command-line quoting/length problems for long task packets.
    $TaskText | & opencode.cmd run --agent $agent

    if ($LASTEXITCODE -ne 0) {
        throw "$Target failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
