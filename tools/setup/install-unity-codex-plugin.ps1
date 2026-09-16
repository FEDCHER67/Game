$ErrorActionPreference = "Stop"

Write-Host "Installing official Unity plugin for Codex..."

codex plugin marketplace add Unity-Technologies/unity-agent-plugin
codex plugin add unity@unity-agent-plugin

Write-Host ""
Write-Host "Installed plugins:"
codex plugin list

Write-Host ""
Write-Host "Unity Codex plugin setup complete."
