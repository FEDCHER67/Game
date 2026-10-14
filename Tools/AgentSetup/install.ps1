# Installs Fedya's AI-agent setup for VOLUNTEERS ONLY on this PC (user level).
# Copies skills/agents for Claude Code and Codex, and the Blender MCP add-on. Never overwrites existing files unless -Force.
# MCP servers and Claude plugins are registered by the agent following SETUP.md (they need the CLIs).
param([switch]$Force)
$ErrorActionPreference = 'Stop'
$kit = $PSScriptRoot
$userDir = $env:USERPROFILE

function Install-Tree([string]$src, [string]$dst) {
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $src -Force) {
        $target = Join-Path $dst $item.Name
        if ((Test-Path -LiteralPath $target) -and -not $Force) { Write-Output "skip (exists): $target"; continue }
        Copy-Item -LiteralPath $item.FullName -Destination $target -Recurse -Force
        Write-Output "installed: $target"
    }
}

Install-Tree "$kit\claude\skills" "$userDir\.claude\skills"
Install-Tree "$kit\claude\agents" "$userDir\.claude\agents"
Install-Tree "$kit\codex\skills"  "$userDir\.codex\skills"
New-Item -ItemType Directory -Force -Path "$userDir\.ai-bridge" | Out-Null

$addons = Join-Path $env:APPDATA 'Blender Foundation\Blender\5.2\scripts\addons'
New-Item -ItemType Directory -Force -Path $addons | Out-Null
$addon = Join-Path $addons 'blender_mcp.py'
if ((Test-Path -LiteralPath $addon) -and -not $Force) { Write-Output "skip (exists): $addon" }
else { Copy-Item -LiteralPath "$kit\blender\blender_mcp.py" -Destination $addon -Force; Write-Output "installed: $addon" }
Write-Output 'Done. In Blender 5.2: Edit > Preferences > Add-ons > enable "MCP for Blender"; then View3D sidebar > MCP > Connect.'
