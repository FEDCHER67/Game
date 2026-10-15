$ErrorActionPreference = 'Stop'
$stagingPath = 'C:\Dev\Game\ArtSource\Dev\Buyers_staging'
Set-Location -LiteralPath $stagingPath
$env:DOTNET_CLI_HOME = Join-Path $stagingPath '.dotnet'
$env:NUGET_PACKAGES = Join-Path $stagingPath 'packages'
$env:NUGET_HTTP_CACHE_PATH = Join-Path $stagingPath 'http-cache'
$env:NUGET_PLUGINS_CACHE_PATH = Join-Path $stagingPath 'plugin-cache'
$env:TEMP = Join-Path $stagingPath 'tmp'
$env:TMP = $env:TEMP
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE = 'true'
$env:VSLANG = '1033'
$env:DOTNET_CLI_UI_LANGUAGE = 'en-US'
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
dotnet test 'C:\Dev\Game\ArtSource\Dev\Buyers_staging\Buyers.Rules.Tests.csproj' --configuration Release --logger 'console;verbosity=normal' --logger 'trx;LogFileName=buyers-results.trx' --results-directory 'C:\Dev\Game\ArtSource\Dev\Buyers_staging\TestResults' 2>&1 | Tee-Object -FilePath 'C:\Dev\Game\ArtSource\Dev\Buyers_staging\test-output.txt'
if ($LASTEXITCODE -ne 0) { throw "dotnet test failed: $LASTEXITCODE" }
