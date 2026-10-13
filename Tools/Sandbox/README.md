# Sandbox tools (outside Assets; approved by Fedya 2026-10-13)

Downloaded binaries are git-ignored; re-download with the commands below. Decisions: docs/DependencyDecisions.md.

| Tool | Version | Licence | Source | SHA-256 | Status |
|---|---|---|---|---|---|
| enginesound (DasEtwas) | v1.5.0 (last release with Windows binaries; v1.6 has none) | MIT | https://github.com/DasEtwas/enginesound/releases/tag/v1.5.0 | gui 15e4eae4…, cli b5a3e699… (see `sha256sum`) | `enginesound-cli.exe --help` runs; generates synthetic engine WAV loops for VehicleEngineAudio (idle/low/mid/high). |
| TexTools (franMarz) | v1.6.1 | GPL-family add-on (exported assets unaffected) | https://github.com/franMarz/TexTools-Blender/releases/tag/v1.6.1 | 0e8f13cf… | Installed and enabled in Blender 5.2 user profile (tested first in a throwaway profile: enables without errors). Texel density / UV tools for the v3 kits. |

Re-download:
    curl -L -o enginesound/v1.5.0/enginesound-gui.exe https://github.com/DasEtwas/enginesound/releases/download/v1.5.0/enginesound-gui.exe
    curl -L -o enginesound/v1.5.0/enginesound-cli.exe https://github.com/DasEtwas/enginesound/releases/download/v1.5.0/enginesound-cli.exe
    curl -L -o TexTools/v1.6.1/TexTools_1_6_1.zip https://github.com/franMarz/TexTools-Blender/releases/download/v1.6.1/TexTools_1_6_1.zip

Also on 2026-10-13: blender-mcp pinned to 2.0.0 in ~/.claude.json and ~/.codex/config.toml (backups *.bak_20261013); the BlenderMCP add-on is now enabled in Blender 5.2 (start its server from the N-panel "BlenderMCP" tab when Blender is open).
