param([string]$Filter = '', [string]$ResultName = 'inventory-results')
. "$PSScriptRoot\Environment.ps1"
Set-Location -LiteralPath $PSScriptRoot
$testArgs = @('test', 'tests/WorkInventory.Tests.csproj', '-c', 'Release', '--logger', "trx;LogFileName=$ResultName.trx", '--results-directory', "$PSScriptRoot\evidence", '--nologo')
if ($Filter) { $testArgs += @('--filter', $Filter) }
& dotnet @testArgs 2>&1 | Tee-Object -FilePath "$PSScriptRoot\evidence\$ResultName.txt"
if ($LASTEXITCODE -ne 0) { throw "Inventory tests failed ($LASTEXITCODE)" }
