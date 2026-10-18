$ErrorActionPreference = 'Stop'
$stageRoot = $PSScriptRoot
$env:DOTNET_CLI_HOME = Join-Path $stageRoot '.dotnet'
$env:NUGET_PACKAGES = Join-Path $stageRoot 'packages'
$env:NUGET_HTTP_CACHE_PATH = Join-Path $stageRoot 'http-cache'
$env:NUGET_PLUGINS_CACHE_PATH = Join-Path $stageRoot 'plugin-cache'
$env:TEMP = Join-Path $stageRoot 'tmp'
$env:TMP = $env:TEMP
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE = 'true'
$env:DOTNET_CLI_UI_LANGUAGE = 'en-US'
$env:VSLANG = '1033'
$env:PYTHONDONTWRITEBYTECODE = '1'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
