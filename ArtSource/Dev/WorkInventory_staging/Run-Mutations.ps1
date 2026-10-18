. "$PSScriptRoot\Environment.ps1"
Set-Location -LiteralPath $PSScriptRoot
$mutations = @(
    @{ Name='M1-room-interval'; File='src/ItemCoreTypes.cs'; Replacements=@(
        @('RoomSecondsPerGrade = 300;', 'RoomSecondsPerGrade = 301;')) },
    @{ Name='M2-two-hands'; File='src/PlayerInventory.cs'; Replacements=@(
        @('if (CarryCore(playerId) != null) return MoveResult.Fail(ItemError.TwoHandedOnly);', 'if (CarryCore(playerId) != null && slot < 0) return MoveResult.Fail(ItemError.TwoHandedOnly);')) },
    @{ Name='M3-disconnected-freeze'; File='src/ItemLedger.cs'; Replacements=@(
        @('if (!r.HasOrgan || Detached(r)) return;', 'if (!r.HasOrgan) return;')) },
    @{ Name='M4-cold-chain'; File='src/ItemLedger.cs'; Replacements=@(
        @('r.Organ.CaseColdLatch = to?.Kind == ContainerKind.BuyerCase && DeliveredColdCore(r, now);', 'r.Organ.CaseColdLatch = to?.Kind == ContainerKind.BuyerCase;')) },
    @{ Name='M5-request-dedup'; File='src/PlayerInventory.cs'; Replacements=@(
        @('if (previous != null) { var replay = previous.Result; replay.Replayed = true; return replay; }', 'if (previous != null) saved.Results.Remove(previous);'),
        @('if (requestId <= saved.HighWater) return MoveResult.Fail(ItemError.StaleRequest);', 'if (requestId <= 0) return MoveResult.Fail(ItemError.StaleRequest);')) }
)
$results = @()
foreach ($mutation in $mutations) {
    $sourcePath = Join-Path $PSScriptRoot $mutation.File
    $originalBytes = [IO.File]::ReadAllBytes($sourcePath)
    $originalHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    $sourceText = [IO.File]::ReadAllText($sourcePath)
    # PowerShell unwraps a single nested pair; normalize it to one replacement list.
    $pairs = $mutation.Replacements
    if ($pairs.Count -eq 2 -and $pairs[0] -is [string]) { $pairs = ,$pairs }
    foreach ($pair in $pairs) {
        if (($sourceText.Split([string[]]@($pair[0]), [StringSplitOptions]::None).Length - 1) -ne 1) { throw "Expected one mutation anchor: $($mutation.Name)" }
        $sourceText = $sourceText.Replace($pair[0], $pair[1])
    }
    $trxPath = Join-Path $PSScriptRoot "evidence/$($mutation.Name).trx"
    try {
        [IO.File]::WriteAllText($sourcePath, $sourceText, [Text.UTF8Encoding]::new($false))
        & dotnet test tests/WorkInventory.Tests.csproj -c Release --no-restore --nologo --logger "trx;LogFileName=$($mutation.Name).trx" --results-directory "$PSScriptRoot/evidence" 2>&1 |
            Out-File -LiteralPath "$PSScriptRoot/evidence/$($mutation.Name).txt" -Encoding utf8
        $testExit = $LASTEXITCODE
        if (!(Test-Path -LiteralPath $trxPath)) { throw "Mutation did not produce test evidence (compilation is not a test catch): $($mutation.Name)" }
        [xml]$trx = Get-Content -LiteralPath $trxPath -Raw
        $failed = @($trx.TestRun.Results.UnitTestResult | Where-Object outcome -eq 'Failed' | ForEach-Object testName)
        if ($testExit -eq 0 -or $failed.Count -eq 0) { throw "Mutation survived: $($mutation.Name)" }
        $results += [pscustomobject]@{ Mutation=$mutation.Name; Source=$mutation.File; ExitCode=$testExit; Executed=[int]$trx.TestRun.ResultSummary.Counters.executed; Failed=$failed.Count; FailingTests=$failed; OriginalHash=$originalHash; RestoredHash='' }
        Write-Output "CAUGHT $($mutation.Name): $($failed.Count) failing tests"
    }
    finally {
        [IO.File]::WriteAllBytes($sourcePath, $originalBytes)
        $restoredHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
        if ($restoredHash -ne $originalHash) { throw "Source restoration hash mismatch: $sourcePath" }
        if ($results.Count -gt 0 -and $results[-1].Mutation -eq $mutation.Name) { $results[-1].RestoredHash = $restoredHash }
        $results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$PSScriptRoot/evidence/mutation-results.json" -Encoding utf8
    }
}
& "$PSScriptRoot/Run-Tests.ps1" -ResultName 'inventory-final'
& dotnet run -c Release --project selftest 2>&1 | Out-File -LiteralPath "$PSScriptRoot/evidence/selftest-final.txt" -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'Restored console selftest failed' }
Get-Content -LiteralPath "$PSScriptRoot/evidence/selftest-final.txt" | Select-Object -Last 1
