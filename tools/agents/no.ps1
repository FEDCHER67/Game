$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root

$stateDir = Join-Path $root ".git\agent-state"
New-Item -ItemType Directory -Force $stateDir | Out-Null

$inputFile  = Join-Path $stateDir "reject-input.tmp"
$stdoutFile = Join-Path $stateDir "reject-stdout.tmp"
$stderrFile = Join-Path $stateDir "reject-stderr.tmp"
$logFile    = Join-Path $stateDir "committer-last.log"

Remove-Item $inputFile,$stdoutFile,$stderrFile -Force -ErrorAction SilentlyContinue

"REJECT_PENDING_TASK=YES" |
    Set-Content -LiteralPath $inputFile -Encoding ASCII

$opencode = (Get-Command opencode.cmd -ErrorAction Stop).Source
$cmdLine = '""{0}" run --agent deepseek-committer"' -f $opencode

$startArgs = @{
    FilePath               = "cmd.exe"
    ArgumentList           = @("/d", "/s", "/c", $cmdLine)
    RedirectStandardInput  = $inputFile
    RedirectStandardOutput = $stdoutFile
    RedirectStandardError  = $stderrFile
    Wait                   = $true
    PassThru               = $true
    NoNewWindow            = $true
}

$process = Start-Process @startArgs

$stdout = if (Test-Path $stdoutFile) {
    Get-Content -Raw -LiteralPath $stdoutFile
} else {
    ""
}

$stderr = if (Test-Path $stderrFile) {
    Get-Content -Raw -LiteralPath $stderrFile
} else {
    ""
}

$text = $stdout + "`r`n" + $stderr

$text | Set-Content -LiteralPath $logFile -Encoding UTF8

Remove-Item $inputFile,$stdoutFile,$stderrFile -Force -ErrorAction SilentlyContinue

$text = [regex]::Replace(
    $text,
    "$([char]27)\[[0-?]*[ -/]*[@-~]",
    ""
)

if ($text -match "NO PENDING TASK") {
    Write-Host ""
    Write-Host "— No pending task"
    exit 0
}

if ($text -match "NOT APPROVED") {
    Write-Host ""
    Write-Host "✗ Rejection not approved"
    exit 1
}

$success = $text -match "PENDING TASK REJECTED"

if ($process.ExitCode -eq 0 -and $success) {
    Write-Host ""
    Write-Host "✓ Pending task rejected"
    Write-Host "✓ Task files restored/removed"

    $ua1 = $text -match '(?m)^ua1:\s+CLEANED'
    $ua2 = $text -match '(?m)^ua2:\s+CLEANED'

    if ($ua1 -and $ua2) {
        Write-Host "✓ main + ua1 + ua2 cleaned"
    }
    elseif ($ua1) {
        Write-Host "✓ main + ua1 cleaned; ua2 skipped"
    }
    elseif ($ua2) {
        Write-Host "✓ main + ua2 cleaned; ua1 skipped"
    }
    else {
        Write-Host "✓ main cleaned; worker cleanup skipped"
    }

    exit 0
}

Write-Host ""
Write-Host "✗ Committer stopped"
Write-Host "Full log: .git\agent-state\committer-last.log"
exit 1

