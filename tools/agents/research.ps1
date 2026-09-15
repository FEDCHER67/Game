param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Task
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

# Enable OpenCode web search tools for this process.
$env:OPENCODE_ENABLE_EXA = "1"

Write-Host "=== DeepSeek Researcher ==="
Write-Host "Repository: $RepoRoot"
Write-Host ""

& opencode.cmd run `
    --dir $RepoRoot `
    --agent deepseek-researcher `
    --model deepseek/deepseek-flash `
    --variant low `
    $Task

if ($LASTEXITCODE -ne 0) {
    throw "DeepSeek Researcher failed with exit code $LASTEXITCODE"
}