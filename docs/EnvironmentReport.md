# Environment report (2026-10-13)

Facts read on the machine on 2026-10-13 by a Claude Code worker. No secrets or account data are recorded here.

## Execution mode

Local Claude Code 2.1.286 (Opus worker) on Fedya's Windows PC, Git Bash shell, working directory `C:\Dev\Game`. Real access: files, terminal, the open Unity editor (unity-mcp), Blender 5.2 CLI. Network through a local proxy (`http://127.0.0.1:10809/`, from the OS settings).

## Machine

| Item | Value |
|---|---|
| OS | Windows 11 Pro 10.0.26200 (build 26200) |
| CPU | AMD Ryzen 7 7800X3D, 8 cores (8 logical processors reported) |
| RAM | 31.1 GB usable (32 GB DDR5) |
| GPU | NVIDIA GeForce RTX 5070 Ti, driver 32.0.15.9649 (plus a basic display adapter entry) |

## Tools

| Tool | Version / path |
|---|---|
| Unity Editor | 6000.5.11f1 (5c3a1087d8e4), `C:\Program Files\Unity 6000.5.11f1\Editor\Unity.exe` |
| Unity CLI | 1.0.0-beta.13 (`unity`, WindowsApps install; a second copy at `%LOCALAPPDATA%\Unity\bin\unity.exe`) |
| Blender | 5.2.1 LTS, `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` (not on PATH) |
| Claude Code | 2.1.286 |
| Codex CLI | 0.160.0 (`codex`, npm global); Fedya uses the Codex desktop app |
| uv / uvx | on PATH (WinGet links) |
| git | 2.55.0.windows.5, git-lfs 3.7.1, gh 2.101.0 |
| Python | 3.12 (`%LOCALAPPDATA%\Programs\Python\Python312`) |
| Node.js | `C:\Program Files\nodejs\node` |

## Project

| Item | Value |
|---|---|
| Path | `C:\Dev\Game` (git, branch main; last commit 40a0fe7d "[fedya] TASK-000401..000409 …") |
| Product name | VOLUNTEERS ONLY |
| Render pipeline | URP 17.5.0 (render-pipelines.core 17.5.0) |
| Networking | FishNet 4.7.3 (git `FirstGearGames/FishNet#4.7.3`) + Tugboat |
| Input | Input System 1.20.0 plus the legacy Input Manager (both read by current scripts; Unity warns that the Input Manager is marked for deprecation) |
| Navigation | AI Navigation 2.0.14 |
| Other packages | Test Framework 1.7.0, uGUI 2.5.0, Rider 3.0.38, Visual Studio 2.0.26, Burst 1.8.30, Mathematics 1.4.0, Collections 6.5.0, built-in modules |
| Third-party code in Assets | KinematicCharacterController (player motor), OnlyVolunteers/ThirdParty |
| Current play scene | `Assets/OnlyVolunteers/Scenes/Map/Map_Look_v17_Play.unity` (tracked) |
| Build scenes | `NetworkTest` only (ProjectSettings/EditorBuildSettings.asset) |
| Console at start | 0 errors; 2 warnings (Input Manager deprecation, editor running with Administrator privileges) |

Not in the manifest: Cinemachine, ProBuilder, Splines (the kit lists them as candidates; the game's cameras and van do not use them).

## Existing bridges and agent integrations

| Integration | State |
|---|---|
| Claude ↔ Unity | unity-mcp: package `com.coplaydev.unity-mcp` v10.2.0 (git commit 30d22075093d); server `uvx --from mcpforunityserver==10.2.0 mcp-for-unity --transport stdio`; `claude mcp list`: Connected |
| Codex ↔ Unity | same `unityMCP` server in `~/.codex/config.toml` (env UNITY_MCP_DEFAULT_INSTANCE=GAME); not exercised in this session |
| Claude ↔ Blender, Codex ↔ Blender | blender-mcp (`uvx blender-mcp`) registered in both clients; the server starts, the Blender addon socket needs a running Blender with the addon |
| Serena | registered in both clients (code navigation) |
| Unity agent plugin (Claude) | `unity@claude-plugins-official` 0.1.6-beta, enabled, user scope |
| Unity Pipeline package | not installed on purpose (one Unity bridge only) |
| Project skills | 9 `fc-*` in `.claude/skills/` and `.agents/skills/`; originals in `Tools/FieldClinicBrief/skills/` |
| Other Claude plugins | agent-foundry, ai-3d-foundry, blender-texture-foundry, context7 (needs auth), csharp-lsp, pr-review-toolkit and others (user scope) |

## Notes

- `unity doctor` warns about a duplicate `unity.exe` on PATH and disabled Windows long paths; the auth session is "stale" but logged in. None of these blocked the tests.
- The repository root contains 17 empty directories with garbled names (e.g. `Ȍ蜫我뽀`, dated 2026-10-07; git ignores empty folders). They were left untouched; worth a look by the owner.
