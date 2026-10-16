$ErrorActionPreference = 'Stop'
$repoRoot = 'C:\Dev\Game\'
$corePath = 'C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core'
$testPath = 'C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests'
$stagePath = 'C:\Dev\Game\ArtSource\Dev\Buyers_staging'
$reportPath = 'C:\Dev\Game\docs\reports\BUYERS_RULES_v01.md'
$inventoryPath = 'C:\Dev\Game\ArtSource\Dev\Buyers_staging\created-and-changed-files.txt'
$summaryPath = 'C:\Dev\Game\ArtSource\Dev\Buyers_staging\verification-summary.txt'

$coreAssembly = Get-Content -Raw -LiteralPath (Join-Path $corePath 'OnlyVolunteers.Buyers.Core.asmdef') | ConvertFrom-Json
if (!$coreAssembly.noEngineReferences -or $coreAssembly.references.Count -ne 0) { throw 'Core assembly references failed.' }
$testAssembly = Get-Content -Raw -LiteralPath (Join-Path $testPath 'OnlyVolunteers.Buyers.Tests.asmdef') | ConvertFrom-Json
if (!$testAssembly.noEngineReferences -or $testAssembly.includePlatforms.Count -ne 1 -or $testAssembly.includePlatforms[0] -ne 'Editor') { throw 'EditMode assembly failed.' }
$coreSources = @(Get-ChildItem -LiteralPath $corePath -Filter '*.cs' -File)
$testSources = @(Get-ChildItem -LiteralPath $testPath -Filter '*.cs' -File)
$coreText = ($coreSources | ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName }) -join "`n"
if ($coreText -match 'UnityEngine|UnityEditor|DateTime|new Random\s*\(') { throw 'Forbidden core dependency or hidden nondeterminism.' }
$testText = ($testSources | ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName }) -join "`n"
$coveredIds = @([regex]::Matches($testText, 'BUY(\d{2})') | ForEach-Object { [int]$_.Groups[1].Value } | Sort-Object -Unique)
$nonRuleIds = @(1..56 | Where-Object { $_ -notin $coveredIds })
if (($nonRuleIds -join ',') -ne '27,39,40') { throw 'Unexpected BUY coverage gap.' }
$reportText = Get-Content -Raw -LiteralPath $reportPath
$methods = @([regex]::Matches($testText, 'public void (BUY\w+)\(') | ForEach-Object { $_.Groups[1].Value })
foreach ($testReference in [regex]::Matches($reportText, '`(BUY\d{2}\w+)`')) {
    if ($testReference.Groups[1].Value -notin $methods) { throw ('Report names missing method: ' + $testReference.Groups[1].Value) }
}
foreach ($projectName in 'Buyers.Core.csproj','Buyers.Rules.Tests.csproj') {
    [xml]$projectXml = Get-Content -Raw -LiteralPath (Join-Path $stagePath $projectName)
    $linkedItems = @($projectXml.Project.ItemGroup.Compile | Where-Object { $_ })
    if ($linkedItems.Count -ne 1 -or !$linkedItems[0].Link -or !$linkedItems[0].Include.StartsWith($repoRoot + 'Assets\OnlyVolunteers\Buyers\', [StringComparison]::OrdinalIgnoreCase)) { throw ('Source link check failed: ' + $projectName) }
}
[xml]$trxDoc = Get-Content -Raw -LiteralPath (Join-Path $stagePath 'TestResults\buyers-results.trx')
$counters = $trxDoc.TestRun.ResultSummary.Counters
if ($counters.failed -ne '0' -or $counters.notExecuted -ne '0' -or $counters.passed -ne $counters.total -or $counters.total -ne '130') { throw 'NUnit result check failed.' }
$assetFiles = @(Get-ChildItem -LiteralPath $corePath,$testPath -File | Select-Object -ExpandProperty FullName)
$assetFiles += @(($corePath + '.meta'), ($testPath + '.meta'))
foreach ($source in @($coreSources) + @($testSources)) { if (!(Test-Path -LiteralPath ($source.FullName + '.meta') -PathType Leaf)) { throw ('Missing meta: ' + $source.FullName) } }
$guidValues = @($assetFiles | Where-Object { $_.EndsWith('.meta') } | ForEach-Object {
    $guidMatch = [regex]::Match((Get-Content -Raw -LiteralPath $_), '(?m)^guid:\s*([0-9a-f]{32})')
    if (!$guidMatch.Success) { throw ('Invalid meta: ' + $_) }; $guidMatch.Groups[1].Value
})
if (@($guidValues | Sort-Object -Unique).Count -ne $guidValues.Count) { throw 'Duplicate asset GUIDs.' }

# Create both evidence files before enumeration so the inventory includes itself and its verification.
Set-Content -LiteralPath $inventoryPath -Value '' -Encoding utf8NoBOM
Set-Content -LiteralPath $summaryPath -Value '' -Encoding utf8NoBOM
$stageFiles = @(Get-ChildItem -LiteralPath $stagePath -File -Recurse -Force | Select-Object -ExpandProperty FullName)
$allOutputs = @($assetFiles + $reportPath + $stageFiles | Sort-Object -Unique)
foreach ($outputPath in $allOutputs) {
    $fullOutputPath = [IO.Path]::GetFullPath($outputPath)
    if (!$fullOutputPath.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath $fullOutputPath -PathType Leaf)) { throw ('Invalid output location or missing file: ' + $outputPath) }
}
Set-Content -LiteralPath $inventoryPath -Value $allOutputs -Encoding utf8NoBOM
$summaryLines = @(
    'G27 buyer rules verification: PASS'
    'NUnit: total 130; passed 130; failed 0; skipped 0.'
    'Core: .NET Standard 2.1; five original linked C# files; no Unity references.'
    'Tests: four original linked C# files; Editor-only asmdef; no Unity execution.'
    'BUY coverage: 53 rule IDs. Non-rule IDs: BUY-27, BUY-39, BUY-40.'
    'Report method names, source links, asmdefs and asset GUID uniqueness: PASS.'
    ('Absolute output file paths checked: ' + $allOutputs.Count)
    'Every listed path exists as a file under C:\Dev\Game\: PASS.'
    ('Complete file inventory: ' + $inventoryPath)
    'No git staging, commit, push, scene or operation edits were performed.'
)
Set-Content -LiteralPath $summaryPath -Value $summaryLines -Encoding utf8NoBOM
$summaryLines
'Authored assets and report (generated staging files are enumerated in the complete inventory):'
$assetFiles + $reportPath
