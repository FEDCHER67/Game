$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

$stateDir = Join-Path $root ".git\agent-state"
New-Item -ItemType Directory -Force $stateDir | Out-Null

$inputFile  = Join-Path $stateDir "committer-input.tmp"
$stdoutFile = Join-Path $stateDir "committer-stdout.tmp"
$stderrFile = Join-Path $stateDir "committer-stderr.tmp"
$logFile    = Join-Path $stateDir "committer-last.log"

Remove-Item $inputFile,$stdoutFile,$stderrFile -Force -ErrorAction SilentlyContinue

"APPROVE_PENDING_TASK=YES" |
    Set-Content -LiteralPath $inputFile -Encoding ASCII

$opencode = (Get-Command opencode.cmd -ErrorAction Stop).Source

$cmdLine = '""{0}" run --agent deepseek-committer"' -f $opencode

$process = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList @("/d", "/s", "/c", $cmdLine) `
    -RedirectStandardInput $inputFile `
    -RedirectStandardOutput $stdoutFile `
    -RedirectStandardError $stderrFile `
    -Wait `
    -PassThru `
    -NoNewWindow

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

# Сохраняем полный лог, но не засоряем им консоль.
$text | Set-Content -LiteralPath $logFile -Encoding UTF8

Remove-Item $inputFile,$stdoutFile,$stderrFile -Force -ErrorAction SilentlyContinue

# Убираем ANSI-коды.
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
    Write-Host "✗ Not approved"
    exit 1
}

$commit = [regex]::Match(
    $text,
    '(?m)^([0-9a-f]{7,40})\s+[—-]\s+(.+)$'
)

$success = $text -match "COMMITTED AND PUSHED"

if ($process.ExitCode -eq 0 -and $success) {

    if ($commit.Success) {
        $fullHash = $commit.Groups[1].Value
        $hash = $fullHash.Substring(
            0,
            [Math]::Min(7, $fullHash.Length)
        )
        $message = $commit.Groups[2].Value.Trim()

        Write-Host ""
        Write-Host "✓ $hash — $message"
    }
    else {
        Write-Host ""
        Write-Host "✓ Task committed and pushed"
    }

    $ua1 = $text -match '(?m)^ua1:\s+SYNCED'
    $ua2 = $text -match '(?m)^ua2:\s+SYNCED'

    if ($ua1 -and $ua2) {
        Write-Host "✓ main + ua1 + ua2 synced"
    }
    elseif ($ua1) {
        Write-Host "✓ main + ua1 synced; ua2 skipped"
    }
    elseif ($ua2) {
        Write-Host "✓ main + ua2 synced; ua1 skipped"
    }
    else {
        Write-Host "✓ main pushed; worker sync skipped"
    }

    exit 0
}

Write-Host ""
Write-Host "✗ Committer stopped"
Write-Host "Full log: .git\agent-state\committer-last.log"

exit 1
